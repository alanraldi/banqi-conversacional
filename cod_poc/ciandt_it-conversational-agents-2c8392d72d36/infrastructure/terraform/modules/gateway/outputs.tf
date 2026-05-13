output "gateway_arn" {
  value = aws_bedrockagentcore_gateway.this.gateway_arn
}

output "gateway_id" {
  value = aws_bedrockagentcore_gateway.this.gateway_id
}

output "gateway_url" {
  value = aws_bedrockagentcore_gateway.this.gateway_url
}

output "target_ids" {
  value = { for k, v in aws_bedrockagentcore_gateway_target.tools : k => v.target_id }
}

# OAuth credentials (populated when gateway_auth_type = COGNITO)
output "oauth_config" {
  description = "OAuth configuration for GatewayTokenManager (empty when AWS_IAM)"
  value = local.use_cognito ? {
    client_id      = aws_cognito_user_pool_client.gateway[0].id
    client_secret  = aws_cognito_user_pool_client.gateway[0].client_secret
    token_endpoint = "https://${aws_cognito_user_pool_domain.gateway[0].domain}.auth.${var.aws_region}.amazoncognito.com/oauth2/token"
    scope          = local.gateway_scope
    user_pool_id   = aws_cognito_user_pool.gateway[0].id
  } : null
  sensitive = true
}
