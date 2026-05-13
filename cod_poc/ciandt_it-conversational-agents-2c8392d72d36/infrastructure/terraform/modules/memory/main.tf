# -----------------------------------------------------------------------------
# AgentCore Memory
# -----------------------------------------------------------------------------
resource "aws_bedrockagentcore_memory" "this" {
  name                   = var.memory_name
  description            = "AgentCore Memory for ${var.name_prefix}"
  event_expiry_duration  = 90
}

resource "aws_bedrockagentcore_memory_strategy" "semantic" {
  memory_id  = aws_bedrockagentcore_memory.this.id
  name       = "semantic_${replace(var.name_prefix, "-", "_")}"
  type       = "SEMANTIC"
  namespaces = ["/users/{actorId}/facts"]
}

resource "aws_bedrockagentcore_memory_strategy" "summary" {
  memory_id  = aws_bedrockagentcore_memory.this.id
  name       = "summary_${replace(var.name_prefix, "-", "_")}"
  type       = "SUMMARIZATION"
  namespaces = ["/summaries/{actorId}/{sessionId}"]
}

resource "aws_bedrockagentcore_memory_strategy" "user_preference" {
  memory_id  = aws_bedrockagentcore_memory.this.id
  name       = "user_pref_${replace(var.name_prefix, "-", "_")}"
  type       = "USER_PREFERENCE"
  namespaces = ["/users/{actorId}/preferences"]
}
