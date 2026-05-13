locals {
  name_prefix = "${var.domain_slug}-${var.environment}"
}

# =============================================================================
# Network — VPC, subnets, SGs, VPC Endpoints, WAF
# =============================================================================

module "network" {
  count  = var.vpc_mode != "none" ? 1 : 0
  source = "./modules/network"

  vpc_mode    = var.vpc_mode
  vpc_name    = var.vpc_name
  domain_slug = var.domain_slug
  environment = var.environment
  aws_region  = var.aws_region
  vpc_cidr    = var.vpc_cidr
}

# =============================================================================
# IAM — Runtime, Lambda, Gateway roles
# =============================================================================

module "iam" {
  source = "./modules/iam"

  name_prefix    = local.name_prefix
  domain_slug    = var.domain_slug
  agent_name     = var.agent_name
  aws_account_id = var.aws_account_id
  aws_region     = var.aws_region
  environment    = var.environment
  ecr_repo_name  = "${local.name_prefix}-runtime"
}

# =============================================================================
# AgentCore Memory
# =============================================================================

module "memory" {
  source = "./modules/memory"

  name_prefix = local.name_prefix
  memory_name = var.agentcore_memory_name
}

# =============================================================================
# Bedrock Guardrails
# =============================================================================

module "guardrails" {
  source = "./modules/guardrails"

  name_prefix = local.name_prefix
}

# =============================================================================
# AgentCore Gateway (MCP — 8 banQi API targets)
# =============================================================================

module "gateway" {
  source = "./modules/gateway"

  name_prefix        = local.name_prefix
  agent_name         = var.agent_name
  role_arn           = module.iam.gateway_role_arn
  aws_account_id     = var.aws_account_id
  aws_region         = var.aws_region
  banqi_api_base_url = var.banqi_api_base_url
}

# =============================================================================
# AgentCore Runtime (container ARM64)
# =============================================================================

module "runtime" {
  source = "./modules/runtime"

  name_prefix        = local.name_prefix
  agent_name         = var.agent_name
  role_arn           = module.iam.runtime_role_arn
  ecr_repo_name      = "${local.name_prefix}-runtime"
  aws_region         = var.aws_region
  project_root       = abspath("${path.module}/../..")
  image_tag          = var.image_tag
  network_mode       = var.vpc_mode != "none" ? "VPC" : "PUBLIC"
  subnet_ids         = var.vpc_mode != "none" ? module.network[0].private_subnet_ids : []
  security_group_ids = var.vpc_mode != "none" ? [module.network[0].security_group_ids.runtime] : []

  environment_variables = {
    APP_ENV                    = var.environment
    AWS_REGION                 = var.aws_region
    DOMAIN_SLUG                = var.domain_slug
    AGENTCORE_MEMORY_ID        = module.memory.memory_id
    BEDROCK_GUARDRAIL_ID       = module.guardrails.guardrail_id
    AGENTCORE_GATEWAY_ENDPOINT = module.gateway.gateway_url
    GATEWAY_CLIENT_ID          = module.gateway.oauth_client_id
    GATEWAY_CLIENT_SECRET      = module.gateway.oauth_client_secret
    GATEWAY_TOKEN_ENDPOINT     = module.gateway.token_endpoint
    GATEWAY_SCOPE              = "${local.name_prefix}-gateway/invoke"
    SUPERVISOR_AGENT_MODEL_ID  = "us.anthropic.claude-sonnet-4-6-20250514-v1:0"
    CONSIGNADO_AGENT_MODEL_ID  = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    GENERAL_AGENT_MODEL_ID     = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    BANQI_API_BASE_URL         = var.banqi_api_base_url
    ERROR_MESSAGE_GENERIC      = "Desculpe, ocorreu um erro. Tente novamente em alguns instantes."
  }
}

# =============================================================================
# WhatsApp channel — Lambda + API GW + DynamoDB + WAF
# =============================================================================

module "whatsapp" {
  source = "./modules/whatsapp"

  name_prefix              = local.name_prefix
  domain_slug              = var.domain_slug
  environment              = var.environment
  agent_name               = var.agent_name
  agentcore_runtime_arn    = module.runtime.runtime_arn
  agentcore_memory_id      = module.memory.memory_id
  lambda_role_arn          = module.iam.lambda_role_arn
  whatsapp_token           = var.whatsapp_token
  whatsapp_app_secret      = var.whatsapp_app_secret
  whatsapp_verify_token    = var.whatsapp_verify_token
  whatsapp_phone_number_id = var.whatsapp_phone_number_id
  private_subnet_ids       = var.vpc_mode != "none" ? module.network[0].private_subnet_ids : []
  lambda_security_group_id = var.vpc_mode != "none" ? module.network[0].security_group_ids.lambda : ""
  waf_acl_arn              = var.vpc_mode != "none" ? module.network[0].waf_acl_arn : ""
}
