#!/bin/bash

# AWS ECS Deployment Script for isA MCP
set -e

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PROJECT_NAME="isa-mcp"
ENVIRONMENT=${ENVIRONMENT:-"production"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    echo_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo_error "AWS CLI is not installed"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo_error "Docker is not installed"
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        echo_error "Terraform is not installed"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo_error "AWS credentials not configured"
        exit 1
    fi
    
    echo_info "Prerequisites check passed"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    echo_info "Deploying infrastructure with Terraform..."
    
    cd deployment/aws/terraform
    
    terraform init
    terraform plan -var="aws_region=$AWS_REGION" -var="environment=$ENVIRONMENT"
    
    read -p "Continue with Terraform apply? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        terraform apply -var="aws_region=$AWS_REGION" -var="environment=$ENVIRONMENT" -auto-approve
    else
        echo_warn "Terraform apply cancelled"
        exit 0
    fi
    
    cd ../../..
    echo_info "Infrastructure deployment completed"
}

# Build and push Docker images
build_and_push_images() {
    echo_info "Building and pushing Docker images..."
    
    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
    
    # Build and push MCP server
    echo_info "Building MCP server image..."
    docker build -f deployment/aws/Dockerfile.aws -t $PROJECT_NAME:latest .
    docker tag $PROJECT_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME:latest
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME:latest
    
    # Build and push User service
    echo_info "Building User service image..."
    docker build -f tools/services/user_service/Dockerfile.aws -t isa-user-service:latest .
    docker tag isa-user-service:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/isa-user-service:latest
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/isa-user-service:latest
    
    # Build and push Event service
    echo_info "Building Event service image..."
    docker build -f tools/services/event_sourcing_service/Dockerfile.aws -t isa-event-service:latest .
    docker tag isa-event-service:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/isa-event-service:latest
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/isa-event-service:latest
    
    echo_info "Docker images built and pushed successfully"
}

# Create or update ECS task definition
update_task_definition() {
    echo_info "Updating ECS task definition..."
    
    # Replace variables in task definition
    sed -e "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g" \
        -e "s/\${AWS_REGION}/$AWS_REGION/g" \
        deployment/aws/ecs-task-definition.json > /tmp/ecs-task-definition.json
    
    # Register task definition
    aws ecs register-task-definition \
        --cli-input-json file:///tmp/ecs-task-definition.json \
        --region $AWS_REGION
    
    echo_info "Task definition updated successfully"
}

# Deploy ECS services
deploy_services() {
    echo_info "Deploying ECS services..."
    
    CLUSTER_NAME="$PROJECT_NAME-cluster"
    
    # Get subnet and security group IDs from Terraform output
    cd deployment/aws/terraform
    PRIVATE_SUBNETS=$(terraform output -json private_subnet_ids | jq -r '.[]' | tr '\n' ',' | sed 's/,$//')
    ECS_SECURITY_GROUP=$(terraform output -raw ecs_security_group_id)
    TARGET_GROUP_MCP=$(terraform output -json target_group_arns | jq -r '.mcp_server')
    TARGET_GROUP_USER=$(terraform output -json target_group_arns | jq -r '.user_service')
    TARGET_GROUP_EVENT=$(terraform output -json target_group_arns | jq -r '.event_service')
    cd ../../..
    
    # Create ECS service for MCP server
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name "$PROJECT_NAME-mcp-service" \
        --task-definition "$PROJECT_NAME-task" \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNETS],securityGroups=[$ECS_SECURITY_GROUP],assignPublicIp=DISABLED}" \
        --load-balancers "targetGroupArn=$TARGET_GROUP_MCP,containerName=isa-mcp-server,containerPort=8081" \
        --region $AWS_REGION \
        --enable-execute-command || echo_warn "Service might already exist, updating instead..."
    
    # Update service if creation failed (service already exists)
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service "$PROJECT_NAME-mcp-service" \
        --task-definition "$PROJECT_NAME-task" \
        --desired-count 1 \
        --region $AWS_REGION || true
    
    echo_info "ECS services deployed successfully"
}

# Setup secrets in AWS Secrets Manager
setup_secrets() {
    echo_info "Setting up secrets in AWS Secrets Manager..."
    
    echo_warn "Please create the following secrets in AWS Secrets Manager:"
    echo "- isa-mcp/database-url"
    echo "- isa-mcp/redis-url"
    echo "- isa-mcp/jwt-secret"
    echo "- isa-mcp/supabase-url"
    echo "- isa-mcp/supabase-service-key"
    echo "- isa-mcp/auth0-domain"
    echo "- isa-mcp/auth0-audience"
    echo "- isa-mcp/auth0-client-id"
    echo "- isa-mcp/auth0-client-secret"
    echo "- isa-mcp/stripe-secret-key"
    echo "- isa-mcp/stripe-webhook-secret"
    
    read -p "Have you created all required secrets? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo_warn "Please create secrets before continuing"
        exit 1
    fi
}

# Main deployment function
main() {
    echo_info "Starting AWS deployment for $PROJECT_NAME"
    
    case "${1:-all}" in
        "prerequisites")
            check_prerequisites
            ;;
        "infrastructure")
            check_prerequisites
            deploy_infrastructure
            ;;
        "images")
            check_prerequisites
            build_and_push_images
            ;;
        "services")
            check_prerequisites
            update_task_definition
            deploy_services
            ;;
        "secrets")
            setup_secrets
            ;;
        "all")
            check_prerequisites
            setup_secrets
            deploy_infrastructure
            build_and_push_images
            update_task_definition
            deploy_services
            echo_info "Deployment completed successfully!"
            ;;
        *)
            echo_error "Usage: $0 [prerequisites|infrastructure|images|services|secrets|all]"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"