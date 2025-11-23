# crt be 3 line of code, 411

import os
import re
import random
import string
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, or_
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from passlib.context import CryptContext
import smtplib
from email.message import EmailMessage
import io
import pandas as pd
from fastapi.responses import StreamingResponse

# -------------------------
# Config
# -------------------------
DB_FILENAME = "latest.db"
DATABASE_URL = f"sqlite:///{DB_FILENAME}"

OTP_LENGTH = 6
OTP_TTL_MINUTES = 10

DEV_MODE = True

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else None
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "noreply@example.com")

# -------------------------
# DB setup
# -------------------------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# -------------------------
# Password hashing
# -------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------------
# Models
# -------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, index=True, nullable=False)
    email = Column(String(256), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(16), default="user", nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    requests = relationship("RequestItem", back_populates="user", cascade="all, delete-orphan")

class RequestItem(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(1000), nullable=False)
    status = Column(String(16), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="requests")

class OTP(Base):
    __tablename__ = "otps"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(256), index=True, nullable=False)
    code = Column(String(32), nullable=False)
    purpose = Column(String(32), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# -------------------------
# Pydantic Schemas
# -------------------------
class SignupSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field("user")

class VerifyOTPSchema(BaseModel):
    email: str
    otp: str

class LoginSchema(BaseModel):
    identifier: str
    password: str

class ForgotPasswordSchema(BaseModel):
    email: str

class ResetPasswordSchema(BaseModel):
    email: str
    otp: str
    new_password: str = Field(..., min_length=6)

class ParseSchema(BaseModel):
    username: str
    text: str

# -------------------------
# Helpers
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_valid_email(email: str) -> bool:
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return isinstance(email, str) and re.match(pattern, email) is not None

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def gen_otp(length: int = OTP_LENGTH) -> str:
    return "".join(random.choices(string.digits, k=length))

def send_email_otp(to_email: str, code: str, purpose: str = "signup"):
    subject = "Your OTP Code"
    body = f"Your OTP for {purpose} is: {code}\nThis code will expire in {OTP_TTL_MINUTES} minutes."
    if DEV_MODE:
        print(f"[DEV OTP] purpose={purpose} to={to_email} -> {code}")
        return
    if not SMTP_HOST or not SMTP_PORT or not SMTP_USER or not SMTP_PASSWORD:
        print(f"[OTP NOT SENT - SMTP not configured] {to_email} -> {code}")
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        print(f"[Error sending OTP email] {e}")

def store_otp(db: Session, email: str, purpose: str) -> OTP:
    db.query(OTP).filter(OTP.email == email, OTP.purpose == purpose, OTP.used == False).update({"used": True})
    db.commit()
    code = gen_otp()
    otp = OTP(
        email=email,
        code=code,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES),
        used=False,
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)
    send_email_otp(email, code, purpose)
    return otp

def validate_otp(db: Session, email: str, code: str, purpose: str):
    now = datetime.utcnow()
    otp = (
        db.query(OTP)
        .filter(
            OTP.email == email,
            OTP.purpose == purpose,
            OTP.code == code,
            OTP.used == False,
            OTP.expires_at > now,
        )
        .order_by(OTP.created_at.desc())
        .first()
    )
    if not otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    otp.used = True
    db.commit()
    return otp

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI(title="Cloud Provisioning - Auth + OTP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Routes
# -------------------------
@app.get("/", tags=["root"])
def root():
    return {"msg": "Cloud Provisioning API (OTP & Auth ready)", "db": DB_FILENAME}

@app.post("/signup", tags=["auth"])
def signup(payload: SignupSchema = Body(...), db: Session = Depends(get_db)):
    if not is_valid_email(payload.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    existing_user = db.query(User).filter(
        (User.username == payload.username) | (User.email == payload.email)
    ).first()
    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(status_code=400, detail="Username or email already registered")
        existing_user.hashed_password = hash_password(payload.password)
        existing_user.role = payload.role
        db.commit()
        db.refresh(existing_user)
        store_otp(db, existing_user.email, purpose="signup")
        return {"message": "Existing unverified account updated. OTP resent to email", "email": existing_user.email}
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    store_otp(db, user.email, purpose="signup")
    return {"message": "Signup successful (verify via OTP sent to email)", "email": user.email}

@app.post("/verify-otp", tags=["auth"])
def verify_signup_otp(payload: VerifyOTPSchema = Body(...), db: Session = Depends(get_db)):
    if not is_valid_email(payload.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    validate_otp(db, payload.email, payload.otp, purpose="signup")
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    db.commit()
    return {"message": "Email verified. You can now login."}

@app.post("/login", tags=["auth"])
def login(payload: LoginSchema = Body(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(
        or_(User.username == payload.identifier, User.email == payload.identifier)
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please verify your email via OTP.")
    return {"username": user.username, "role": user.role}

@app.post("/forgot-password", tags=["auth"])
def forgot_password(payload: ForgotPasswordSchema = Body(...), db: Session = Depends(get_db)):
    if not is_valid_email(payload.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        store_otp(db, payload.email, purpose="reset")
    return {"message": "If the email exists, an OTP has been sent for password reset"}

@app.post("/reset-password", tags=["auth"])
def reset_password(payload: ResetPasswordSchema = Body(...), db: Session = Depends(get_db)):
    if not is_valid_email(payload.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    validate_otp(db, payload.email, payload.otp, purpose="reset")
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = hash_password(payload.new_password)
    user.is_verified = True
    db.commit()
    return {"message": "Password reset successful"}

# ----------------- NEW -----------------
@app.post("/check-email", tags=["auth"])
def check_email(payload: ForgotPasswordSchema = Body(...), db: Session = Depends(get_db)):
    if not is_valid_email(payload.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    user = db.query(User).filter(User.email == payload.email).first()
    return {"exists": bool(user)}
# ----------------------------------

@app.post("/parse", tags=["app"])
def create_request(payload: ParseSchema = Body(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    item = RequestItem(text=payload.text.strip(), status="pending", user_id=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "status": item.status}

@app.get("/admin/requests", tags=["admin"])
def admin_list_requests(db: Session = Depends(get_db)):
    rows = db.query(RequestItem).order_by(RequestItem.created_at.asc()).all()
    return [
        {
            "id": r.id,
            "username": r.user.username if r.user else None,
            "text": r.text,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]

@app.get("/user/requests", tags=["app"])
def user_requests(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    rows = sorted(user.requests, key=lambda r: r.created_at)
    return [{"id": r.id, "text": r.text, "status": r.status, "created_at": r.created_at.isoformat()} for r in rows]

@app.post("/admin/update/{request_id}", tags=["admin"])
def admin_update_request(request_id: int, status: str = "approve", db: Session = Depends(get_db)):
    if status not in ("approve", "reject", "pending"):
        raise HTTPException(status_code=400, detail="Invalid status")
    r = db.query(RequestItem).filter(RequestItem.id == request_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    r.status = status
    db.commit()
    return {"id": r.id, "status": r.status}

# ----------------- Export Endpoints -----------------
@app.get("/export/admin", tags=["export"])
def export_admin(admin_username: str = "admin", format: str = "csv", status: str = "all", db: Session = Depends(get_db)):
    rows = db.query(RequestItem).order_by(RequestItem.created_at.asc()).all()
    data = []
    for r in rows:
        if status.lower() != "all" and r.status.lower() != status.lower():
            continue
        data.append({
            "SNO": None,
            "Username": r.user.username if r.user else None,
            "Request": r.text,
            "Status": r.status,
            "Timestamp": r.created_at.strftime("%d-%m-%Y_%H-%M-%S")[:-1]
        })
    for idx, d in enumerate(data, start=1):
        d["SNO"] = idx
    df = pd.DataFrame(data)
    filename = f"admin_requests_{admin_username}_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}"
    if format == "csv":
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
        return response
    else:
        stream = io.BytesIO()
        with pd.ExcelWriter(stream, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        stream.seek(0)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}.xlsx"
        return response


@app.get("/export/user", tags=["export"])
def export_user(username: str, format: str = "csv", db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    rows = sorted(user.requests, key=lambda r: r.created_at)
    data = [{
        "SNO": idx + 1,
        "Request": r.text,
        "Status": r.status,
        "Timestamp": r.created_at.strftime("%d-%m-%Y_%H-%M-%S")[:-1]
    } for idx, r in enumerate(rows)]
    df = pd.DataFrame(data)
    filename = f"user_requests_{username}_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}"
    if format == "csv":
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
        return response
    else:
        stream = io.BytesIO()
        with pd.ExcelWriter(stream, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        stream.seek(0)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}.xlsx"
        return response

    