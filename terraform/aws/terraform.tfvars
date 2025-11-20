# ==========================================================================
# Tria AI-BPO AWS ECS Deployment Configuration
# ==========================================================================
#
# IMPORTANT: This file contains sensitive values. DO NOT commit to git!
# Add terraform.tfvars to .gitignore
# ==========================================================================

# General Configuration
aws_region   = "ap-southeast-1"  # Singapore (change if needed)
environment  = "production"
project_name = "tria-aibpo"

# Database Configuration
db_username = "tria_admin"
db_password = "CHANGE_THIS_TO_SECURE_PASSWORD_MIN_12_CHARS"  # MUST CHANGE!

# Redis Configuration (optional auth token)
redis_auth_token = ""  # Leave empty for no auth, or set secure token

# Application Secrets
openai_api_key = "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"
secret_key     = "CHANGE_THIS_TO_RANDOM_32_CHAR_STRING_FOR_JWT"  # MUST CHANGE!

# ECS Configuration (FREE TIER OPTIMIZED)
# This configuration stays within AWS Free Tier limits:
# - 0.5 vCPU / 1GB RAM = ~750 hours/month free for 12 months
ecs_task_cpu    = "512"   # 0.5 vCPU (free tier)
ecs_task_memory = "1024"  # 1GB RAM (free tier)

ecs_service_desired_count = 1  # Start with 1 task (can scale up)
ecs_autoscaling_min       = 1
ecs_autoscaling_max       = 5  # Can scale to 5 under load

# Database Configuration (FREE TIER OPTIMIZED)
# db.t4g.micro = 750 hours/month free for 12 months
rds_instance_class = "db.t4g.micro"

# Redis Configuration (FREE TIER OPTIMIZED)
# cache.t4g.micro = 750 hours/month free for 12 months
redis_node_type = "cache.t4g.micro"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"

# Additional Tags
additional_tags = {
  Owner       = "tria"
  CostCenter  = "aibpo"
  Terraform   = "true"
}
