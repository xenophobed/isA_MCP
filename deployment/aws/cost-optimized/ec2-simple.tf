terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "key_name" {
  description = "EC2 Key Pair name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "isa-mcp"
}

# 获取最新的 Amazon Linux 2 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# 获取默认 VPC
data "aws_vpc" "default" {
  default = true
}

# 获取默认子网
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# 安全组 - ALB
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb-"
  vpc_id      = data.aws_vpc.default.id

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # 出站流量
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# 安全组 - EC2 Services
resource "aws_security_group" "ec2_services" {
  name_prefix = "${var.project_name}-ec2-"
  vpc_id      = data.aws_vpc.default.id

  # SSH 访问
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # ALB to EC2 services
  ingress {
    from_port       = 8080
    to_port         = 8082
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # User Service
  ingress {
    from_port       = 8100
    to_port         = 8101
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Internal service communication
  ingress {
    from_port = 8080
    to_port   = 8101
    protocol  = "tcp"
    self      = true
  }

  # Model service communication
  ingress {
    from_port = 8082
    to_port   = 8082
    protocol  = "tcp"
    self      = true
  }

  # 出站流量
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ec2-sg"
  }
}

# IAM 角色用于 EC2
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# IAM 策略 - 允许访问 Secrets Manager
resource "aws_iam_role_policy" "secrets_policy" {
  name = "${var.project_name}-secrets-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:${var.project_name}/*"
      }
    ]
  })
}

# IAM 实例配置文件
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# 用户数据脚本将在每个实例中单独定义

# EC2 Instance 1 - Agent Service
resource "aws_instance" "ec2_agent_service" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.small"
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.ec2_services.id]
  subnet_id              = data.aws_subnets.default.ids[0]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  user_data = base64encode(templatefile("${path.module}/user_data_agent.sh", {
    project_name = var.project_name
    aws_region   = var.aws_region
    mcp_private_ip = aws_instance.ec2_mcp_service.private_ip
    model_private_ip = aws_instance.ec2_model_service.private_ip
  }))

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }

  tags = {
    Name = "${var.project_name}-agent-service"
    Service = "agent"
  }

  depends_on = [aws_instance.ec2_mcp_service, aws_instance.ec2_model_service]
}

# EC2 Instance 2 - MCP Service (with UI support)
resource "aws_instance" "ec2_mcp_service" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.medium"  # More resources for UI + Playwright
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.ec2_services.id]
  subnet_id              = data.aws_subnets.default.ids[1]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  user_data = base64encode(templatefile("${path.module}/user_data_mcp.sh", {
    project_name = var.project_name
    aws_region   = var.aws_region
    model_private_ip = aws_instance.ec2_model_service.private_ip
  }))

  root_block_device {
    volume_type = "gp3"
    volume_size = 30  # More storage for UI components
    encrypted   = true
  }

  tags = {
    Name = "${var.project_name}-mcp-service"
    Service = "mcp"
  }

  depends_on = [aws_instance.ec2_model_service]
}

# EC2 Instance 3 - Model Service  
resource "aws_instance" "ec2_model_service" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.small"
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.ec2_services.id]
  subnet_id              = data.aws_subnets.default.ids[2]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  user_data = base64encode(templatefile("${path.module}/user_data_model.sh", {
    project_name = var.project_name
    aws_region   = var.aws_region
  }))

  root_block_device {
    volume_type = "gp3"
    volume_size = 25  # Some storage for models
    encrypted   = true
  }

  tags = {
    Name = "${var.project_name}-model-service"
    Service = "model"
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.default.ids

  enable_deletion_protection = false

  tags = {
    Name = "${var.project_name}-alb"
  }
}

# Target Groups
resource "aws_lb_target_group" "agent_service" {
  name     = "${var.project_name}-agent-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
}

resource "aws_lb_target_group" "mcp_service" {
  name     = "${var.project_name}-mcp-tg"
  port     = 8081
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
}

resource "aws_lb_target_group" "model_service" {
  name     = "${var.project_name}-model-tg"
  port     = 8082
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
}

# Additional Target Groups for User and Event services
resource "aws_lb_target_group" "user_service" {
  name     = "${var.project_name}-user-tg"
  port     = 8100
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
}

resource "aws_lb_target_group" "event_service" {
  name     = "${var.project_name}-event-tg"
  port     = 8101
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
}

# Target Group Attachments
resource "aws_lb_target_group_attachment" "agent_service" {
  target_group_arn = aws_lb_target_group.agent_service.arn
  target_id        = aws_instance.ec2_agent_service.id
  port             = 8080
}

resource "aws_lb_target_group_attachment" "mcp_service" {
  target_group_arn = aws_lb_target_group.mcp_service.arn
  target_id        = aws_instance.ec2_mcp_service.id
  port             = 8081
}

resource "aws_lb_target_group_attachment" "user_service" {
  target_group_arn = aws_lb_target_group.user_service.arn
  target_id        = aws_instance.ec2_mcp_service.id
  port             = 8100
}

resource "aws_lb_target_group_attachment" "event_service" {
  target_group_arn = aws_lb_target_group.event_service.arn
  target_id        = aws_instance.ec2_mcp_service.id
  port             = 8101
}

resource "aws_lb_target_group_attachment" "model_service" {
  target_group_arn = aws_lb_target_group.model_service.arn
  target_id        = aws_instance.ec2_model_service.id
  port             = 8082
}

# ALB Listener
resource "aws_lb_listener" "main" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.agent_service.arn
  }
}

# Listener Rules for routing
resource "aws_lb_listener_rule" "mcp_rule" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.mcp_service.arn
  }

  condition {
    path_pattern {
      values = ["/mcp/*"]
    }
  }
}

resource "aws_lb_listener_rule" "user_api_rule" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 150

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.user_service.arn
  }

  condition {
    path_pattern {
      values = ["/api/users/*", "/api/user/*"]
    }
  }
}

resource "aws_lb_listener_rule" "event_api_rule" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 160

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.event_service.arn
  }

  condition {
    path_pattern {
      values = ["/api/events/*", "/api/event/*"]
    }
  }
}

resource "aws_lb_listener_rule" "model_api_rule" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.model_service.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/*"]
    }
  }
}

resource "aws_lb_listener_rule" "model_docs_rule" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 300

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.model_service.arn
  }

  condition {
    path_pattern {
      values = ["/docs", "/openapi.json", "/redoc"]
    }
  }
}

resource "aws_lb_listener_rule" "agent_api_rule" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 400

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.agent_service.arn
  }

  condition {
    path_pattern {
      values = ["/api/chat/*", "/api/agent/*", "/api/billing/*", "/api/tracing/*", "/api/auth/*"]
    }
  }
}

# 输出
output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "ec2_instances" {
  description = "EC2 instance information"
  value = {
    agent_service = {
      id         = aws_instance.ec2_agent_service.id
      private_ip = aws_instance.ec2_agent_service.private_ip
      public_ip  = aws_instance.ec2_agent_service.public_ip
    }
    mcp_service = {
      id         = aws_instance.ec2_mcp_service.id
      private_ip = aws_instance.ec2_mcp_service.private_ip
      public_ip  = aws_instance.ec2_mcp_service.public_ip
    }
    model_service = {
      id         = aws_instance.ec2_model_service.id
      private_ip = aws_instance.ec2_model_service.private_ip
      public_ip  = aws_instance.ec2_model_service.public_ip
    }
  }
}

output "ssh_commands" {
  description = "SSH commands for each instance"
  value = {
    agent_service = "ssh -i /Users/xenodennis/Documents/Fun/isa_key.pem ec2-user@${aws_instance.ec2_agent_service.public_ip}"
    mcp_service   = "ssh -i /Users/xenodennis/Documents/Fun/isa_key.pem ec2-user@${aws_instance.ec2_mcp_service.public_ip}"
    model_service = "ssh -i /Users/xenodennis/Documents/Fun/isa_key.pem ec2-user@${aws_instance.ec2_model_service.public_ip}"
  }
}

output "api_base_url" {
  description = "Base URL for API access"
  value       = "http://${aws_lb.main.dns_name}"
}

output "service_urls" {
  description = "Individual service URLs"
  value = {
    agent_api    = "http://${aws_lb.main.dns_name}/"
    agent_chat   = "http://${aws_lb.main.dns_name}/api/chat"
    mcp_api      = "http://${aws_lb.main.dns_name}/mcp/"
    user_api     = "http://${aws_lb.main.dns_name}/api/users"
    event_api    = "http://${aws_lb.main.dns_name}/api/events"
    model_api    = "http://${aws_lb.main.dns_name}/api/v1"
    model_docs   = "http://${aws_lb.main.dns_name}/docs"
    health_check = "http://${aws_lb.main.dns_name}/health"
  }
}

output "service_discovery" {
  description = "Internal service discovery URLs (for environment configuration)"
  value = {
    agent_private_ip = aws_instance.ec2_agent_service.private_ip
    mcp_private_ip   = aws_instance.ec2_mcp_service.private_ip
    model_private_ip = aws_instance.ec2_model_service.private_ip
    mcp_url         = "http://${aws_instance.ec2_mcp_service.private_ip}:8081/mcp/"
    model_url       = "http://${aws_instance.ec2_model_service.private_ip}:8082"
  }
}