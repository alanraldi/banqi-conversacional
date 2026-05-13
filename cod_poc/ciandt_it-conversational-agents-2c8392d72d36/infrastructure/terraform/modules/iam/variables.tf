variable "name_prefix" {
  type = string
}

variable "agent_name" {
  type = string
}

variable "aws_account_id" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "environment" {
  type = string
}

variable "ecr_repo_name" {
  type = string
}

variable "domain_slug" {
  description = "Domain identifier slug for tag-based conditions"
  type        = string
}

variable "gateway_tool_arns" {
  description = "Lambda ARNs for gateway tools (added to gateway role policy)"
  type        = list(string)
  default     = []
}