variable "name_prefix" {
  description = "Prefix for resource naming"
  type        = string
}

variable "memory_name" {
  description = "Name of the AgentCore Memory store"
  type        = string
  default     = "BanqiConsignadoMemory"
}
