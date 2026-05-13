# -----------------------------------------------------------------------------
# Bedrock Guardrails — banQi Consignado
# Proteções: prompt attack detection + topic policy (fora do escopo consignado)
# -----------------------------------------------------------------------------

resource "aws_bedrock_guardrail" "this" {
  name        = "${var.name_prefix}-guardrail"
  description = "Guardrail para ${var.name_prefix} — restringe ao escopo de empréstimo consignado"

  blocked_input_messaging   = "Olá! Sou o assistente de empréstimo consignado do banQi. Posso te ajudar a simular ou contratar seu empréstimo. Como posso ajudar?"
  blocked_outputs_messaging = "Desculpe, não consegui processar essa solicitação. Posso te ajudar com simulação ou contratação de empréstimo consignado. O que você precisa?"

  # Prompt attack detection — HIGH sensitivity
  contextual_grounding_policy_config {
    filters_config {
      type      = "GROUNDING"
      threshold = 0.7
    }
    filters_config {
      type      = "RELEVANCE"
      threshold = 0.7
    }
  }

  content_policy_config {
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
    filters_config {
      type            = "HATE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "INSULTS"
      input_strength  = "MEDIUM"
      output_strength = "MEDIUM"
    }
    filters_config {
      type            = "SEXUAL"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "VIOLENCE"
      input_strength  = "MEDIUM"
      output_strength = "MEDIUM"
    }
  }

  # Bloqueia assuntos completamente fora do escopo consignado
  topic_policy_config {
    topics_config {
      name       = "off-topic-consignado"
      definition = "Perguntas ou pedidos não relacionados a empréstimo consignado, simulação de crédito consignado, contratação, proposta, biometria, dados pessoais para empréstimo, ou status de contrato consignado banQi."
      type       = "DENY"
      examples   = [
        "Qual a capital da França?",
        "Me conta uma piada",
        "Escreva um código Python para mim",
        "Quem ganhou a Copa do Mundo?",
        "Consulta de saldo da conta",
        "Extrato bancário",
        "Transferência PIX",
      ]
    }
  }

  # PII masking para logs (não bloqueia o input — mascarado via regex nos logs)
  sensitive_information_policy_config {
    pii_entities_config {
      type   = "CPF"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "EMAIL"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "PHONE"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "NAME"
      action = "ANONYMIZE"
    }
  }

  tags = { Name = "${var.name_prefix}-guardrail" }
}
