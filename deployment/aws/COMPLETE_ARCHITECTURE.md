# isA Complete Full-Stack Architecture

## 🏗️ Complete System Architecture

```
                              ┌─────────────────┐
                              │   Users/Clients │
                              └─────────┬───────┘
                                        │
                        ┌───────────────┼───────────────┐
                        │               │               │
                ┌───────▼───────┐ ┌─────▼─────┐ ┌─────▼─────┐
                │   Website     │ │ AI Apps   │ │  Mobile   │
                │  (Vercel)     │ │ (Vercel)  │ │ (Future)  │
                └───────┬───────┘ └─────┬─────┘ └─────┬─────┘
                        │               │             │
                        └───────────────┼─────────────┘
                                        │
                                ┌───────▼───────┐
                                │  AWS ALB      │
                                │ (Load Bal.)   │
                                └───────┬───────┘
                                        │
                        ┌───────────────┼───────────────┐
                        │               │               │
                ┌───────▼───┐    ┌──────▼──────┐ ┌─────▼─────┐
                │   EC2-1   │    │    EC2-2    │ │   EC2-3   │
                │MCP Services│    │Model Service│ │Agent Serv.│
                │           │    │             │ │           │
                │8081,8100  │    │    8082     │ │   8080    │
                │  8101     │    │             │ │           │
                └───────────┘    └─────────────┘ └───────────┘
                        │               │               │
                        └───────────────┼───────────────┘
                                        │
                        ┌───────────────┼───────────────┐
                        │               │               │
                ┌───────▼───────┐ ┌─────▼─────┐ ┌─────▼─────┐
                │  Supabase     │ │  Neo4j    │ │    AWS    │
                │   Cloud       │ │   Aura    │ │    S3     │
                │ (Database)    │ │ (Graph)   │ │ (Storage) │
                └───────────────┘ └───────────┘ └───────────┘
                        │
                ┌───────┼───────┐
                │       │       │
        ┌───────▼───┐ ┌─▼─┐ ┌───▼───┐
        │   Auth0   │ │...│ │Stripe │
        │ (Login)   │ │   │ │ (Pay) │
        └───────────┘ └───┘ └───────┘
```

## 📋 Service Details & Communication

### Frontend Layer (Vercel)

#### 1. Website Frontend
- **Platform**: Vercel
- **Tech**: Next.js/React
- **Purpose**: Marketing, documentation, public pages
- **APIs Used**: User Service (8100) for basic auth

#### 2. AI Apps Frontend  
- **Platform**: Vercel
- **Tech**: Next.js/React with AI components
- **Purpose**: Interactive AI applications
- **APIs Used**: ALL 5 services
  - Agent Service (8080) - AI agent interactions
  - MCP Service (8081) - Core functionality
  - User Service (8100) - Authentication & user data
  - Event Service (8101) - Analytics & logging
  - Model Service (8082) - AI model inference

### Backend Layer (AWS EC2)

#### EC2-1: Core MCP Services
```
Services:
├── MCP Server (8081)     - Core MCP functionality
├── User Service (8100)   - Auth0 integration, Stripe billing
└── Event Service (8101)  - Analytics, monitoring
```

#### EC2-2: AI Model Services
```
Services:
└── Model Service (8082)  - AI inference, embeddings
```

#### EC2-3: Agent Services
```
Services:
└── Agent Service (8080)  - Autonomous agents, orchestration
```

### Data Layer (Cloud Services)

#### Primary Database
- **Supabase Cloud**: PostgreSQL with extensions
- **Schema**: 43 tables (user data, memories, sessions, etc.)
- **Access**: All backend services via service role key

#### Graph Database
- **Neo4j Aura Cloud**: Knowledge graphs, relationships
- **Access**: MCP & Agent services for complex queries

#### Storage
- **AWS S3**: File storage, assets (future use)
- **Access**: Direct from applications via signed URLs

### Authentication & Payment

#### Auth0
- **Purpose**: User authentication, social login
- **Integration**: User Service (8100) handles all auth flows
- **Frontend**: Direct Auth0 SDK integration

#### Stripe
- **Purpose**: Payment processing, subscriptions
- **Integration**: User Service (8100) webhooks and API
- **Frontend**: Stripe Elements for payment forms

## 🔗 Service Communication Matrix

### Frontend → Backend Communication
```
AI Apps (Vercel) 
├── → ALB/Agent (8080)    [Primary AI interactions]
├── → ALB/MCP (8081)      [Core functions]
├── → ALB/User (8100)     [Auth, profile, billing]
├── → ALB/Event (8101)    [Analytics, logging]
└── → ALB/Model (8082)    [Direct model calls]

Website (Vercel)
├── → ALB/User (8100)     [Authentication only]
└── → ALB/Event (8101)    [Basic analytics]
```

### Backend → Backend Communication
```
Agent Service (8080)
├── → MCP Service (8081)      [Tool execution]
├── → User Service (8100)     [User context]
├── → Event Service (8101)    [Action logging]
└── → Model Service (8082)    [AI inference]

MCP Service (8081)
├── → User Service (8100)     [User permissions]
├── → Event Service (8101)    [Tool usage logs]
└── → Model Service (8082)    [AI-powered tools]

User Service (8100)
└── → Event Service (8101)    [User action logs]

Model Service (8082)
└── → Event Service (8101)    [Performance metrics]
```

## 🌐 Network & Security Configuration

### Load Balancer Routing (ALB)
```yaml
Domain: api.yourdomain.com
Routes:
  - /api/agent/*   → EC2-3:8080 (Agent Service)
  - /api/mcp/*     → EC2-1:8081 (MCP Service)  
  - /api/users/*   → EC2-1:8100 (User Service)
  - /api/auth/*    → EC2-1:8100 (User Service)
  - /api/billing/* → EC2-1:8100 (User Service)
  - /api/events/*  → EC2-1:8101 (Event Service)
  - /api/models/*  → EC2-2:8082 (Model Service)
  - /*             → EC2-1:8081 (Default to MCP)
```

### Security Groups
```yaml
Internet → ALB:
  - 80, 443 (HTTPS only)

ALB → EC2 Services:
  - 8080 (Agent)
  - 8081 (MCP) 
  - 8100 (User)
  - 8101 (Event)
  - 8082 (Model)

EC2 Internal Communication:
  - All services can talk to each other
  - Private subnet communication only
```

## 📱 Environment Configuration

### Vercel Environment Variables (AI Apps)
```bash
# API Endpoints
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
NEXT_PUBLIC_AGENT_API_URL=https://api.yourdomain.com/api/agent
NEXT_PUBLIC_MCP_API_URL=https://api.yourdomain.com/api/mcp
NEXT_PUBLIC_USER_API_URL=https://api.yourdomain.com/api/users

# Auth0
NEXT_PUBLIC_AUTH0_DOMAIN=your-domain.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret

# Stripe
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...

# Analytics
NEXT_PUBLIC_ANALYTICS_URL=https://api.yourdomain.com/api/events
```

### AWS EC2 Environment Variables
```bash
# Service Discovery
AGENT_SERVICE_URL=http://10.0.12.100:8080
MCP_SERVICE_URL=http://10.0.10.100:8081
USER_SERVICE_URL=http://10.0.10.100:8100
EVENT_SERVICE_URL=http://10.0.10.100:8101
MODEL_SERVICE_URL=http://10.0.11.100:8082

# Database
SUPABASE_URL=https://bsvstczwobwxozzmykhx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
NEO4J_URI=neo4j+s://your-neo4j.databases.neo4j.io

# External Services
AUTH0_DOMAIN=your-domain.auth0.com
STRIPE_SECRET_KEY=sk_live_...
AWS_S3_BUCKET=your-s3-bucket
```

## 🚀 Deployment Strategy

### Phase 1: Infrastructure (AWS)
```bash
# 1. Create VPC and networking
terraform apply -target=aws_vpc
terraform apply -target=aws_subnet

# 2. Create security groups
terraform apply -target=aws_security_group

# 3. Create ALB
terraform apply -target=aws_lb

# 4. Create EC2 instances
terraform apply -target=aws_instance
```

### Phase 2: Backend Services
```bash
# Deploy in order:
# 1. EC2-1: User Service (8100) - Foundation
# 2. EC2-1: Event Service (8101) - Logging
# 3. EC2-1: MCP Service (8081) - Core
# 4. EC2-2: Model Service (8082) - AI
# 5. EC2-3: Agent Service (8080) - Orchestration
```

### Phase 3: Frontend Deployment
```bash
# 1. Deploy Website to Vercel
vercel deploy --prod

# 2. Deploy AI Apps to Vercel  
vercel deploy --prod

# 3. Configure custom domains
# 4. Update DNS settings
```

## 📊 Cost Breakdown

### AWS Infrastructure
```
EC2 Instances:
├── t3.small × 2 (MCP + Agent): $30/month
└── t3.medium × 1 (Model): $30/month

Networking:
├── ALB: $25/month
├── Data Transfer: $10/month
└── NAT Gateway: $45/month

Storage:
├── EBS (60GB total): $6/month
└── S3 (minimal): $2/month

Total AWS: ~$148/month
```

### External Services
```
Supabase: Free tier (sufficient for staging)
Neo4j Aura: $65/month (smallest instance)
Auth0: Free tier (up to 7,000 users)
Stripe: 2.9% + 30¢ per transaction
Vercel: Free tier (sufficient for staging)

Total External: ~$65/month
```

**Total Monthly Cost: ~$213/month**

## 🔄 Development Workflow

### 1. Local Development
```bash
# Frontend: Vercel dev server
npm run dev

# Backend: Local services
docker-compose up -d  # Local Supabase
python smart_mcp_server.py --port 8081
python user_service.py --port 8100
# etc.
```

### 2. Staging Deployment
```bash
# Backend: Deploy to AWS staging
./deploy.sh staging

# Frontend: Deploy to Vercel preview
vercel deploy
```

### 3. Production Deployment
```bash
# Backend: Deploy to AWS production
./deploy.sh production

# Frontend: Deploy to Vercel production
vercel deploy --prod
```

## 🔍 Monitoring & Observability

### Application Monitoring
```
- Vercel Analytics (Frontend performance)
- AWS CloudWatch (Backend metrics)
- Supabase Dashboard (Database performance)
- Auth0 Dashboard (Authentication metrics)
- Stripe Dashboard (Payment analytics)
```

### Logging Strategy
```
Frontend Logs → Vercel Console
Backend Logs → CloudWatch
Database Logs → Supabase Logs
Auth Logs → Auth0 Logs
Payment Logs → Stripe Dashboard
```

### Health Checks
```
- ALB Target Group Health
- Service-to-service ping endpoints
- Database connectivity
- External service availability
```

## 🚨 Disaster Recovery

### Backup Strategy
```
- Supabase: Daily automated backups
- Neo4j: Weekly manual exports  
- Code: Git repositories
- Configuration: Infrastructure as Code
- Secrets: AWS Secrets Manager backup
```

### Recovery Procedures
```
1. Infrastructure: Terraform re-deployment
2. Database: Supabase point-in-time recovery
3. Frontend: Vercel re-deployment from Git
4. Secrets: Restore from AWS Secrets Manager
5. DNS: Update Route53 records if needed
```

This architecture provides:
✅ **Scalability**: Each service can scale independently
✅ **Reliability**: Multiple layers of redundancy
✅ **Security**: Proper network isolation and authentication
✅ **Cost-Effective**: Optimized resource allocation
✅ **Maintainable**: Clear separation of concerns
✅ **Observable**: Comprehensive monitoring and logging