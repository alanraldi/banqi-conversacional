# -----------------------------------------------------------------------------
# AgentCore Gateway (MCP) — 8 targets HTTP para APIs banQi Consignado
# Auth: Cognito OAuth2 Client Credentials
# -----------------------------------------------------------------------------

locals {
  gateway_scope = "${var.name_prefix}-gateway/invoke"

  # 8 targets MCP para as APIs banQi consignado
  banqi_targets = {
    consent_term = {
      name        = "consent-term-get"
      description = "Busca o termo de consentimento LGPD do usuário"
      method      = "GET"
      path        = "/consent-term"
    }
    consent_term_accept = {
      name        = "consent-term-accept"
      description = "Registra aceite do termo de consentimento LGPD"
      method      = "POST"
      path        = "/consent-term/accept"
    }
    simulations_get = {
      name        = "simulations-get"
      description = "Consulta simulações de empréstimo consignado existentes do usuário"
      method      = "GET"
      path        = "/simulations"
    }
    simulations_post = {
      name        = "simulations-post"
      description = "Cria uma nova simulação de empréstimo consignado com valor e parcelas"
      method      = "POST"
      path        = "/simulations"
    }
    proposals = {
      name        = "proposals-get"
      description = "Consulta propostas de empréstimo consignado do usuário"
      method      = "GET"
      path        = "/proposals"
    }
    biometry = {
      name        = "biometry-start"
      description = "Inicia o processo de validação biométrica facial"
      method      = "POST"
      path        = "/biometry"
    }
    biometry_continue = {
      name        = "biometry-continue"
      description = "Envia o resultado da biometria e consulta o status da validação"
      method      = "POST"
      path        = "/biometry/continue"
    }
    proposals_accept = {
      name        = "proposals-accept"
      description = "Confirma e aceita a proposta de empréstimo consignado"
      method      = "POST"
      path        = "/proposals/accept"
    }
  }
}

# =============================================================================
# Cognito — OAuth2 Client Credentials para autenticar o Runtime no Gateway
# =============================================================================

resource "aws_cognito_user_pool" "gateway" {
  name = "${var.name_prefix}-gateway-pool"
  tags = { Name = "${var.name_prefix}-gateway-pool" }
}

resource "aws_cognito_user_pool_domain" "gateway" {
  domain       = "${var.name_prefix}-gateway"
  user_pool_id = aws_cognito_user_pool.gateway.id
}

resource "aws_cognito_resource_server" "gateway" {
  identifier   = "${var.name_prefix}-gateway"
  name         = "${var.name_prefix}-gateway"
  user_pool_id = aws_cognito_user_pool.gateway.id

  scope {
    scope_name        = "invoke"
    scope_description = "Invoke banQi consignado gateway tools"
  }
}

resource "aws_cognito_user_pool_client" "gateway" {
  name         = "${var.name_prefix}-gateway-client"
  user_pool_id = aws_cognito_user_pool.gateway.id

  generate_secret                      = true
  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_scopes                 = [local.gateway_scope]
  allowed_oauth_flows_user_pool_client = true

  depends_on = [aws_cognito_resource_server.gateway]
}

# =============================================================================
# AgentCore Gateway
# =============================================================================

resource "aws_bedrockagentcore_gateway" "this" {
  name            = "${var.name_prefix}-gateway"
  description     = "MCP Gateway para ${var.agent_name} — APIs banQi Consignado"
  protocol_type   = "MCP"
  authorizer_type = "CUSTOM_JWT"
  role_arn        = var.role_arn

  protocol_configuration {
    mcp {
      search_type = "SEMANTIC"
    }
  }

  authorizer_configuration {
    custom_jwt_authorizer {
      discovery_url  = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.gateway.id}/.well-known/openid-configuration"
      allowed_scopes = [local.gateway_scope]
    }
  }
}

# =============================================================================
# Gateway Targets — 8 targets HTTP para APIs banQi
# =============================================================================

resource "aws_bedrockagentcore_gateway_target" "banqi" {
  for_each = local.banqi_targets

  gateway_identifier = aws_bedrockagentcore_gateway.this.gateway_id
  name               = each.value.name
  description        = each.value.description

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      http_target {
        url    = "${var.banqi_api_base_url}${each.value.path}"
        method = each.value.method

        tool_schema {
          inline_payload {
            name        = each.value.name
            description = each.value.description

            input_schema {
              type        = "object"
              description = each.value.description
            }
          }
        }
      }
    }
  }
}
