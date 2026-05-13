variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "agent_name" {
  description = "Name of the agent"
  type        = string
}

variable "role_arn" {
  description = "IAM Role ARN for the AgentCore Runtime"
  type        = string
}

variable "ecr_repo_name" {
  description = "ECR repository name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "project_root" {
  description = "Absolute path to the project root (for Docker build context)"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "network_mode" {
  description = "Network mode: VPC or PUBLIC"
  type        = string
  default     = "VPC"

  validation {
    condition     = contains(["VPC", "PUBLIC"], var.network_mode)
    error_message = "network_mode must be VPC or PUBLIC"
  }
}

variable "subnet_ids" {
  description = "List of private subnet IDs (required when network_mode = VPC)"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "List of security group IDs for the runtime (required when network_mode = VPC)"
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Environment variables to inject into the AgentCore Runtime container"
  type        = map(string)
  default     = {}
}
