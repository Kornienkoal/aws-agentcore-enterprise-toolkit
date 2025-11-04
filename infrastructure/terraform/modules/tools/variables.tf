# Tools Module Variables

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "agent_namespace" {
  description = "Agent namespace for resource naming (e.g., 'agentcore', 'myorg/team')"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9/-]+$", var.agent_namespace))
    error_message = "Agent namespace must contain only lowercase letters, numbers, and forward slashes"
  }
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}

variable "gateway_ready_token" {
  description = "Token emitted by the gateway module indicating provisioning completion"
  type        = string
}

variable "tools" {
  description = "List of global tools to deploy. Each tool must define: name, source_dir. Optional: handler, description, memory_size, timeout, environment"
  type = list(object({
    name        = string
    source_dir  = string
    handler     = optional(string)
    description = optional(string)
    memory_size = optional(number)
    timeout     = optional(number)
    environment = optional(map(string))
  }))
}
