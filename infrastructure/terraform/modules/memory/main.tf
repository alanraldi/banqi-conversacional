# -----------------------------------------------------------------------------
# AgentCore Memory — banQi Consignado
# Estratégias: SEMANTIC (dados do usuário), SUMMARIZATION (resumo de sessão)
# -----------------------------------------------------------------------------

resource "aws_bedrockagentcore_memory" "this" {
  name                  = var.memory_name
  description           = "AgentCore Memory para ${var.name_prefix} — dados de contratação consignado"
  event_expiry_duration = 90
}

resource "aws_bedrockagentcore_memory_strategy" "consignado_facts" {
  memory_id  = aws_bedrockagentcore_memory.this.id
  name       = "consignado_facts_${replace(var.name_prefix, "-", "_")}"
  type       = "SEMANTIC"
  namespaces = ["/users/{actorId}/consignado"]
}

resource "aws_bedrockagentcore_memory_strategy" "session_summary" {
  memory_id  = aws_bedrockagentcore_memory.this.id
  name       = "session_summary_${replace(var.name_prefix, "-", "_")}"
  type       = "SUMMARIZATION"
  namespaces = ["/summaries/{actorId}/{sessionId}"]
}
