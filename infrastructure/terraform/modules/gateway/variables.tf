variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "agent_name" {
  description = "Agent name"
  type        = string
}

variable "role_arn" {
  description = "IAM Role ARN for the AgentCore Gateway"
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

variable "banqi_api_base_url" {
  description = "Base URL of the banQi consignado API"
  type        = string
}
