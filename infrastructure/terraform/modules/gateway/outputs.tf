output "gateway_url" {
  description = "URL do AgentCore Gateway (endpoint MCP)"
  value       = aws_bedrockagentcore_gateway.this.gateway_url
}

output "oauth_client_id" {
  description = "Cognito OAuth2 client ID"
  value       = aws_cognito_user_pool_client.gateway.id
}

output "oauth_client_secret" {
  description = "Cognito OAuth2 client secret"
  value       = aws_cognito_user_pool_client.gateway.client_secret
  sensitive   = true
}

output "token_endpoint" {
  description = "Cognito token endpoint para Client Credentials flow"
  value       = "https://${var.name_prefix}-gateway.auth.${var.aws_region}.amazoncognito.com/oauth2/token"
}
