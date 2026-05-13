variable "name_prefix" {
  type = string
}

variable "domain_slug" {
  description = "Domain slug for session ID generation"
  type        = string
}

variable "environment" {
  type = string
}

variable "agent_name" {
  description = "AgentCore agent name (for IAM scoping)"
  type        = string
}

variable "agentcore_runtime_arn" {
  description = "AgentCore Runtime ARN for Lambda invocation"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM role ARN for Lambda"
  type        = string
}

variable "lambda_source_dir" {
  description = "Path to WhatsApp Lambda source code"
  type        = string
}

variable "whatsapp_token" {
  description = "WhatsApp Business API access token"
  type        = string
  sensitive   = true
}

variable "whatsapp_app_secret" {
  description = "WhatsApp app secret for HMAC signature validation"
  type        = string
  sensitive   = true
}

variable "whatsapp_verify_token" {
  description = "WhatsApp webhook verification token"
  type        = string
  sensitive   = true
}

variable "whatsapp_phone_number_id" {
  description = "WhatsApp Business Phone Number ID"
  type        = string
}

variable "error_message_generic" {
  description = "Generic error message sent to users"
  type        = string
  default     = "Sorry, an error occurred. Please try again."
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for Lambda VPC config"
  type        = list(string)
  default     = []
}

variable "lambda_security_group_id" {
  description = "Security group ID for Lambda"
  type        = string
  default     = ""
}

variable "waf_acl_arn" {
  description = "WAF Web ACL ARN to associate with API Gateway (empty to skip)"
  type        = string
  default     = ""
}

variable "log_kms_key_arn" {
  description = "KMS key ARN for CloudWatch Log Group encryption (null to skip)"
  type        = string
  default     = null
}

variable "agentcore_memory_id" {
  description = "AgentCore Memory ID for conversation persistence (empty to skip)"
  type        = string
  default     = ""
}