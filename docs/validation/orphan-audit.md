# Orphan Audit — SSM Producers vs Consumers

Overview

This audit maps SSM parameters produced by shared infrastructure to their consumers across agents, frontend, packages, and scripts. Goal: identify parameters that have no readers (producer-only) or readers referencing parameters that are never written (consumer-only). Findings are based on repository-wide searches at commit time.

Legend
- Producer: Where a parameter is created or updated
- Consumer: Where a parameter is read/required
- Status: OK (matched), Gap (producer-only or consumer-only), N/A (optional feature)

SSM Prefix
- Standardized: /agentcore/{env}/...

Identity (/agentcore/{env}/identity/*)
- Producers:
  - infrastructure/terraform/modules/identity/outputs.tf — writes pool_id, machine_client_id, client_secret (SecureString), frontend_client_id, frontend_client_secret (SecureString), domain
- Consumers:
  - infrastructure/terraform/custom-resources/agentcore-gateway/lambda_function.py — reads pool_id, machine_client_id
  - frontend/streamlit_app/config.py — reads pool_id, frontend_client_id, frontend_client_secret (SecureString), domain
  - agent-config/customer-support.yaml — reads pool_id, machine_client_id, client_secret, domain
  - scripts/infra/validate.sh — validates presence of identity parameters
  - tests/unit/frontend/test_config.py — mocks identity params
- Status: OK

Gateway (/agentcore/{env}/gateway/*)
- Producers:
  - infrastructure/terraform/custom-resources/agentcore-gateway/lambda_function.py — writes gateway_id, gateway_arn, invoke_url, role_arn
- Consumers:
  - infrastructure/terraform/modules/gateway/outputs.tf — data sources for invoke_url
  - frontend/streamlit_app/config.py — reads invoke_url
  - agent-config/customer-support.yaml — api_url via ${SSM:/agentcore/dev/gateway/invoke_url}
  - scripts/infra/validate.sh — validates presence of gateway parameters
- Status: OK

Memory (/agentcore/{env}/memory/*)
- Producers:
  - infrastructure/terraform/custom-resources/agentcore-memory/lambda_function.py — writes memory_id, memory_arn, enabled_strategies, short_term_ttl, embedding_model_arn (if SEMANTIC enabled)
- Consumers:
  - packages/agentcore-tools/src/agentcore_tools/memory.py — reads memory_id
  - infrastructure/terraform/modules/memory/outputs.tf — reads enabled_strategies
  - infrastructure/terraform/modules/runtime/README.md — documents reading memory_id, iam_policy_arn
  - agent-config/customer-support.yaml — reads memory_id, enabled_strategies
  - scripts/infra/validate.sh — validates memory parameters
- Status: OK

Knowledge Base (/agentcore/{env}/kb/*)
- Producers:
  - Not using SSM for KB in this template; resources are returned as Terraform outputs and used directly.
- Consumers:
  - N/A
- Status: N/A (optional component disabled by default)

Other Shared Signals
- Observability: No SSM parameters written; configuration is via Terraform variables and resource properties.
- Runtime: Reads from identity/gateway/memory SSM; no additional SSM producers.

Outcomes
- No orphaned parameters detected: every produced SSM parameter has at least one consumer, and all consumer references have corresponding producers in infrastructure.
- SSM prefix consistency validated across modules and apps: /agentcore/{env}/...

Follow-ups
- If new parameters are added, update scripts/infra/validate.sh to include presence checks.
- For optional components (Knowledge Base), add SSM only when a stable consumer contract is established.
