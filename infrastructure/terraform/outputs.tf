output "runtime_arn" {
  description = "ARN do AgentCore Runtime"
  value       = module.runtime.runtime_arn
}

output "runtime_endpoint" {
  description = "URL do endpoint do AgentCore Runtime"
  value       = module.runtime.runtime_endpoint
}

output "memory_id" {
  description = "ID do AgentCore Memory store"
  value       = module.memory.memory_id
}

output "gateway_url" {
  description = "URL do AgentCore Gateway (endpoint MCP)"
  value       = module.gateway.gateway_url
}

output "lambda_function_name" {
  description = "Nome da função Lambda do canal WhatsApp"
  value       = module.whatsapp.lambda_function_name
}

output "api_gateway_url" {
  description = "URL base do API Gateway que recebe os webhooks do WhatsApp"
  value       = module.whatsapp.api_gateway_url
}

output "whatsapp_webhook_url" {
  description = "URL completa do webhook para configurar no Meta Developer Portal"
  value       = module.whatsapp.webhook_url
}
