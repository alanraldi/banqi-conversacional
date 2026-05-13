variable "vpc_mode" {
  description = "VPC provisioning mode: create or existing"
  type        = string
  default     = "create"
}

variable "vpc_name" {
  description = "Name tag of existing VPC (used when vpc_mode = existing)"
  type        = string
  default     = ""
}

variable "vpc_cidr" {
  description = "CIDR block for new VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "domain_slug" {
  description = "Domain slug for naming"
  type        = string
  default     = "banqi-consignado"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}
