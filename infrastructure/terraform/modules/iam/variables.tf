variable "name_prefix" {
  description = "Prefix for all resource names (e.g. banqi-consignado-staging)"
  type        = string
}

variable "domain_slug" {
  description = "Domain slug identifier"
  type        = string
}

variable "agent_name" {
  description = "Name of the AgentCore agent"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "ecr_repo_name" {
  description = "ECR repository name for the runtime container"
  type        = string
}
