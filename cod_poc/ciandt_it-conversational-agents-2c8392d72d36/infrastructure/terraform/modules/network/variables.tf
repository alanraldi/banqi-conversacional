variable "vpc_mode" {
  description = "VPC mode: 'create' or 'existing'"
  type        = string
}

variable "vpc_name" {
  description = "Name of existing VPC (used when vpc_mode = 'existing')"
  type        = string
  default     = ""
}

variable "vpc_cidr" {
  description = "CIDR block for new VPC (used when vpc_mode = 'create')"
  type        = string
  default     = "10.0.0.0/16"
}

variable "domain_slug" {
  type = string
}

variable "environment" {
  type = string
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}
