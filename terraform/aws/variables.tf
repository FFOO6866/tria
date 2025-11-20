# ==========================================================================
# Tria AI-BPO AWS Infrastructure Variables
# ==========================================================================

# ==========================================================================
# General
# ==========================================================================

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "tria-aibpo"
}

# ==========================================================================
# Networking
# ==========================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# ==========================================================================
# RDS Configuration
# ==========================================================================

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"  # Free tier eligible, upgrade for production
}

variable "db_username" {
  description = "Database master username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.db_password) >= 12
    error_message = "Database password must be at least 12 characters long."
  }
}

# ==========================================================================
# ElastiCache Configuration
# ==========================================================================

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t4g.micro"  # Free tier eligible, upgrade for production
}

variable "redis_auth_token" {
  description = "Redis authentication token (optional, leave empty to disable)"
  type        = string
  sensitive   = true
  default     = ""
}

# ==========================================================================
# ECS Configuration
# ==========================================================================

variable "ecs_task_cpu" {
  description = "ECS task CPU units (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "512"
}

variable "ecs_task_memory" {
  description = "ECS task memory in MB (512, 1024, 2048, 4096, 8192)"
  type        = string
  default     = "1024"
}

variable "ecs_service_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "ecs_autoscaling_min" {
  description = "Minimum number of ECS tasks for autoscaling"
  type        = number
  default     = 1
}

variable "ecs_autoscaling_max" {
  description = "Maximum number of ECS tasks for autoscaling"
  type        = number
  default     = 10
}

# ==========================================================================
# Application Configuration
# ==========================================================================

variable "openai_api_key" {
  description = "OpenAI API key (stored in Secrets Manager)"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Application secret key (stored in Secrets Manager)"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.secret_key) >= 32
    error_message = "Secret key must be at least 32 characters long."
  }
}

# ==========================================================================
# Tags
# ==========================================================================

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
