variable "name_prefix" {
  type = string
}

variable "agent_name" {
  type = string
}

variable "role_arn" {
  type = string
}

variable "aws_account_id" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "gateway_auth_type" {
  description = "Gateway auth: COGNITO (creates User Pool), AWS_IAM (simple), or CUSTOM_JWT (bring your own OIDC)"
  type        = string
  default     = "AWS_IAM"
  validation {
    condition     = contains(["COGNITO", "AWS_IAM", "CUSTOM_JWT"], var.gateway_auth_type)
    error_message = "Must be COGNITO, AWS_IAM, or CUSTOM_JWT."
  }
}

variable "gateway_jwt_discovery_url" {
  description = "OIDC discovery URL (required when gateway_auth_type = CUSTOM_JWT)"
  type        = string
  default     = ""
}

variable "gateway_tools" {
  description = "List of Lambda tools to register as gateway targets"
  type = list(object({
    name        = string
    tool_name   = string
    description = string
    lambda_arn  = string
  }))
  default = []
}
