#!/bin/bash

# 简化的 AWS EC2 部署脚本
set -e

AWS_REGION=${AWS_REGION:-"us-east-1"}
PROJECT_NAME="isa-mcp"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查先决条件
check_prerequisites() {
    echo_info "检查先决条件..."
    
    # 检查 AWS CLI
    if ! command -v aws &> /dev/null; then
        echo_error "请先安装 AWS CLI"
        exit 1
    fi
    
    # 检查 AWS 凭证
    if ! aws sts get-caller-identity &> /dev/null; then
        echo_error "请先配置 AWS 凭证: aws configure"
        exit 1
    fi
    
    # 检查 Terraform
    if ! command -v terraform &> /dev/null; then
        echo_error "请先安装 Terraform"
        exit 1
    fi
    
    echo_info "先决条件检查通过"
}

# 创建 EC2 密钥对
create_key_pair() {
    local key_name="${PROJECT_NAME}-key"
    
    echo_info "检查 EC2 密钥对..."
    
    if aws ec2 describe-key-pairs --key-names "$key_name" --region "$AWS_REGION" &>/dev/null; then
        echo_info "密钥对 $key_name 已存在"
    else
        echo_info "创建新的密钥对: $key_name"
        aws ec2 create-key-pair \
            --key-name "$key_name" \
            --region "$AWS_REGION" \
            --query 'KeyMaterial' \
            --output text > ~/.ssh/"$key_name".pem
        
        chmod 400 ~/.ssh/"$key_name".pem
        echo_info "密钥对已保存到: ~/.ssh/$key_name.pem"
    fi
    
    echo "$key_name"
}

# 部署基础设施
deploy_infrastructure() {
    echo_info "部署 EC2 基础设施..."
    
    local key_name=$(create_key_pair)
    
    cd deployment/aws/cost-optimized
    
    # 初始化 Terraform
    terraform init
    
    # 规划部署
    terraform plan \
        -var="aws_region=$AWS_REGION" \
        -var="key_name=$key_name" \
        -var="project_name=$PROJECT_NAME"
    
    # 确认部署
    read -p "继续部署? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        terraform apply \
            -var="aws_region=$AWS_REGION" \
            -var="key_name=$key_name" \
            -var="project_name=$PROJECT_NAME" \
            -auto-approve
    else
        echo_warn "部署已取消"
        exit 0
    fi
    
    # 获取输出
    local public_ip=$(terraform output -raw public_ip)
    local ssh_command=$(terraform output -raw ssh_command)
    
    echo_info "部署完成！"
    echo_info "公网 IP: $public_ip"
    echo_info "SSH 连接: $ssh_command"
    
    cd ../../..
}

# 构建和推送镜像
build_and_push_images() {
    echo_info "构建和推送 Docker 镜像..."
    
    local aws_account_id=$(aws sts get-caller-identity --query Account --output text)
    
    # 创建 ECR 仓库
    for repo in "isa-mcp" "isa-user-service" "isa-event-service"; do
        aws ecr create-repository \
            --repository-name "$repo" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            2>/dev/null || echo_warn "仓库 $repo 可能已存在"
    done
    
    # 登录 ECR
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$aws_account_id.dkr.ecr.$AWS_REGION.amazonaws.com"
    
    # 构建 MCP 服务镜像
    echo_info "构建 MCP 服务镜像..."
    docker build -f deployment/aws/Dockerfile.aws -t isa-mcp:latest .
    docker tag isa-mcp:latest "$aws_account_id.dkr.ecr.$AWS_REGION.amazonaws.com/isa-mcp:latest"
    docker push "$aws_account_id.dkr.ecr.$AWS_REGION.amazonaws.com/isa-mcp:latest"
    
    # 构建用户服务镜像
    echo_info "构建用户服务镜像..."
    docker build -f tools/services/user_service/Dockerfile -t isa-user-service:latest .
    docker tag isa-user-service:latest "$aws_account_id.dkr.ecr.$AWS_REGION.amazonaws.com/isa-user-service:latest"
    docker push "$aws_account_id.dkr.ecr.$AWS_REGION.amazonaws.com/isa-user-service:latest"
    
    # 构建事件服务镜像
    echo_info "构建事件服务镜像..."
    docker build -f tools/services/event_sourcing_service/Dockerfile -t isa-event-service:latest .
    docker tag isa-event-service:latest "$aws_account_id.dkr.ecr.$AWS_REGION.amazonaws.com/isa-event-service:latest"
    docker push "$aws_account_id.dkr.ecr.$AWS_REGION.amazonaws.com/isa-event-service:latest"
    
    echo_info "所有镜像已推送到 ECR"
}

# 部署到 EC2
deploy_to_ec2() {
    echo_info "部署服务到 EC2..."
    
    cd deployment/aws/cost-optimized
    local public_ip=$(terraform output -raw public_ip)
    local key_name="${PROJECT_NAME}-key"
    
    echo_info "等待 EC2 实例完全启动..."
    sleep 60
    
    echo_info "连接到 EC2 实例并部署服务..."
    ssh -i ~/.ssh/"$key_name".pem -o StrictHostKeyChecking=no ec2-user@"$public_ip" << 'EOF'
        cd /home/ec2-user/isa-mcp
        
        # 更新 Docker Compose 文件中的镜像地址
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        sed -i "s/your-account/$AWS_ACCOUNT_ID/g" docker-compose.yml
        
        # 加载密钥
        ./load-secrets.sh
        
        # 部署服务
        ./deploy.sh
EOF
    
    echo_info "部署完成！"
    echo_info "访问地址: http://$public_ip"
    echo_info "SSH 连接: ssh -i ~/.ssh/$key_name.pem ec2-user@$public_ip"
    
    cd ../../..
}

# 显示成本信息
show_cost_info() {
    echo_info "成本信息:"
    echo "- EC2 t3.small: ~$15/月"
    echo "- EBS 20GB: ~$2/月"
    echo "- 数据传输: ~$3-8/月"
    echo "- 总计: ~$20-25/月"
    echo ""
    echo_warn "相比原方案节省 80%+ 成本"
}

# 主函数
main() {
    echo_info "开始简化 AWS 部署"
    show_cost_info
    
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
        "deploy")
            deploy_to_ec2
            ;;
        "all")
            check_prerequisites
            deploy_infrastructure
            build_and_push_images
            deploy_to_ec2
            echo_info "🎉 完整部署成功！"
            ;;
        *)
            echo_error "用法: $0 [prerequisites|infrastructure|images|deploy|all]"
            exit 1
            ;;
    esac
}

main "$@"