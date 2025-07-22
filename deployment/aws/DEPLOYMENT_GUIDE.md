# 🚀 Complete Deployment Guide for isA System

## Team Roles & Responsibilities

### 👨‍💻 Frontend Developer
**Responsible for**: Website + AI Apps (Vercel deployment)
**Dependencies**: Backend APIs must be running
**Files needed**: Frontend environment variables

### 🛠️ Backend Developer  
**Responsible for**: AWS EC2 services deployment
**Dependencies**: Infrastructure must be ready
**Files needed**: Backend configurations, Docker files

### 🏗️ DevOps/Infrastructure
**Responsible for**: AWS infrastructure, networking, security
**Dependencies**: AWS account setup
**Files needed**: Terraform configurations

## 📋 Deployment Checklist

### Pre-Deployment Setup ✅

#### 1. External Services Setup
- [ ] **Supabase Cloud**: Project created (✅ Done: isa_staging)
- [ ] **Neo4j Aura**: Database instance created
- [ ] **Auth0**: Application configured
- [ ] **Stripe**: Webhook endpoints configured
- [ ] **AWS**: Account setup with billing (✅ Done)
- [ ] **Vercel**: Account setup for frontend deployment

#### 2. DNS & Domains
- [ ] **Domain purchased**: (e.g., yourdomain.com)
- [ ] **AWS Route53**: Hosted zone created
- [ ] **Subdomains planned**:
  - `api.yourdomain.com` → AWS ALB
  - `app.yourdomain.com` → Vercel AI Apps
  - `www.yourdomain.com` → Vercel Website

## 🏗️ Phase 1: Infrastructure Deployment (DevOps)

### Step 1: Update Terraform Configuration
```bash
cd deployment/aws/terraform

# Update variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values:
# domain_name = "yourdomain.com"
# project_name = "isa-mcp"
# aws_region = "us-east-1"
```

### Step 2: Deploy Infrastructure
```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Deploy (will create VPC, ALB, Security Groups)
terraform apply
```

### Step 3: Get Infrastructure Outputs
```bash
# Get ALB DNS name for frontend configuration
terraform output alb_dns_name

# Get private IPs for service configuration
terraform output ec2_private_ips
```

## 🔧 Phase 2: Backend Services Deployment

### Step 1: Deploy EC2-1 (MCP Services)
```bash
# SSH into EC2-1
ssh -i ~/.ssh/isa-mcp-key.pem ec2-user@EC2-1-PUBLIC-IP

# Clone repository
git clone https://github.com/your-org/isA_MCP.git
cd isA_MCP

# Copy environment configuration
cp deployment/aws/.env.aws .env

# Update service URLs with actual private IPs
sed -i 's/10.0.11.100/ACTUAL-EC2-2-PRIVATE-IP/' .env
sed -i 's/10.0.12.100/ACTUAL-EC2-3-PRIVATE-IP/' .env

# Install Docker and run services
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo usermod -a -G docker ec2-user

# Exit and reconnect for docker permissions
exit
ssh -i ~/.ssh/isa-mcp-key.pem ec2-user@EC2-1-PUBLIC-IP

# Deploy services
docker-compose -f deployment/aws/docker-compose.aws.yml up -d
```

### Step 2: Deploy EC2-2 (Model Service)
```bash
# SSH into EC2-2
ssh -i ~/.ssh/isa-mcp-key.pem ec2-user@EC2-2-PUBLIC-IP

# Clone and setup
git clone https://github.com/your-org/isA_MCP.git
cd isA_MCP

# Update environment with private IPs
cp deployment/aws/.env.model .env
# Edit .env with actual private IPs

# Deploy model service
docker-compose -f deployment/model/docker-compose.yml up -d
```

### Step 3: Deploy EC2-3 (Agent Service)
```bash
# SSH into EC2-3
ssh -i ~/.ssh/isa-mcp-key.pem ec2-user@EC2-3-PUBLIC-IP

# Clone and setup
git clone https://github.com/your-org/isA_MCP.git
cd isA_MCP

# Update environment with private IPs
cp deployment/aws/.env.agent .env
# Edit .env with actual private IPs

# Deploy agent service
docker-compose -f deployment/agent/docker-compose.yml up -d
```

## 🌐 Phase 3: Frontend Deployment (Frontend Developer)

### Step 1: Configure Environment Variables

#### For AI Apps (Vercel)
Create `.env.local` in your AI apps repository:
```bash
# API Base URL (use ALB DNS name or custom domain)
NEXT_PUBLIC_API_BASE_URL=https://your-alb-dns-name.elb.amazonaws.com
# Or: NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com

# Service-specific URLs
NEXT_PUBLIC_AGENT_API_URL=https://api.yourdomain.com/api/agent
NEXT_PUBLIC_MCP_API_URL=https://api.yourdomain.com/api/mcp
NEXT_PUBLIC_USER_API_URL=https://api.yourdomain.com/api/users
NEXT_PUBLIC_EVENT_API_URL=https://api.yourdomain.com/api/events
NEXT_PUBLIC_MODEL_API_URL=https://api.yourdomain.com/api/models

# Auth0 Configuration
NEXT_PUBLIC_AUTH0_DOMAIN=your-domain.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret
NEXT_PUBLIC_AUTH0_AUDIENCE=your-auth0-audience

# Stripe Configuration
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# Feature Flags
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_DEBUG_MODE=false
```

#### For Website (Vercel)
Create `.env.local` in your website repository:
```bash
# Simplified config for website
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
NEXT_PUBLIC_USER_API_URL=https://api.yourdomain.com/api/users

# Auth0 (same as AI apps)
NEXT_PUBLIC_AUTH0_DOMAIN=your-domain.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret
```

### Step 2: Deploy to Vercel
```bash
# Deploy AI Apps
cd ai-apps-repository
vercel --prod

# Deploy Website  
cd website-repository
vercel --prod
```

### Step 3: Configure Custom Domains (Optional)
```bash
# Add custom domain in Vercel dashboard
# Point DNS to Vercel:
# app.yourdomain.com → Vercel AI Apps
# www.yourdomain.com → Vercel Website

# Point API subdomain to AWS:
# api.yourdomain.com → AWS ALB
```

## 🔧 Phase 4: Service Integration Testing

### Step 1: Backend Health Checks
```bash
# Test each service individually
curl http://ALB-DNS-NAME/api/users/health
curl http://ALB-DNS-NAME/api/events/health  
curl http://ALB-DNS-NAME/api/mcp/health
curl http://ALB-DNS-NAME/api/models/health
curl http://ALB-DNS-NAME/api/agent/health
```

### Step 2: Service Communication Tests
```bash
# Test Agent → MCP communication
curl -X POST http://ALB-DNS-NAME/api/agent/test-mcp

# Test MCP → Model communication
curl -X POST http://ALB-DNS-NAME/api/mcp/test-model

# Test User authentication flow
curl -X POST http://ALB-DNS-NAME/api/users/test-auth
```

### Step 3: Frontend Integration Tests
```bash
# Test frontend → backend communication
# Visit your Vercel apps and test:
# 1. User login (Auth0)
# 2. AI agent interactions
# 3. Model inference calls
# 4. Event logging
```

## 📊 Monitoring Setup

### Step 1: AWS CloudWatch Dashboards
```bash
# Create CloudWatch dashboard for:
# - EC2 metrics (CPU, memory, disk)
# - ALB metrics (request count, latency)
# - Service health checks
```

### Step 2: Application Monitoring
```bash
# Set up alerts for:
# - Service downtime
# - High error rates  
# - Slow response times
# - High resource usage
```

## 🔒 Security Configuration

### Step 1: SSL Certificates
```bash
# Request SSL certificate in AWS Certificate Manager
aws acm request-certificate \
  --domain-name api.yourdomain.com \
  --validation-method DNS

# Add to ALB HTTPS listener
```

### Step 2: Security Groups Review
```bash
# Verify security groups are restrictive:
# - Only necessary ports open
# - Internal communication only between services
# - SSH access from your IP only
```

## 🚨 Troubleshooting Guide

### Common Issues

#### Backend Services Won't Start
```bash
# Check logs
docker logs container-name

# Check environment variables
docker exec container-name env | grep -E "(SUPABASE|MODEL|AGENT)"

# Check network connectivity
docker exec container-name ping other-service-ip
```

#### Frontend Can't Connect to Backend
```bash
# Check environment variables in Vercel
# Verify ALB DNS name is correct
# Test API endpoints directly:
curl https://api.yourdomain.com/api/users/health
```

#### Database Connection Issues
```bash
# Test Supabase connection
psql "postgresql://postgres:password@db.bsvstczwobwxozzmykhx.supabase.co:5432/postgres"

# Check environment variables
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_ROLE_KEY
```

## 📋 Post-Deployment Checklist

### Functionality Tests
- [ ] User registration/login works
- [ ] AI agent responds to requests
- [ ] Model inference is working
- [ ] Events are being logged
- [ ] Payment flow works (if enabled)

### Performance Tests
- [ ] Response times < 2 seconds
- [ ] No memory leaks in services
- [ ] Database queries optimized
- [ ] Frontend loads quickly

### Security Tests
- [ ] All endpoints require authentication
- [ ] HTTPS is enforced
- [ ] API keys are not exposed
- [ ] Rate limiting is working

## 🔄 Maintenance Tasks

### Daily
- [ ] Check service health in CloudWatch
- [ ] Review error logs
- [ ] Monitor costs in AWS billing

### Weekly  
- [ ] Update dependencies
- [ ] Review security alerts
- [ ] Backup verification

### Monthly
- [ ] Security patching
- [ ] Performance optimization
- [ ] Cost optimization review

## 📞 Emergency Contacts & Procedures

### Service Outage
1. Check AWS service health
2. Verify ALB target health
3. Restart services if needed
4. Scale up if resource constrained

### Security Incident
1. Rotate API keys immediately
2. Check access logs
3. Update security groups
4. Report to security team

### Data Issues
1. Check Supabase status
2. Verify backup integrity
3. Contact database admin
4. Prepare rollback plan

---

This guide provides step-by-step instructions for the complete deployment of your isA system across all components. Each team member can follow their specific sections while coordinating with others for dependencies.