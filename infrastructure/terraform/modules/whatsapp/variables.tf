variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "domain_slug" {
  description = "Domain slug"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "agent_name" {
  description = "AgentCore agent name"
  type        = string
}

variable "agentcore_runtime_arn" {
  description = "ARN do AgentCore Runtime para invocar"
  type        = string
}

variable "agentcore_memory_id" {
  description = "ID do AgentCore Memory"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM Role ARN para a Lambda"
  type        = string
}

variable "whatsapp_token" {
  description = "WhatsApp Cloud API access token"
  type        = string
  sensitive   = true
}

variable "whatsapp_app_secret" {
  description = "WhatsApp app secret para verificar assinaturas"
  type        = string
  sensitive   = true
}

variable "whatsapp_verify_token" {
  description = "Token de verificação do webhook"
  type        = string
  sensitive   = true
}

variable "whatsapp_phone_number_id" {
  description = "WhatsApp Phone Number ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs das subnets privadas para a Lambda"
  type        = list(string)
  default     = []
}

variable "lambda_security_group_id" {
  description = "Security Group ID para a Lambda"
  type        = string
  default     = ""
}

variable "waf_acl_arn" {
  description = "ARN do WAF WebACL para associar ao API Gateway"
  type        = string
  default     = ""
}

variable "error_message_generic" {
  description = "Mensagem de erro genérica exibida ao usuário em caso de falha"
  type        = string
  default     = "Desculpe, ocorreu um erro. Tente novamente em alguns instantes."
}

variable "log_kms_key_arn" {
  description = "ARN da KMS key para criptografar logs do CloudWatch (opcional)"
  type        = string
  default     = ""
}
