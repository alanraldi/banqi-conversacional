variable "name_prefix" {
  type = string
}

variable "agent_name" {
  type = string
}

variable "role_arn" {
  type = string
}

variable "ecr_repo_name" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "project_root" {
  description = "Absolute path to project root (for docker build context)"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag (defaults to timestamp)"
  type        = string
  default     = "latest"
}

variable "network_mode" {
  description = "Network mode for AgentCore Runtime: VPC or PUBLIC"
  type        = string
  default     = "VPC"
}

variable "subnet_ids" {
  description = "Subnet IDs for VPC mode"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security Group IDs for VPC mode"
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Environment variables for the AgentCore Runtime container"
  type        = map(string)
  default     = {}
}