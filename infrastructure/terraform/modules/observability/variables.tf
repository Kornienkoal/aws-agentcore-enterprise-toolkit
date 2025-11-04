# Observability Module Variables

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "agent_namespace" {
  description = "Agent namespace for resource naming"
  type        = string
}

variable "xray_tracing" {
  description = "Enable X-Ray tracing"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days"
  type        = number
  default     = 7
}

variable "enable_log_encryption" {
  description = "Enable KMS encryption for CloudWatch Logs"
  type        = bool
  default     = false
}

variable "xray_sampling_rate" {
  description = "X-Ray sampling rate (0.0-1.0)"
  type        = number
  default     = 0.1
}

variable "error_rate_threshold" {
  description = "Error rate threshold for CloudWatch alarms (percentage)"
  type        = number
  default     = 5
}

variable "gateway_latency_threshold_ms" {
  description = "Bedrock Gateway latency threshold in milliseconds"
  type        = number
  default     = 5000 # 5 seconds

  validation {
    condition     = var.gateway_latency_threshold_ms > 0
    error_message = "Gateway latency threshold must be positive"
  }
}

variable "gateway_error_threshold" {
  description = "Bedrock Gateway error count threshold"
  type        = number
  default     = 10

  validation {
    condition     = var.gateway_error_threshold > 0
    error_message = "Gateway error threshold must be positive"
  }
}

variable "memory_throttle_threshold" {
  description = "Bedrock Memory throttle count threshold"
  type        = number
  default     = 5

  validation {
    condition     = var.memory_throttle_threshold > 0
    error_message = "Memory throttle threshold must be positive"
  }
}

variable "memory_latency_threshold_ms" {
  description = "Bedrock Memory read latency threshold in milliseconds"
  type        = number
  default     = 1000 # 1 second

  validation {
    condition     = var.memory_latency_threshold_ms > 0
    error_message = "Memory latency threshold must be positive"
  }
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
