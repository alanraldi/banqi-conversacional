# -----------------------------------------------------------------------------
# AgentCore Gateway — supports COGNITO, AWS_IAM, or CUSTOM_JWT auth
# -----------------------------------------------------------------------------

locals {
  use_cognito    = var.gateway_auth_type == "COGNITO"
  use_custom_jwt = var.gateway_auth_type == "CUSTOM_JWT"
  use_jwt        = local.use_cognito || local.use_custom_jwt

  # Cognito OIDC discovery URL (auto-generated)
  cognito_discovery_url = local.use_cognito ? "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.gateway[0].id}/.well-known/openid-configuration" : ""

  # Final discovery URL: Cognito auto or user-provided
  discovery_url = local.use_cognito ? local.cognito_discovery_url : var.gateway_jwt_discovery_url

  # Authorizer type for the gateway resource
  authorizer_type = local.use_jwt ? "CUSTOM_JWT" : "AWS_IAM"

  # OAuth scope
  gateway_scope = "${var.name_prefix}-gateway/invoke"
}

# =============================================================================
# Cognito — only when gateway_auth_type = COGNITO
# =============================================================================

resource "aws_cognito_user_pool" "gateway" {
  count = local.use_cognito ? 1 : 0
  name  = "${var.name_prefix}-gateway-pool"

  tags = { Name = "${var.name_prefix}-gateway-pool" }
}

resource "aws_cognito_user_pool_domain" "gateway" {
  count        = local.use_cognito ? 1 : 0
  domain       = "${var.name_prefix}-gateway"
  user_pool_id = aws_cognito_user_pool.gateway[0].id
}

resource "aws_cognito_resource_server" "gateway" {
  count      = local.use_cognito ? 1 : 0
  identifier = "${var.name_prefix}-gateway"
  name       = "${var.name_prefix}-gateway"

  user_pool_id = aws_cognito_user_pool.gateway[0].id

  scope {
    scope_name        = "invoke"
    scope_description = "Invoke gateway tools"
  }
}

resource "aws_cognito_user_pool_client" "gateway" {
  count        = local.use_cognito ? 1 : 0
  name         = "${var.name_prefix}-gateway-client"
  user_pool_id = aws_cognito_user_pool.gateway[0].id

  generate_secret              = true
  allowed_oauth_flows          = ["client_credentials"]
  allowed_oauth_scopes         = ["${var.name_prefix}-gateway/invoke"]
  allowed_oauth_flows_user_pool_client = true

  depends_on = [aws_cognito_resource_server.gateway]
}

# =============================================================================
# AgentCore Gateway
# =============================================================================

resource "aws_bedrockagentcore_gateway" "this" {
  name            = "${var.name_prefix}-gateway"
  description     = "MCP Gateway for ${var.agent_name}"
  protocol_type   = "MCP"
  authorizer_type = local.authorizer_type
  role_arn        = var.role_arn

  protocol_configuration {
    mcp {
      search_type = "SEMANTIC"
    }
  }

  dynamic "authorizer_configuration" {
    for_each = local.use_jwt ? [1] : []
    content {
      custom_jwt_authorizer {
        discovery_url  = local.discovery_url
        allowed_scopes = local.use_cognito ? [local.gateway_scope] : []
      }
    }
  }
}

# =============================================================================
# Gateway Targets — one per tool (domain config)
# =============================================================================

resource "aws_bedrockagentcore_gateway_target" "tools" {
  for_each = { for t in var.gateway_tools : t.tool_name => t }

  gateway_identifier = aws_bedrockagentcore_gateway.this.gateway_id
  name               = each.value.name
  description        = each.value.description

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = each.value.lambda_arn

        tool_schema {
          inline_payload {
            name        = each.value.tool_name
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
