# AWS Deployment Guide for Tria AI-BPO Chatbot

**Status**: Production Ready
**Last Updated**: 2025-11-13
**Estimated Time**: 45-60 minutes

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Cost Estimate](#cost-estimate)
4. [Quick Start](#quick-start)
5. [Step 1: AWS Account Setup](#step-1-aws-account-setup)
6. [Step 2: GitHub Secrets Configuration](#step-2-github-secrets-configuration)
7. [Step 3: Terraform Infrastructure Deployment](#step-3-terraform-infrastructure-deployment)
8. [Step 4: Initial Docker Image Push](#step-4-initial-docker-image-push)
9. [Step 5: CI/CD Activation](#step-5-cicd-activation)
10. [Verification](#verification)
11. [Monitoring and Maintenance](#monitoring-and-maintenance)
12. [Troubleshooting](#troubleshooting)
13. [Cost Optimization](#cost-optimization)
14. [Rollback Procedures](#rollback-procedures)

---

## Overview

This guide walks you through deploying the Tria AI-BPO chatbot to AWS using:

- **ECS/Fargate**: Serverless container orchestration
- **RDS PostgreSQL**: Managed database
- **ElastiCache Redis**: Managed cache
- **Application Load Balancer**: Traffic distribution
- **ECR**: Container registry
- **GitHub Actions**: Automated CI/CD

### Architecture Diagram

```
┌──────────────┐
│   GitHub     │
│   Actions    │──────┐
└──────────────┘      │
                      ▼
              ┌───────────────┐
              │   AWS ECR     │
              │ (Docker Image)│
              └───────┬───────┘
                      │
         ┌────────────┴────────────┐
         │                         │
    ┌────▼────┐              ┌────▼────┐
    │   ALB   │              │   ECS   │
    │ (Port   │─────────────▶│ Fargate │
    │   80)   │              │ Tasks   │
    └─────────┘              └────┬────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
               ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
               │   RDS   │   │  Redis  │   │CloudWatch│
               │Postgres │   │  Cache  │   │   Logs   │
               └─────────┘   └─────────┘   └──────────┘
```

---

## Prerequisites

### Required Tools

1. **AWS CLI** (v2.x)
   ```bash
   # Install (Windows)
   msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

   # Install (Linux/Mac)
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install

   # Verify
   aws --version
   ```

2. **Terraform** (v1.5.0+)
   ```bash
   # Install (Windows - using Chocolatey)
   choco install terraform

   # Install (Linux/Mac)
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/

   # Verify
   terraform --version
   ```

3. **Docker** (for local testing)
   ```bash
   docker --version
   ```

4. **GitHub Account** with repository access

### Required Credentials

- AWS account with admin access
- OpenAI API key (from https://platform.openai.com/)
- GitHub personal access token (for CI/CD)

---

## Cost Estimate

### Monthly Costs (US East 1)

| Service | Configuration | Monthly Cost |
|---------|--------------|-------------|
| **ECS Fargate** | 2 tasks × 0.5 vCPU, 1 GB RAM | ~$30 |
| **RDS PostgreSQL** | db.t4g.micro (free tier) | $0 (first year) |
| **ElastiCache Redis** | cache.t4g.micro (free tier) | $0 (first year) |
| **Application Load Balancer** | 1 ALB + data transfer | ~$20 |
| **Data Transfer** | 10 GB/month | ~$1 |
| **CloudWatch Logs** | 5 GB logs | ~$3 |
| **ECR Storage** | 1 GB images | ~$0.10 |
| **NAT Gateway** | 2 NAT gateways | ~$70 |
| **Total (Staging)** | | **~$124/month** |
| **Total (First Year with Free Tier)** | | **~$54/month** |

**Cost Optimization**: See [Cost Optimization](#cost-optimization) section for ways to reduce costs.

---

## Quick Start

**For experienced users**, execute these commands:

```bash
# 1. Configure AWS credentials
aws configure

# 2. Navigate to terraform directory
cd terraform/aws

# 3. Configure variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Edit with your values

# 4. Deploy infrastructure
terraform init
terraform plan
terraform apply

# 5. Push initial Docker image
$(terraform output -raw useful_commands | grep get_ecr_login | cut -d'"' -f4)
docker build -t tria-aibpo:latest .
docker tag tria-aibpo:latest $(terraform output -raw ecr_repository_url):latest
docker push $(terraform output -raw ecr_repository_url):latest

# 6. Configure GitHub secrets (see Step 2 for values)

# 7. Push to GitHub to trigger CI/CD
git push origin main
```

---

## Step 1: AWS Account Setup

### 1.1 Create AWS Account

If you don't have an AWS account:

1. Go to https://aws.amazon.com/
2. Click "Create an AWS Account"
3. Follow the registration process
4. Add a payment method (free tier available for 12 months)

### 1.2 Create IAM User for Terraform

**Why**: Better security than using root credentials.

```bash
# Create IAM user via AWS Console:
# 1. Go to IAM → Users → Add User
# 2. Username: terraform-user
# 3. Access type: Programmatic access
# 4. Attach policies: AdministratorAccess (for simplicity; restrict in production)
# 5. Save the Access Key ID and Secret Access Key

# Or via CLI:
aws iam create-user --user-name terraform-user
aws iam attach-user-policy --user-name terraform-user \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
aws iam create-access-key --user-name terraform-user
```

### 1.3 Configure AWS CLI

```bash
aws configure

# Enter when prompted:
# AWS Access Key ID: <your-access-key-id>
# AWS Secret Access Key: <your-secret-access-key>
# Default region: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDAXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/terraform-user"
}
```

---

## Step 2: GitHub Secrets Configuration

### 2.1 Required GitHub Secrets

Navigate to your GitHub repository:
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add the following secrets:

| Secret Name | Description | How to Get |
|------------|-------------|------------|
| `AWS_ACCESS_KEY_ID` | AWS access key for CI/CD | From Step 1.2 |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for CI/CD | From Step 1.2 |
| `OPENAI_API_KEY` | OpenAI API key for chatbot | https://platform.openai.com/api-keys |

### 2.2 Adding Secrets via GitHub UI

For each secret:

1. Click **New repository secret**
2. **Name**: Enter the secret name (e.g., `AWS_ACCESS_KEY_ID`)
3. **Value**: Paste the secret value
4. Click **Add secret**

### 2.3 Verify Secrets

After adding all secrets, you should see:

```
✓ AWS_ACCESS_KEY_ID
✓ AWS_SECRET_ACCESS_KEY
✓ OPENAI_API_KEY
```

---

## Step 3: Terraform Infrastructure Deployment

### 3.1 Navigate to Terraform Directory

```bash
cd terraform/aws
```

### 3.2 Configure Variables

```bash
# Copy example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required values** in `terraform.tfvars`:

```hcl
# General Configuration
aws_region   = "us-east-1"
environment  = "staging"  # or "production"
project_name = "tria-aibpo"

# Database Configuration
db_username = "tria_admin"
db_password = "GENERATE_SECURE_PASSWORD_HERE"  # Min 12 chars

# Application Secrets
openai_api_key = "sk-your-openai-api-key-here"
secret_key     = "GENERATE_32_CHAR_SECRET_KEY_HERE"
```

**Generate secure passwords**:

```bash
# Database password (20 characters)
openssl rand -base64 20

# Secret key (32 characters)
openssl rand -hex 32
```

### 3.3 Initialize Terraform

```bash
terraform init
```

Expected output:
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.x.x...

Terraform has been successfully initialized!
```

### 3.4 Review Deployment Plan

```bash
terraform plan
```

Review the resources to be created (approximately 40+ resources):
- VPC, subnets, route tables
- Security groups
- RDS PostgreSQL instance
- ElastiCache Redis cluster
- ECS cluster, task definition, service
- Application Load Balancer
- ECR repository
- IAM roles and policies
- CloudWatch log groups

### 3.5 Apply Infrastructure

```bash
terraform apply
```

Type `yes` when prompted.

**Deployment time**: 10-15 minutes

Expected final output:
```
Apply complete! Resources: 42 added, 0 changed, 0 destroyed.

Outputs:

alb_url = "http://tria-aibpo-staging-alb-123456789.us-east-1.elb.amazonaws.com"
ecr_repository_url = "123456789012.dkr.ecr.us-east-1.amazonaws.com/tria-aibpo-staging"
database_url = <sensitive>
deployment_summary = {
  app_url = "http://tria-aibpo-staging-alb-123456789.us-east-1.elb.amazonaws.com"
  docs_url = "http://tria-aibpo-staging-alb-123456789.us-east-1.elb.amazonaws.com/docs"
  environment = "staging"
  health_url = "http://tria-aibpo-staging-alb-123456789.us-east-1.elb.amazonaws.com/health"
  region = "us-east-1"
}
```

### 3.6 Save Outputs

```bash
# Save all outputs for reference
terraform output > terraform-outputs.txt

# Get specific sensitive outputs
terraform output -raw database_url
terraform output -raw redis_primary_endpoint
```

---

## Step 4: Initial Docker Image Push

The GitHub Actions CI/CD pipeline builds and pushes Docker images automatically, but for the **first deployment**, you need to push an initial image.

### 4.1 Authenticate with ECR

```bash
# Get ECR login command from Terraform output
ECR_URL=$(terraform output -raw ecr_repository_url)
AWS_REGION=$(terraform output -json deployment_summary | jq -r '.region')

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_URL
```

### 4.2 Build and Tag Docker Image

```bash
# Navigate to project root
cd ../..

# Build Docker image
docker build -t tria-aibpo:latest -f Dockerfile .

# Tag for ECR
docker tag tria-aibpo:latest $ECR_URL:latest
docker tag tria-aibpo:latest $ECR_URL:staging-initial
```

### 4.3 Push Image to ECR

```bash
# Push both tags
docker push $ECR_URL:latest
docker push $ECR_URL:staging-initial
```

Expected output:
```
The push refers to repository [123456789012.dkr.ecr.us-east-1.amazonaws.com/tria-aibpo-staging]
staging-initial: digest: sha256:abc123... size: 2841
latest: digest: sha256:abc123... size: 2841
```

### 4.4 Update ECS Service (Force New Deployment)

```bash
aws ecs update-service \
  --cluster tria-aibpo-staging-cluster \
  --service tria-aibpo-staging-service \
  --force-new-deployment \
  --region us-east-1
```

Wait 2-3 minutes for the service to stabilize.

---

## Step 5: CI/CD Activation

### 5.1 Verify GitHub Actions Workflow

Check that the workflow file exists:

```bash
ls -la .github/workflows/aws-cicd.yml
```

### 5.2 Update Workflow Configuration (if needed)

Edit `.github/workflows/aws-cicd.yml` and verify:

```yaml
env:
  AWS_REGION: us-east-1  # Match your terraform region
  ECR_REPOSITORY: tria-aibpo-staging  # Match terraform output
  ECS_SERVICE: tria-aibpo-service-staging
  ECS_CLUSTER: tria-aibpo-cluster-staging
  ECS_TASK_DEFINITION: tria-aibpo-task-staging
  CONTAINER_NAME: tria-aibpo-backend
```

### 5.3 Trigger CI/CD Pipeline

**Option A: Push to main branch**

```bash
git add .
git commit -m "ci: Activate AWS CI/CD pipeline"
git push origin main
```

**Option B: Manual workflow dispatch**

1. Go to GitHub repository
2. Click **Actions** tab
3. Select **AWS CI/CD** workflow
4. Click **Run workflow**
5. Select branch (main or develop)
6. Click **Run workflow**

### 5.4 Monitor Pipeline Execution

1. Go to **Actions** tab in GitHub
2. Click on the running workflow
3. Monitor each job:
   - ✓ Code Quality Checks (~2 min)
   - ✓ Unit Tests (~3 min)
   - ✓ Integration Tests (~5 min)
   - ✓ Docker Build & Push (~4 min)
   - ✓ Deploy to Staging (~5 min)
   - ✓ E2E Tests on Staging (~3 min)

**Total pipeline time**: ~20-25 minutes

---

## Verification

### 6.1 Check Application Health

```bash
# Get ALB URL from Terraform
ALB_URL=$(terraform output -raw alb_url)

# Health check
curl $ALB_URL/health

# Expected response:
# {"status": "healthy", "version": "1.1.0"}
```

### 6.2 Test API Documentation

Open in browser:
```
http://<your-alb-url>/docs
```

### 6.3 Test Chatbot API

```bash
# Send test message
curl -X POST "$ALB_URL/api/chatbot" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is your refund policy?",
    "session_id": "test-session-001"
  }'
```

Expected response:
```json
{
  "message": "Our refund policy allows returns within 30 days...",
  "session_id": "test-session-001",
  "metadata": {
    "from_cache": false,
    "processing_time": "2.3s"
  }
}
```

### 6.4 Check ECS Service Status

```bash
aws ecs describe-services \
  --cluster tria-aibpo-staging-cluster \
  --services tria-aibpo-staging-service \
  --region us-east-1 \
  --query 'services[0].[serviceName,status,runningCount,desiredCount]'
```

Expected: `["tria-aibpo-staging-service", "ACTIVE", 2, 2]`

### 6.5 View Application Logs

```bash
# Tail logs
aws logs tail /ecs/tria-aibpo-staging --follow --region us-east-1

# View recent logs
aws logs tail /ecs/tria-aibpo-staging --since 10m --region us-east-1
```

---

## Monitoring and Maintenance

### 7.1 CloudWatch Dashboard

Access metrics via AWS Console:

1. Navigate to **CloudWatch** → **Dashboards**
2. View metrics:
   - ECS CPU/Memory utilization
   - ALB request count and latency
   - RDS database connections
   - Redis cache hit rate

### 7.2 Key Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|--------|
| ECS CPU Utilization | >70% | Scale up tasks |
| ECS Memory Utilization | >80% | Scale up tasks or increase memory |
| ALB 5XX errors | >1% | Check application logs |
| RDS CPU Utilization | >80% | Upgrade instance class |
| Redis Evictions | >100/min | Increase cache size |

### 7.3 Set Up CloudWatch Alarms

```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name tria-aibpo-high-cpu \
  --alarm-description "ECS CPU > 70%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 70 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ClusterName,Value=tria-aibpo-staging-cluster \
  --region us-east-1
```

### 7.4 Regular Maintenance Tasks

**Weekly**:
- Review CloudWatch logs for errors
- Check RDS storage utilization
- Review AWS cost explorer

**Monthly**:
- Update dependencies (security patches)
- Review and optimize cache hit rates
- Check for unused resources

---

## Troubleshooting

### 8.1 Deployment Failures

**Issue**: Terraform apply fails with "InvalidParameterException"

**Solution**:
```bash
# Check AWS service quotas
aws service-quotas list-service-quotas --service-code ecs

# Request quota increase if needed
aws service-quotas request-service-quota-increase \
  --service-code ecs \
  --quota-code L-XXXXX \
  --desired-value 20
```

### 8.2 ECS Tasks Not Starting

**Issue**: ECS tasks stuck in "PENDING" state

**Diagnosis**:
```bash
aws ecs describe-tasks \
  --cluster tria-aibpo-staging-cluster \
  --tasks $(aws ecs list-tasks --cluster tria-aibpo-staging-cluster --query 'taskArns[0]' --output text) \
  --region us-east-1
```

**Common causes**:
1. **No Docker image**: Push initial image (see Step 4)
2. **Insufficient resources**: Reduce task CPU/memory or scale cluster
3. **Secrets not found**: Create secrets in AWS Secrets Manager

### 8.3 Health Check Failures

**Issue**: ALB health checks failing, tasks being replaced

**Diagnosis**:
```bash
# Check target health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups --names tria-aibpo-staging-tg --query 'TargetGroups[0].TargetGroupArn' --output text) \
  --region us-east-1
```

**Solution**:
1. Check application logs for startup errors
2. Verify `/health` endpoint is accessible
3. Increase health check timeout in Terraform

### 8.4 Database Connection Issues

**Issue**: Application can't connect to RDS

**Diagnosis**:
```bash
# Check security group rules
aws ec2 describe-security-groups \
  --group-ids $(terraform output -raw rds_security_group_id) \
  --region us-east-1

# Test connection from ECS task
aws ecs execute-command \
  --cluster tria-aibpo-staging-cluster \
  --task <task-id> \
  --container tria-aibpo-backend \
  --interactive \
  --command "/bin/bash"
```

**Solution**:
- Verify security group allows port 5432 from ECS tasks SG
- Check database credentials in Terraform outputs
- Verify DATABASE_URL environment variable in task definition

### 8.5 CI/CD Pipeline Failures

**Issue**: GitHub Actions workflow failing

**Common issues**:

1. **AWS credentials invalid**
   - Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` secrets
   - Check IAM user permissions

2. **Docker build fails**
   - Check Dockerfile syntax
   - Verify all dependencies in requirements.txt

3. **Tests fail**
   - Check test environment variables
   - Review test logs in GitHub Actions

---

## Cost Optimization

### 9.1 Reduce NAT Gateway Costs (~$70/month savings)

**Option A**: Use single NAT gateway (less redundancy)

```hcl
# In terraform/aws/main.tf
resource "aws_nat_gateway" "main" {
  count = 1  # Change from 2 to 1
  ...
}
```

**Option B**: Remove NAT gateways for staging (no outbound internet)
- Remove NAT gateways entirely
- Use VPC endpoints for AWS services

### 9.2 Use Fargate Spot (up to 70% savings)

```hcl
# In terraform/aws/main.tf
resource "aws_ecs_cluster_capacity_providers" "main" {
  ...
  default_capacity_provider_strategy {
    base              = 0
    weight            = 100
    capacity_provider = "FARGATE_SPOT"  # Changed from FARGATE
  }
}
```

### 9.3 Right-Size Resources

**Current**: 2 tasks × 0.5 vCPU, 1 GB RAM
**Optimized for low traffic**: 1 task × 0.25 vCPU, 512 MB RAM

```hcl
# In terraform.tfvars
ecs_task_cpu            = "256"   # 0.25 vCPU
ecs_task_memory         = "512"   # 512 MB
ecs_service_desired_count = 1
```

### 9.4 Enable Auto-Scaling Based on Schedule

```hcl
# Scale down at night (9 PM - 6 AM)
resource "aws_appautoscaling_scheduled_action" "scale_down" {
  name               = "scale-down-at-night"
  service_namespace  = "ecs"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = "ecs:service:DesiredCount"

  schedule = "cron(0 21 * * ? *)"

  scalable_target_action {
    min_capacity = 1
    max_capacity = 1
  }
}
```

### 9.5 Estimated Savings

| Optimization | Monthly Savings | New Total |
|-------------|----------------|-----------|
| Baseline | - | $124 |
| Single NAT gateway | -$35 | $89 |
| Fargate Spot | -$20 | $69 |
| Right-size resources | -$15 | $54 |
| **Total Optimizations** | **-$70** | **$54/month** |

---

## Rollback Procedures

### 10.1 Rollback GitHub Actions Deployment

**Automatic rollback** is configured in `.github/workflows/aws-cicd.yml` for production failures.

**Manual rollback**:

```bash
# List recent task definitions
aws ecs list-task-definitions \
  --family-prefix tria-aibpo-staging-task \
  --sort DESC \
  --max-items 5 \
  --region us-east-1

# Rollback to previous version
aws ecs update-service \
  --cluster tria-aibpo-staging-cluster \
  --service tria-aibpo-staging-service \
  --task-definition tria-aibpo-staging-task:N \
  --force-new-deployment \
  --region us-east-1
```

Replace `N` with the previous revision number.

### 10.2 Rollback Terraform Changes

```bash
# Rollback to previous state
cd terraform/aws

# List backups
ls -la terraform.tfstate.backup

# Restore backup
cp terraform.tfstate.backup terraform.tfstate

# Apply previous state
terraform apply
```

### 10.3 Emergency Procedures

**Complete service shutdown**:
```bash
aws ecs update-service \
  --cluster tria-aibpo-staging-cluster \
  --service tria-aibpo-staging-service \
  --desired-count 0 \
  --region us-east-1
```

**Restore service**:
```bash
aws ecs update-service \
  --cluster tria-aibpo-staging-cluster \
  --service tria-aibpo-staging-service \
  --desired-count 2 \
  --region us-east-1
```

---

## Next Steps

After successful deployment:

1. **Set up custom domain** (optional)
   - Register domain in Route 53
   - Create SSL certificate in ACM
   - Update ALB listener for HTTPS

2. **Configure monitoring alerts**
   - Set up SNS topics for alerts
   - Configure CloudWatch alarms
   - Integrate with Slack/PagerDuty

3. **Deploy to production**
   - Create production terraform workspace
   - Deploy with `environment = "production"`
   - Configure GitHub environments for approval gates

4. **Performance testing**
   - Run load tests: `python scripts/load_test_chat_api.py`
   - Monitor cache hit rates
   - Optimize based on metrics

---

## Support and Resources

### Documentation
- [Project README](../../README.md)
- [Cache Integration Guide](../guides/cache-integration-guide.md)
- [Project Status](../../PROJECT_STATUS.md)

### AWS Documentation
- [ECS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [ElastiCache Redis](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/WhatIs.html)

### Community
- GitHub Issues: [Report issues](https://github.com/your-org/tria-aibpo/issues)
- Project Repository: [tria-aibpo](https://github.com/your-org/tria-aibpo)

---

**Last Updated**: 2025-11-13
**Maintainer**: Development Team
**Version**: 1.0
