# ==========================================================================
# Tria AI-BPO AWS Infrastructure Outputs
# ==========================================================================

# ==========================================================================
# Networking Outputs
# ==========================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

# ==========================================================================
# Load Balancer Outputs
# ==========================================================================

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_url" {
  description = "Application URL"
  value       = "http://${aws_lb.main.dns_name}"
}

output "alb_zone_id" {
  description = "ALB Zone ID for Route53"
  value       = aws_lb.main.zone_id
}

# ==========================================================================
# ECR Outputs
# ==========================================================================

output "ecr_repository_url" {
  description = "ECR repository URL for Docker images"
  value       = aws_ecr_repository.app.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN"
  value       = aws_ecr_repository.app.arn
}

# ==========================================================================
# ECS Outputs
# ==========================================================================

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.app.name
}

output "ecs_task_definition" {
  description = "ECS task definition ARN"
  value       = aws_ecs_task_definition.app.arn
}

# ==========================================================================
# Database Outputs
# ==========================================================================

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "rds_address" {
  description = "RDS PostgreSQL address"
  value       = aws_db_instance.postgres.address
  sensitive   = true
}

output "rds_port" {
  description = "RDS PostgreSQL port"
  value       = aws_db_instance.postgres.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.postgres.db_name
}

output "database_url" {
  description = "Full database connection URL"
  value       = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${aws_db_instance.postgres.db_name}"
  sensitive   = true
}

# ==========================================================================
# Redis Outputs
# ==========================================================================

output "redis_primary_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = 6379
}

# ==========================================================================
# IAM Outputs
# ==========================================================================

output "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.ecs_task.arn
}

# ==========================================================================
# CloudWatch Outputs
# ==========================================================================

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.app.name
}

# ==========================================================================
# Security Groups
# ==========================================================================

output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "ecs_tasks_security_group_id" {
  description = "ECS tasks security group ID"
  value       = aws_security_group.ecs_tasks.id
}

# ==========================================================================
# Deployment Information
# ==========================================================================

output "deployment_summary" {
  description = "Deployment summary"
  value = {
    environment = var.environment
    region      = var.aws_region
    app_url     = "http://${aws_lb.main.dns_name}"
    health_url  = "http://${aws_lb.main.dns_name}/health"
    docs_url    = "http://${aws_lb.main.dns_name}/docs"
  }
}

# ==========================================================================
# Quick Reference Commands
# ==========================================================================

output "useful_commands" {
  description = "Useful AWS CLI commands for this deployment"
  value = {
    push_docker_image = "docker push ${aws_ecr_repository.app.repository_url}:latest"
    get_ecr_login     = "aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.app.repository_url}"
    view_logs         = "aws logs tail /ecs/${var.project_name}-${var.environment} --follow --region ${var.aws_region}"
    update_service    = "aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.app.name} --force-new-deployment --region ${var.aws_region}"
    describe_service  = "aws ecs describe-services --cluster ${aws_ecs_cluster.main.name} --services ${aws_ecs_service.app.name} --region ${var.aws_region}"
  }
}
