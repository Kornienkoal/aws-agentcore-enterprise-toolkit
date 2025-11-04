# Dev Environment Variables

variable "agent_namespace" {
  description = "Agent namespace (e.g., agentcore)"
  type        = string
}

variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "knowledge_enabled" {
  description = "Enable Bedrock Knowledge Base (optional)"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days"
  type        = number
  default     = 7
}

variable "xray_tracing" {
  description = "Enable X-Ray tracing"
  type        = bool
  default     = true
}

# Global tools to deploy via tools module
variable "global_tools" {
  description = "List of global tools (name, source_dir, optional handler/description/memory_size/timeout/environment)"
  type = list(object({
    name        = string
    source_dir  = string
    handler     = optional(string)
    description = optional(string)
    memory_size = optional(number)
    timeout     = optional(number)
    environment = optional(map(string))
  }))
  default = []
}
