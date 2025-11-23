# Intent-Based Cloud Resource Provisioning
## Overview
This project implements an interactive cloud management system where users can request and manage AWS resources using natural language commands.
This system intelligently interprets user intent and provisions cloud resources such as EC2 and S3 using Terraform automation, FastAPI backends, and Streamlit dashboards.

Users can request resources in plain English (e.g., "Give me an EC2 instance"), while admins manage approvals and monitor all activity.
The system dynamically generates IaC, deploys resources on AWS, and even provides a live, interactive SSH terminal for EC2 instances — all within the browser.

## Features
### 1. User Authentication & RBAC
- Register as User or Admin
- OTP verification (sent to developer console)
- Unique username, email, and password validation
- Forgot password & reset support

### 2. Natural Language Cloud Requests
- Example: "Give me an S3 bucket"
- Backend parses request text
- Users can submit and track requests

### 3. Admin Panel
- View all resource requests
- Approve / Reject / Keep pending
- Filter by request status
- Export all entries as CSV or Excel

### 4. EC2 Provisioning
- Terraform automatically launches EC2
- Backend retrieves Public IP
- Live xTerm SSH terminal (supports nano, top, apt, sudo, arrow keys, etc.)
- Destroy instance instantly using Terraform target destroy

### 5. S3 Bucket Management
- Create bucket via dynamic Terraform file
- Upload files (public-read enabled)
- List contents
- View files using public URL
- Delete files
- Destroy bucket

### 6. Logging & Export
- Every action logged
- Requests and audit data exportable

## Tech Stack
- Frontend: Streamlit
- Backend: FastAPI
- Cloud SDK: Boto3
- IaC: Terraform
- SSH Terminal: AsyncSSH + xTerm.js
- DB Layer: SQLAlchemy (for users & requests)

## Available Scripts
### Frontend Dashboards
`dashboard_main.py` → Login, Register, OTP, User & Admin panels

`dashboard_ec2.py` → EC2 Live SSH control panel

`dashboard_s3.py` → S3 Bucket UI

### Backends

`backend_main.py` → Auth, NLP parsing, Request system

`backend_ec2.py` → EC2 Terraform + SSH

`backend_s3.py` → S3 Terraform + file operations

### Automation

`run-all.py` → Starts all Streamlit and FastAPI servers

`stop-all.py` → Stops all running project servers


## How to Run

1. Clone the repo

2. Install all dependencies `pip install -r requirements.txt`

3. Configure AWS credentials

4. Run all services:
`python run-all.py`

5. Access dashboards:
   - Main Dashboard → `http://localhost:8501`
   - EC2 Dashboard → `http://localhost:8502`
   - S3 Dashboard → `http://localhost:8503`

6. Stop all services:
`python stop-all.py`


## Workflow Summary

1. User submits natural-language request
2. Admin approves
3. Based on request:
   - EC2 → Terraform creates instance → Streamlit opens live terminal
   - S3 → Terraform creates bucket → User uploads/manages files
4. User can destroy allocated resources
5. All actions logged and exportable

[![Workflow Architecture](https://github.com/Krish1908/Intent-Based-Cloud-Resource-Provisioning/blob/main/Workflow%20Architecture%2004.png?raw=true)](https://github.com/Krish1908/Intent-Based-Cloud-Resource-Provisioning/blob/main/Workflow%20Architecture%2004.png?raw=true)

