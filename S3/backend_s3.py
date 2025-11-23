
from fastapi import FastAPI, UploadFile, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import subprocess
import os
import boto3
import mimetypes
import time

app = FastAPI(title="Terraform + S3 Mediator API")

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Allow CORS for local UI testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


# Terraform working directory
TF_DIR = os.path.dirname(os.path.abspath(__file__))


# -------------------------------------------------
# MODEL
# -------------------------------------------------
class BucketModel(BaseModel):
    bucket_name: str


# -------------------------------------------------
# CREATE BUCKET (via Terraform)
# -------------------------------------------------
@app.post("/bucket/create")
def create_bucket(bucket_name: str = Form(...)):
    try:
        # Create a temporary Terraform file
        tf_path = os.path.join(TF_DIR, "main.tf")
        with open(tf_path, "w") as f:
            f.write(f"""
provider "aws" {{
  region = "{AWS_REGION}"
}}

resource "aws_s3_bucket" "files_bucket" {{
  bucket        = "{bucket_name}"
  force_destroy = true
}}

resource "aws_s3_bucket_public_access_block" "public_access" {{
  bucket = aws_s3_bucket.files_bucket.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}}

resource "aws_s3_bucket_ownership_controls" "ownership" {{
  bucket = aws_s3_bucket.files_bucket.id
  rule {{
    object_ownership = "BucketOwnerPreferred"
  }}
}}

resource "aws_s3_bucket_acl" "bucket_acl" {{
  depends_on = [
    aws_s3_bucket_ownership_controls.ownership,
    aws_s3_bucket_public_access_block.public_access,
  ]
  bucket = aws_s3_bucket.files_bucket.id
  acl    = "public-read"
}}

resource "aws_s3_bucket_policy" "public_policy" {{
  bucket = aws_s3_bucket.files_bucket.id
  policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Sid       = "PublicReadAccess"
        Effect    = "Allow"
        Principal = "*"
        Action    = ["s3:GetObject"]
        Resource  = "${{aws_s3_bucket.files_bucket.arn}}/*"
      }}
    ]
  }})
}}

output "bucket_url" {{
  value = "https://${{aws_s3_bucket.files_bucket.bucket}}.s3.amazonaws.com/"
}}
""")

        # Run Terraform commands automatically
        subprocess.run(["terraform", "init", "-upgrade"], cwd=TF_DIR, check=True)
        
        time.sleep(10)  # 👈 give AWS a few seconds

        subprocess.run(["terraform", "apply", "-auto-approve"], cwd=TF_DIR, check=True)

        return {"message": f"S3 bucket '{bucket_name}' created successfully via Terraform."}
    except subprocess.CalledProcessError as e:
        return {"detail": f"Terraform error: {e}"}
    except Exception as e:
        return {"detail": str(e)}


# -------------------------------------------------
# UPLOAD FILE TO S3
# -------------------------------------------------
@app.post("/bucket/upload")
async def upload_file(bucket_name: str = Form(...), file: UploadFile = Form(...)):
    try:
        content_type = (
            file.content_type
            or mimetypes.guess_type(file.filename)[0]
            or "application/octet-stream"
        )

        s3_client.upload_fileobj(
            file.file,
            bucket_name,
            file.filename,
            ExtraArgs={"ACL": "public-read", "ContentType": content_type},
        )

        return {"message": f"File '{file.filename}' uploaded successfully."}
    except Exception as e:
        return {"detail": str(e)}


# -------------------------------------------------
# LIST FILES IN BUCKET
# -------------------------------------------------
@app.get("/bucket/{bucket_name}/list")
def list_files(bucket_name: str):
    try:
        resp = s3_client.list_objects_v2(Bucket=bucket_name)
        files = resp.get("Contents", [])
        return {"files": [{"Key": f["Key"]} for f in files]}
    except Exception as e:
        return {"detail": str(e)}


# -------------------------------------------------
# DELETE FILES
# -------------------------------------------------
@app.delete("/bucket/{bucket_name}/delete")
def delete_files(bucket_name: str, keys: str = Query(...)):
    try:
        key_list = keys.split(",")
        objects = [{"Key": key} for key in key_list]
        s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": objects})
        return {"message": f"Deleted {len(key_list)} files successfully."}
    except Exception as e:
        return {"detail": str(e)}


# -------------------------------------------------
# GET PUBLIC URL
# -------------------------------------------------
@app.get("/bucket/{bucket_name}/url")
def get_public_url(bucket_name: str, key: str):
    try:
        url = f"https://{bucket_name}.s3.us-east-1.amazonaws.com/{key}"
        return {"url": url}
    except Exception as e:
        return {"detail": str(e)}


# -------------------------------------------------
# DELETE BUCKET
# -------------------------------------------------
@app.delete("/bucket/{bucket_name}")
def delete_bucket(bucket_name: str):
    try:
        # Sanitize bucket name (Terraform resource labels cannot contain '-')
        resource_name = bucket_name.replace("-", "_")

        # Run targeted Terraform destroy
        subprocess.run(
            ["terraform", "init", "-input=false"], cwd=TF_DIR, check=True
          )
        subprocess.run(
            [ "terraform", "destroy", f"-target=aws_s3_bucket.files_bucket", "-auto-approve",], cwd=TF_DIR, check=True,
            )

        return {
            "message": f"S3 bucket '{bucket_name}' destroyed successfully via targeted Terraform destroy."
        }
    except subprocess.CalledProcessError as e:
        return {"detail": f"Terraform error: {e}"}
    except Exception as e:
        return {"detail": str(e)}


# -------------------------------------------------
# ROOT
# -------------------------------------------------
@app.get("/")
def root():
    return {"message": "S3 Terraform Mediator API running successfully"}
