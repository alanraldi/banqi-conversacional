# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region where resources will be provisioned"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "staging"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod"
  }
}

variable "aws_account_id" {
  description = "AWS account ID — used in IAM ARNs and ECR paths"
  type        = string
}

variable "domain_slug" {
  description = "Short identifier for the domain, used in resource names"
  type        = string
  default     = "banqi-consignado"
}

variable "agent_name" {
  description = "Name of the AgentCore Runtime agent"
  type        = string
  default     = "banqi_consignado_agent"
}

# -----------------------------------------------------------------------------
# Networking
# -----------------------------------------------------------------------------

variable "vpc_mode" {
  description = "VPC provisioning mode: 'create' creates a new VPC, 'existing' reuses one by name, 'none' disables VPC"
  type        = string
  default     = "create"

  validation {
    condition     = contains(["create", "existing", "none"], var.vpc_mode)
    error_message = "vpc_mode must be one of: create, existing, none"
  }
}

variable "vpc_name" {
  description = "Name tag of an existing VPC (required when vpc_mode = 'existing')"
  type        = string
  default     = ""
}

variable "vpc_cidr" {
  description = "CIDR block for the new VPC (only used when vpc_mode = 'create')"
  type        = string
  default     = "10.0.0.0/16"
}

# -----------------------------------------------------------------------------
# Container / Runtime
# -----------------------------------------------------------------------------

variable "image_tag" {
  description = "Docker image tag to deploy to AgentCore Runtime"
  type        = string
  default     = "latest"
}

# -----------------------------------------------------------------------------
# AgentCore Memory
# -----------------------------------------------------------------------------

variable "agentcore_memory_name" {
  description = "Name of the AgentCore Memory store"
  type        = string
  default     = "BanqiConsignadoMemory"
}

# -----------------------------------------------------------------------------
# banQi API
# -----------------------------------------------------------------------------

variable "banqi_api_base_url" {
  description = "Base URL of the banQi consignado REST API (e.g. https://api.banqi.com.br/consignado/v1)"
  type        = string
}

# -----------------------------------------------------------------------------
# WhatsApp (sensitive)
# -----------------------------------------------------------------------------

variable "whatsapp_token" {
  description = "WhatsApp Cloud API access token"
  type        = string
  sensitive   = true
}

variable "whatsapp_app_secret" {
  description = "WhatsApp application secret used to verify webhook signatures"
  type        = string
  sensitive   = true
}

variable "whatsapp_verify_token" {
  description = "Verification token used during WhatsApp webhook registration"
  type        = string
  sensitive   = true
}

variable "whatsapp_phone_number_id" {
  description = "WhatsApp Cloud API phone number ID (numeric string)"
  type        = string
}
