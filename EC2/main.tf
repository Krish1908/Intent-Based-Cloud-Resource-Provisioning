provider "aws" {
  region     = "us-east-1"
  access_key = "your-access-key"  
  secret_key = "your-secret-key"
}

resource "aws_vpc" "vpc-1" {
  cidr_block       = "10.0.0.0/16"
  instance_tenancy = "default"

  tags = {
    Name = "terraform-test-vpc"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.vpc-1.id

  tags = {
    Name = "terraform-test-gateway"
  }
}


resource "aws_route_table" "test-routetable" {
  vpc_id = aws_vpc.vpc-1.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  route {
    ipv6_cidr_block        = "::/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "terraform-test-gateway"
  }
}

resource "aws_subnet" "subnet-1" {
  vpc_id     = aws_vpc.vpc-1.id
  cidr_block = "10.0.1.0/24"
  availability_zone = "us-east-1a"  # ✅ Add this

  tags = {
    Name = "terraform-test-subnet"
  }
}

resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.subnet-1.id
  route_table_id = aws_route_table.test-routetable.id
}



resource "aws_security_group" "allow_tls" {
  name        = "allow_tls"
  description = "Allow TLS inbound traffic and all outbound traffic"
  vpc_id      = aws_vpc.vpc-1.id

  tags = {
    Name = "allow_tls"
  }
}

resource "aws_vpc_security_group_ingress_rule" "allow_https" {
  security_group_id = aws_security_group.allow_tls.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  ip_protocol       = "tcp"
  to_port           = 443
}

resource "aws_vpc_security_group_ingress_rule" "allow_http_ipv4" {
  security_group_id = aws_security_group.allow_tls.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  ip_protocol       = "tcp"
  to_port           = 80
}

resource "aws_vpc_security_group_ingress_rule" "allow_ssh_ipv4" {
  security_group_id = aws_security_group.allow_tls.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 22
  ip_protocol       = "tcp"
  to_port           = 22
}

resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.allow_tls.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}


resource "aws_network_interface" "test-network" {
  subnet_id       = aws_subnet.subnet-1.id
  private_ips     = ["10.0.1.50"]
  security_groups = [aws_security_group.allow_tls.id]
}

resource "aws_instance" "krish-crp" {
  ami                    = "ami-0360c520857e3138f" # Ubuntu 20.04 LTS (example for us-east-1)
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.subnet-1.id
  vpc_security_group_ids = [aws_security_group.allow_tls.id]
  key_name               = "krish-crp"
  
  associate_public_ip_address = true
  

   tags = {
     Name = "krish-crp"

   }
}


output "public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_instance.krish-crp.public_ip
}

# MANUAL WORKS
# 1. CREATE A KEY PAIR

# AUTOMATED WORKS
# 1. VPC, INTERNET GATEWAY, SUBNET, ROUTE TABLE
# 2. SECURITY GROUPS TO ALLOW SSH 22, HTTP 80, HTTPS 443
