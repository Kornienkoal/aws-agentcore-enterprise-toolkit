# Best Practices & CIS Mapping

Scope and Method

This document maps relevant CIS AWS Foundations Benchmark themes and AWS-recommended best practices to this template’s scope. It highlights what is covered by the template, what is intentionally out-of-scope (organization controls), and targeted recommendations. Evidence was gathered via repo-wide searches and inspection of Terraform modules.

Applicability Legend
- Covered: Implemented in this template
- Gap: Not implemented; recommendation provided
- Out-of-scope: Requires org-level or account-level controls beyond this template

Identity and Access Management
- IAM policies attached to users — Out-of-scope
  - Control: Disallow customer-managed policies attached directly to IAM users.
  - Reason: This template does not manage IAM users. Enforce via org governance (SCP/Identity Center).
- IAM admin privileges prohibited — Out-of-scope
  - Control: Prevent wildcard admin access grants.
  - Reason: Enforce via org policies and CI checks on IAM changes.
- Secrets management — Covered
  - Client secrets placed in SSM as SecureString: /agentcore/{env}/identity/client_secret and frontend_client_secret.
- Least-privilege IAM — Covered with justified exceptions
  - Bedrock AgentCore control-plane APIs (Gateway/Memory) currently require Resource = "*" for certain actions; documented in modules with rationale.
  - CloudWatch Logs KMS integration uses Resource = "*" with Conditions scoping to agent log groups (standard AWS pattern).
  - X-Ray sampling rules and policies use wildcards by design.

Logging and Monitoring
- CloudWatch Log group retention — Covered
  - observability module sets retention_in_days (default 7, configurable). Recommendation: increase for prod (e.g., 90–365).
- Log encryption — Covered (optional)
  - enable_log_encryption toggles KMS with rotation enabled; policy allows logs service access with scoped conditions.
- CloudTrail enabled and integrated — Out-of-scope
  - This template does not provision CloudTrail. Control is account-level; enable org-wide with centralized S3/KMS.

Networking and Compute
- EC2 security group restrictions — Out-of-scope
  - No EC2 security groups are created by this template.
- VPC Flow Logs — Out-of-scope
  - No VPCs are created by this template.

Storage (S3 and Data)
- S3 bucket public access block — Gap (for KB bucket)
  - knowledge/main.tf creates an S3 bucket for data source but does not explicitly configure aws_s3_bucket_public_access_block.
  - Recommendation: Add aws_s3_bucket_public_access_block for the knowledge base bucket when KB is enabled. Optionally enforce aws_s3_account_public_access_block at the account level (org control).
- S3 encryption and versioning — Covered
  - SSE-S3 enabled; versioning enabled for the knowledge base bucket.

Bedrock AgentCore Components
- Gateway and Memory provisioning — Covered
  - Custom resources write outputs to SSM; IAM narrowly scoped for SSM prefixes; PassRole constrained.
- Model invocation scope — Covered
  - Memory module restricts bedrock:InvokeModel to amazon.titan-embed-* for embeddings.

Frontend and Runtime
- OAuth client credentials — Covered
  - Frontend reads frontend_client_secret as SecureString; machine-to-machine client secret stored as SecureString.
- Config from SSM — Covered
  - All critical IDs and URLs are retrieved from SSM using the standardized /agentcore/{env}/ prefix.

Actionable Recommendations
- Production log retention: Increase observability.log_retention_days to at least 90 (ideally 365) for production.
- S3 public access blocking for KB: Add aws_s3_bucket_public_access_block to knowledge base S3 bucket when enabled.
- TFLint & tfsec: Consider adding TFLint/tfsec into CI to flag regressions (optional, not added by this cleanup as per constraints).
- Organization controls: Ensure CloudTrail, password policies, and IAM guardrails (no inline user policies, admin boundaries) are enforced at org level via SCP/Config/Control Tower.

Notes on Wildcards
- KMS for CloudWatch Logs: Resource = "*" with encryption context condition is the published AWS pattern to allow logs service to use the key for specific log groups.
- X-Ray: Sampling rule wildcards are required for rule matching semantics.
- Bedrock AgentCore control-plane: As provider and service mature, prefer ARNs/conditions that scope to gateway/* and memory/* when supported; revisit periodically.
