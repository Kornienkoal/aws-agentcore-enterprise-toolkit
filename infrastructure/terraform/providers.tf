# AWS Provider Configuration
#
# Default provider configuration for AgentCore infrastructure.
# Specific configurations (region, profile) are set per environment.

provider "aws" {
  # Region set via environment variables or terraform.tfvars
  # Profile can be set via AWS_PROFILE environment variable

  default_tags {
    tags = var.common_tags
  }
}

variable "common_tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default     = {}
}
