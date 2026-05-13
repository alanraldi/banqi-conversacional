# -----------------------------------------------------------------------------
# Bedrock Guardrail — PII detection (LGPD) + content filtering
# -----------------------------------------------------------------------------

resource "aws_bedrock_guardrail" "this" {
  name                      = "${var.name_prefix}-guardrail"
  description               = "PII protection + content filtering for ${var.name_prefix}"
  blocked_input_messaging   = "Olá! 😊 Sou o assistente virtual do BanQi e posso te ajudar com consultas de saldo, extrato, simulação de empréstimos e informações sobre nossos produtos e serviços. Como posso te ajudar?"
  blocked_outputs_messaging = "Desculpe, não consegui processar essa solicitação. Posso te ajudar com serviços BanQi como consulta de saldo, extrato, empréstimos e informações sobre nossos produtos. O que você precisa?"

  dynamic "sensitive_information_policy_config" {
    for_each = length(var.pii_entities) > 0 ? [1] : []
    content {
      dynamic "pii_entities_config" {
        for_each = var.pii_entities
        content {
          type   = pii_entities_config.value.type
          action = pii_entities_config.value.action
        }
      }
    }
  }

  content_policy_config {
    dynamic "filters_config" {
      for_each = var.content_filters
      content {
        type             = filters_config.value.type
        input_strength   = filters_config.value.input_strength
        output_strength  = filters_config.value.output_strength
      }
    }
  }

  topic_policy_config {
    topics_config {
      name       = "off-topic"
      definition = "Questions or requests not related to BanQi banking services, financial products, account operations, loans, transactions, or customer support."
      type       = "DENY"
      examples   = [
        "Qual a capital da França?",
        "Me conta uma piada",
        "Escreva um código Python para mim",
        "Quem ganhou a Copa do Mundo?",
      ]
    }
  }

  tags = {
    Name = "${var.name_prefix}-guardrail"
  }
}
