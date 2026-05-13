variable "domain_slug" {
  description = "Domain identifier slug (e.g. my-assistant)"
  type        = string
}

variable "agent_name" {
  description = "AgentCore agent name"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_mode" {
  description = "VPC mode: 'create' to create a new VPC, 'existing' to use an existing one by name, 'none' to skip networking (PUBLIC runtime)"
  type        = string
  default     = "create"
  validation {
    condition     = contains(["create", "existing", "none"], var.vpc_mode)
    error_message = "vpc_mode must be 'create', 'existing', or 'none'."
  }
}

variable "vpc_name" {
  description = "Name of existing VPC (required when vpc_mode = 'existing')"
  type        = string
  default     = ""
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "memory_name" {
  description = "AgentCore Memory resource name"
  type        = string
}

# --- Gateway Tools (domain-specific) ---

variable "gateway_tools" {
  description = "List of Lambda tools to register in AgentCore Gateway (domain-specific)"
  type = list(object({
    name        = string
    tool_name   = string
    description = string
    lambda_arn  = string
  }))
  default = []
}

variable "gateway_auth_type" {
  description = "Gateway auth: COGNITO (creates User Pool), AWS_IAM (simple), or CUSTOM_JWT (bring your own OIDC)"
  type        = string
  default     = "AWS_IAM"
}

# --- Runtime Environment (domain-specific) ---

variable "runtime_environment_variables" {
  description = "Domain-specific env vars for AgentCore Runtime container (model IDs, etc.)"
  type        = map(string)
  default     = {}
}

# --- Knowledge Base ---

variable "knowledge_base_enabled" {
  description = "Enable Knowledge Base deployment (creates OpenSearch Serverless + S3 + KB)"
  type        = bool
  default     = true
}

variable "embedding_model_id" {
  description = "Bedrock embedding model ID for Knowledge Base"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "vector_store_type" {
  description = "KB vector store: S3 (cheap) or OPENSEARCH_SERVERLESS (hybrid search, low latency)"
  type        = string
  default     = "S3"
}

variable "chunking_strategy" {
  description = "KB chunking strategy: DEFAULT, FIXED_SIZE, SEMANTIC, NONE"
  type        = string
  default     = "FIXED_SIZE"
}

# --- WhatsApp ---

variable "image_tag" {
  description = "Docker image tag for runtime container (e.g. git SHA or CI build number)"
  type        = string
}

variable "whatsapp_enabled" {
  description = "Enable WhatsApp channel deployment"
  type        = bool
  default     = true
}

variable "whatsapp_lambda_source_dir" {
  description = "Path to WhatsApp Lambda source code"
  type        = string
  default     = "../../src/channels/whatsapp"
}

variable "whatsapp_token" {
  description = "WhatsApp Business API access token"
  type        = string
  default     = ""
  sensitive   = true
}

variable "whatsapp_app_secret" {
  description = "WhatsApp app secret for HMAC signature validation"
  type        = string
  default     = ""
  sensitive   = true
}

variable "whatsapp_verify_token" {
  description = "WhatsApp webhook verification token"
  type        = string
  default     = ""
  sensitive   = true
}

variable "whatsapp_phone_number_id" {
  description = "WhatsApp Business Phone Number ID"
  type        = string
  default     = ""
}
