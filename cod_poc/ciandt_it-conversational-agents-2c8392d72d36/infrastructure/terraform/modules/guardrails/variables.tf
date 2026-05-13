variable "name_prefix" {
  type = string
}

variable "pii_entities" {
  description = "PII entity types to detect/anonymize (LGPD)"
  type = list(object({
    type   = string
    action = string
  }))
  default = []
}

variable "content_filters" {
  description = "Content filter types and strengths"
  type = list(object({
    type            = string
    input_strength  = string
    output_strength = string
  }))
  default = [
    # Apenas prompt attack — protege contra jailbreak/injection
    { type = "PROMPT_ATTACK", input_strength = "HIGH", output_strength = "NONE" },
  ]
}
