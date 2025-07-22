# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.ecs.name
      }
    }
  }

  tags = {
    Name        = "${var.project_name}-cluster"
    Environment = var.environment
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 30

  tags = {
    Name        = "${var.project_name}-ecs-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "mcp_server" {
  name              = "/ecs/isa-mcp"
  retention_in_days = 30

  tags = {
    Name        = "${var.project_name}-mcp-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "user_service" {
  name              = "/ecs/isa-user-service"
  retention_in_days = 30

  tags = {
    Name        = "${var.project_name}-user-service-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "event_service" {
  name              = "/ecs/isa-event-service"
  retention_in_days = 30

  tags = {
    Name        = "${var.project_name}-event-service-logs"
    Environment = var.environment
  }
}

# IAM Roles
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${var.project_name}-ecs-secrets-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:isa-mcp/*"
      }
    ]
  })
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# ECR Repositories
resource "aws_ecr_repository" "mcp_server" {
  name                 = "isa-mcp"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.project_name}-mcp-repo"
    Environment = var.environment
  }
}

resource "aws_ecr_repository" "user_service" {
  name                 = "isa-user-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.project_name}-user-service-repo"
    Environment = var.environment
  }
}

resource "aws_ecr_repository" "event_service" {
  name                 = "isa-event-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.project_name}-event-service-repo"
    Environment = var.environment
  }
}

# ECS Services will be defined in separate files
# This allows for better organization and individual service management