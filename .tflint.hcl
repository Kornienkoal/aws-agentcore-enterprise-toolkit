# TFLint Configuration for AgentCore Infrastructure
#
# Enforces Terraform best practices and AWS-specific rules.
# Reference: https://github.com/terraform-linters/tflint

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

plugin "aws" {
  enabled = true
  version = "0.31.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

# Enforce rules
rule "terraform_naming_convention" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}

rule "terraform_unused_declarations" {
  enabled = true
}

rule "terraform_required_version" {
  enabled = true
}

rule "terraform_required_providers" {
  enabled = true
}

# AWS-specific rules
rule "aws_resource_missing_tags" {
  enabled = true
  tags    = ["Environment", "Component", "ManagedBy", "AgentCore"]
}
