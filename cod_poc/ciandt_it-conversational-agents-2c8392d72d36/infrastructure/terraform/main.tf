locals {
  name_prefix = "${var.domain_slug}-${var.environment}"
}

module "network" {
  count  = var.vpc_mode != "none" ? 1 : 0
  source = "./modules/network"

  vpc_mode    = var.vpc_mode
  vpc_name    = var.vpc_name
  domain_slug = var.domain_slug
  environment = var.environment
  aws_region  = var.aws_region
}

module "iam" {
  source = "./modules/iam"

  name_prefix       = local.name_prefix
  domain_slug       = var.domain_slug
  agent_name        = var.agent_name
  aws_account_id    = var.aws_account_id
  aws_region        = var.aws_region
  environment       = var.environment
  ecr_repo_name     = "${local.name_prefix}-runtime"
  gateway_tool_arns = [for t in var.gateway_tools : t.lambda_arn]
}

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

  environment_variables = merge(var.runtime_environment_variables, {
    APP_ENV                    = var.environment
    AWS_REGION                 = var.aws_region
    AGENTCORE_MEMORY_ID        = module.memory.memory_id
    BEDROCK_GUARDRAIL_ID       = module.guardrails.guardrail_id
    BEDROCK_KB_ID              = var.knowledge_base_enabled ? module.knowledge_base[0].knowledge_base_id : ""
    AGENTCORE_GATEWAY_ENDPOINT = module.gateway.gateway_url
    GATEWAY_CLIENT_ID          = try(module.gateway.oauth_config.client_id, "")
    GATEWAY_CLIENT_SECRET      = try(module.gateway.oauth_config.client_secret, "")
    GATEWAY_TOKEN_ENDPOINT     = try(module.gateway.oauth_config.token_endpoint, "")
    GATEWAY_SCOPE              = try(module.gateway.oauth_config.scope, "")
  })
}

module "memory" {
  source = "./modules/memory"

  name_prefix = local.name_prefix
  memory_name = var.memory_name
}

module "gateway" {
  source = "./modules/gateway"

  name_prefix    = local.name_prefix
  agent_name     = var.agent_name
  role_arn       = module.iam.gateway_role_arn
  aws_account_id = var.aws_account_id
  aws_region        = var.aws_region
  gateway_tools     = var.gateway_tools
  gateway_auth_type = var.gateway_auth_type
}

# --- New modules (T-040, T-041) ---

module "guardrails" {
  source = "./modules/guardrails"

  name_prefix = local.name_prefix
}

module "knowledge_base" {
  count  = var.knowledge_base_enabled ? 1 : 0
  source = "./modules/knowledge_base"

  name_prefix        = local.name_prefix
  environment        = var.environment
  aws_region         = var.aws_region
  embedding_model_id = var.embedding_model_id
  vector_store_type  = var.vector_store_type
  chunking_strategy  = var.chunking_strategy
  kb_docs_path       = "${abspath("${path.module}/../..")}/domains/${var.domain_slug}/kb-docs"
  aoss_vpce_id       = var.vpc_mode != "none" ? module.network[0].aoss_vpce_id : ""
}

module "whatsapp" {
  count  = var.whatsapp_enabled ? 1 : 0
  source = "./modules/whatsapp"

  name_prefix              = local.name_prefix
  domain_slug              = var.domain_slug
  environment              = var.environment
  agent_name               = var.agent_name
  agentcore_runtime_arn    = module.runtime.runtime_arn
  agentcore_memory_id      = module.memory.memory_id
  lambda_role_arn          = module.iam.lambda_role_arn
  lambda_source_dir        = var.whatsapp_lambda_source_dir
  whatsapp_token           = var.whatsapp_token
  whatsapp_app_secret      = var.whatsapp_app_secret
  whatsapp_verify_token    = var.whatsapp_verify_token
  whatsapp_phone_number_id = var.whatsapp_phone_number_id
  private_subnet_ids       = var.vpc_mode != "none" ? module.network[0].private_subnet_ids : []
  lambda_security_group_id = var.vpc_mode != "none" ? module.network[0].security_group_ids.lambda : ""
  waf_acl_arn              = var.vpc_mode != "none" ? module.network[0].waf_acl_arn : ""
}
