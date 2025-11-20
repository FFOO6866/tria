# AWS ECS Deployment Guide for Tria AI-BPO

**Elastic IP**: 13.214.14.130
**Region**: ap-southeast-1 (Singapore)
**Environment**: Production

## Prerequisites

1. AWS Account with admin access
2. AWS CLI installed and configured
3. Terraform installed (v1.5+)
4. Docker Desktop (for building images)

## Step 1: Install AWS CLI (Windows)

```powershell
# Download AWS CLI v2 for Windows
# Visit: https://awscli.amazonaws.com/AWSCLIV2.msi
# Or use PowerShell:
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Verify installation
aws --version
```

## Step 2: Configure AWS Credentials

```bash
# Configure AWS credentials
aws configure

# Enter when prompted:
# AWS Access Key ID: [YOUR_ACCESS_KEY]
# AWS Secret Access Key: [YOUR_SECRET_KEY]
# Default region name: ap-southeast-1
# Default output format: json

# Verify credentials
aws sts get-caller-identity
```

## Step 3: Update Terraform Variables

Edit `terraform/aws/terraform.tfvars`:

```hcl
# CRITICAL: Change these values!
db_password = "YOUR_SECURE_DB_PASSWORD_MIN_12_CHARS"
secret_key  = "YOUR_RANDOM_32_CHAR_JWT_SECRET_KEY"

# OpenAI API key is already set from .env.production
```

## Step 4: Initialize Terraform

```bash
cd terraform/aws

# Initialize Terraform (downloads AWS provider)
terraform init

# Validate configuration
terraform validate

# Preview what will be created
terraform plan
```

**Expected Resources** (~30 resources):
- VPC with public/private subnets
- NAT Gateways (2)
- Application Load Balancer
- ECS Fargate cluster
- RDS PostgreSQL (db.t4g.micro)
- ElastiCache Redis (cache.t4g.micro)
- ECR repository
- IAM roles and policies
- CloudWatch log groups
- Security groups
- Auto-scaling policies

## Step 5: Deploy Infrastructure

```bash
# Create all AWS resources (takes ~15 minutes)
terraform apply

# Type 'yes' when prompted

# Save outputs
terraform output > ../../deployment_outputs.txt
```

## Step 6: Build and Push Docker Image

```bash
cd ../..  # Back to project root

# Get ECR login command
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.ap-southeast-1.amazonaws.com

# Get ECR repository URL from terraform output
ECR_REPO=$(terraform -chdir=terraform/aws output -raw ecr_repository_url)

# Build Docker image
docker build -t tria-aibpo:latest -f Dockerfile .

# Tag for ECR
docker tag tria-aibpo:latest $ECR_REPO:latest

# Push to ECR
docker push $ECR_REPO:latest
```

## Step 7: Deploy ECS Service

```bash
# Force ECS service to use new image
aws ecs update-service \
  --cluster tria-aibpo-production-cluster \
  --service tria-aibpo-production-service \
  --force-new-deployment \
  --region ap-southeast-1

# Watch deployment status
aws ecs describe-services \
  --cluster tria-aibpo-production-cluster \
  --services tria-aibpo-production-service \
  --region ap-southeast-1 \
  --query 'services[0].deployments'
```

## Step 8: Run Database Migration

```bash
# Get ECS task ARN (will be running after deployment)
TASK_ARN=$(aws ecs list-tasks \
  --cluster tria-aibpo-production-cluster \
  --service-name tria-aibpo-production-service \
  --region ap-southeast-1 \
  --query 'taskArns[0]' \
  --output text)

# Run migration via ECS Exec
aws ecs execute-command \
  --cluster tria-aibpo-production-cluster \
  --task $TASK_ARN \
  --container tria-aibpo-backend \
  --command "python scripts/migrate_conversation_tables.py" \
  --interactive \
  --region ap-southeast-1
```

## Step 9: Configure DNS (Elastic IP)

**Option A: Point Elastic IP to ALB** (if ALB supports Elastic IP association)
```bash
# Get ALB DNS name
ALB_DNS=$(terraform -chdir=terraform/aws output -raw alb_dns_name)

# In AWS Console:
# 1. Go to EC2 > Load Balancers
# 2. Select your ALB
# 3. Actions > Associate Elastic IP (if available)
# 4. Select 13.214.14.130
```

**Option B: Use Route53 with Alias** (recommended)
```bash
# The ALB has a DNS name like: tria-aibpo-production-alb-123456789.ap-southeast-1.elb.amazonaws.com

# In AWS Console > Route53:
# 1. Create hosted zone for your domain
# 2. Create A record with Alias to ALB
# 3. The Elastic IP 13.214.14.130 can be used for direct EC2 access if needed
```

## Step 10: Test Deployment

```bash
# Get ALB URL
ALB_URL=$(terraform -chdir=terraform/aws output -raw alb_dns_name)

# Test health endpoint
curl http://$ALB_URL/health

# Test chat endpoint
curl -X POST http://$ALB_URL/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! I need pizza boxes",
    "user_id": "test_user",
    "session_id": "test_session"
  }'
```

## Cost Estimate (FREE TIER - First 12 Months)

| Resource | Configuration | Free Tier | Cost After Free Tier |
|----------|--------------|-----------|---------------------|
| ECS Fargate | 0.5 vCPU, 1GB RAM | 750 hrs/month | ~$15/month |
| RDS PostgreSQL | db.t4g.micro | 750 hrs/month | ~$15/month |
| ElastiCache Redis | cache.t4g.micro | 750 hrs/month | ~$12/month |
| ALB | Application Load Balancer | Not free | ~$20/month |
| NAT Gateway | 2x NAT Gateways | Not free | ~$70/month |
| Data Transfer | Outbound data | 100GB/month | $0.09/GB after |
| **Total** | | **~$90/month** | **~$132/month** |

**Cost Optimization**:
- NAT Gateway is the biggest cost ($35/month each)
- Consider single NAT Gateway for non-production: Save $35/month
- Use single AZ for staging: Additional savings

## Monitoring

```bash
# View logs
aws logs tail /ecs/tria-aibpo-production --follow --region ap-southeast-1

# View CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=tria-aibpo-production-service \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region ap-southeast-1
```

## Troubleshooting

### ECS Task Not Starting
```bash
# Check task status
aws ecs describe-tasks \
  --cluster tria-aibpo-production-cluster \
  --tasks $TASK_ARN \
  --region ap-southeast-1
```

### Database Connection Issues
```bash
# Check RDS endpoint
terraform -chdir=terraform/aws output -raw rds_endpoint

# Check security groups
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=tria-aibpo-production-rds-sg" \
  --region ap-southeast-1
```

### View Container Logs
```bash
aws logs tail /ecs/tria-aibpo-production --follow --region ap-southeast-1
```

## Cleanup (Destroy Infrastructure)

```bash
cd terraform/aws

# Destroy all resources
terraform destroy

# Type 'yes' when prompted
```

## Notes

- **Elastic IP 13.214.14.130**: Currently available for DNS configuration
- **Free Tier**: ECS, RDS, and Redis are free for first 12 months (750 hours/month each)
- **NAT Gateway**: Not free tier eligible (~$35/month each, 2 total = $70/month)
- **Production Ready**: Auto-scaling, multi-AZ, encrypted storage, CloudWatch monitoring
- **Migration**: Run after first deployment to create conversation tables

## Next Steps

1. Install AWS CLI: `msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi`
2. Configure credentials: `aws configure`
3. Update `terraform/aws/terraform.tfvars` with secure passwords
4. Deploy: `terraform apply`
5. Build and push Docker image
6. Run database migration
7. Test the deployment
