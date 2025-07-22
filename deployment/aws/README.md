# AWS Deployment Guide for isA MCP

这个文档指导您如何将 isA MCP 系统部署到 AWS 云平台。

## 架构概览

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Internet  │───▶│  CloudFront  │───▶│  Load Balancer  │
└─────────────┘    └──────────────┘    └─────────────────┘
                                              │
                         ┌────────────────────┼────────────────────┐
                         │                    │                    │
                    ┌─────▼──────┐    ┌───────▼──────┐    ┌───────▼──────┐
                    │ MCP Server │    │ User Service │    │Event Service │
                    │   (ECS)    │    │    (ECS)     │    │    (ECS)     │
                    └────────────┘    └──────────────┘    └──────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
              ┌─────▼──────┐         ┌───────▼──────┐         ┌───────▼──────┐
              │  Supabase  │         │   Neo4j      │         │ Cloudflare   │
              │ (Database) │         │  (Graph DB)  │         │    (R2)      │
              └────────────┘         └──────────────┘         └──────────────┘
```

## 前置要求

1. **AWS 账户和 CLI 配置**
   ```bash
   aws configure
   ```

2. **必要工具安装**
   - AWS CLI v2
   - Docker
   - Terraform
   - jq

3. **域名配置**
   - 在 Route 53 中配置您的域名
   - 或确保您的域名 DNS 指向 AWS

## 快速部署

### 1. 克隆和配置

```bash
# 进入项目目录
cd /Users/xenodennis/Documents/Fun/isA_MCP

# 复制环境变量模板
cp deployment/aws/.env.aws.template deployment/aws/.env.aws

# 编辑环境变量文件，填入实际值
nano deployment/aws/.env.aws
```

### 2. 设置 AWS 密钥

```bash
# 创建所有必需的密钥（占位符值）
./deployment/aws/secrets-setup.sh setup

# 从环境文件加载实际密钥值
./deployment/aws/secrets-setup.sh load deployment/aws/.env.aws
```

### 3. 一键部署

```bash
# 完整部署（推荐首次使用）
./deployment/aws/deploy.sh all
```

## 分步部署

如果您想要更细粒度的控制，可以分步执行：

### 1. 检查前置条件
```bash
./deployment/aws/deploy.sh prerequisites
```

### 2. 部署基础设施
```bash
./deployment/aws/deploy.sh infrastructure
```

### 3. 构建和推送 Docker 镜像
```bash
./deployment/aws/deploy.sh images
```

### 4. 部署 ECS 服务
```bash
./deployment/aws/deploy.sh services
```

## 配置文件说明

### 主要配置文件

- `docker-compose.aws.yml` - AWS 环境的 Docker Compose 配置
- `Dockerfile.aws` - 优化的 AWS 生产环境 Dockerfile
- `ecs-task-definition.json` - ECS 任务定义
- `terraform/` - 基础设施即代码

### Terraform 模块

- `main.tf` - VPC, 子网, 安全组
- `ecs.tf` - ECS 集群和 ECR 仓库
- `alb.tf` - 应用负载均衡器和 SSL 证书

## 服务配置

### MCP 服务器 (端口 8081)
- 支持 Playwright 有头浏览器
- 包含虚拟显示器 (Xvfb)
- 路径: `/mcp/*`

### 用户管理服务 (端口 8100)
- Auth0 集成
- Stripe 支付处理
- 路径: `/api/users/*`, `/api/auth/*`, `/api/billing/*`

### 事件溯源服务 (端口 8101)
- 事件存储和分析
- 路径: `/api/events/*`, `/api/analytics/*`

## 监控和日志

### CloudWatch 日志
- `/ecs/isa-mcp` - MCP 服务器日志
- `/ecs/isa-user-service` - 用户服务日志  
- `/ecs/isa-event-service` - 事件服务日志

### 健康检查
所有服务都配置了健康检查端点 `/health`

## 安全配置

### 网络安全
- VPC 私有子网部署
- 安全组限制访问
- NAT 网关用于外网访问

### 密钥管理
- AWS Secrets Manager 存储敏感信息
- IAM 角色最小权限原则
- SSL/TLS 加密传输

## 扩展和优化

### 自动扩展
```bash
# 在 Terraform 中配置 ECS 服务自动扩展
# 基于 CPU 或内存使用率
```

### 成本优化
- 使用 Spot 实例（开发环境）
- 配置合适的 CPU/内存资源
- 启用 CloudWatch 成本监控

### 性能优化
- CloudFront CDN 加速
- ElastiCache Redis 缓存
- RDS 读写分离

## 故障排除

### 常见问题

1. **ECS 任务启动失败**
   ```bash
   aws ecs describe-tasks --cluster isa-mcp-cluster --tasks task-id
   ```

2. **健康检查失败**
   ```bash
   aws logs tail /ecs/isa-mcp --follow
   ```

3. **负载均衡器 502 错误**
   - 检查安全组配置
   - 确认服务健康状态
   - 查看目标组健康检查

### 日志查看
```bash
# 查看 MCP 服务日志
aws logs tail /ecs/isa-mcp --follow

# 查看用户服务日志
aws logs tail /ecs/isa-user-service --follow

# 查看事件服务日志
aws logs tail /ecs/isa-event-service --follow
```

## 更新和维护

### 代码更新
```bash
# 重新构建和部署镜像
./deployment/aws/deploy.sh images

# 重启服务以使用新镜像
aws ecs update-service --cluster isa-mcp-cluster --service isa-mcp-mcp-service --force-new-deployment
```

### 基础设施更新
```bash
cd deployment/aws/terraform
terraform plan
terraform apply
```

## 成本估算

基于 us-east-1 区域的估算成本（每月）：

- **ECS Fargate**: ~$50-100
- **ALB**: ~$25
- **NAT Gateway**: ~$45
- **CloudWatch Logs**: ~$5-10
- **总计**: ~$125-180/月

*实际成本取决于使用量和资源配置*

## 支持

如有问题，请检查：
1. AWS CloudWatch 日志
2. ECS 服务状态
3. 负载均衡器健康检查
4. 安全组和网络配置

## 清理资源

要删除所有 AWS 资源：

```bash
cd deployment/aws/terraform
terraform destroy
```

**注意**: 这将删除所有基础设施，请确保已备份重要数据。