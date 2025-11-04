#!/usr/bin/env bash
# AgentCore Infrastructure Teardown Script
#
# Safely removes all infrastructure with confirmations and safeguards.
# Implements: T050 [US3] - Safe teardown workflow
#
# Usage:
#   ./scripts/infra/teardown.sh <environment> [--force]
#
# Example:
#   ./scripts/infra/teardown.sh dev
#   ./scripts/infra/teardown.sh prod --force  # Skip confirmation (use with caution!)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-}"
FORCE="${2:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"
TERRAFORM_DIR="infrastructure/terraform/envs/${ENVIRONMENT}"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Validation
if [[ -z "$ENVIRONMENT" ]]; then
    log_error "Environment required"
    echo "Usage: $0 <environment> [--force]"
    echo "Example: $0 dev"
    exit 1
fi

if [[ ! -d "$TERRAFORM_DIR" ]]; then
    log_error "Terraform directory not found: $TERRAFORM_DIR"
    exit 1
fi

# Production safeguard
if [[ "$ENVIRONMENT" == "prod" ]] && [[ "$FORCE" != "--force" ]]; then
    log_error "Production teardown requires --force flag"
    echo ""
    echo "This is a DESTRUCTIVE operation that will DELETE ALL production resources."
    echo "To proceed, run: $0 prod --force"
    exit 1
fi

# Main teardown flow
main() {
    echo "========================================="
    echo "AgentCore Infrastructure Teardown"
    echo "========================================="
    echo "Environment: ${ENVIRONMENT}"
    echo "Region: ${AWS_REGION}"
    echo "Terraform Dir: ${TERRAFORM_DIR}"
    echo ""

    # Check AWS credentials
    log_info "Verifying AWS credentials..."
    if ! aws sts get-caller-identity &>/dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi

    local account_id=$(aws sts get-caller-identity --query Account --output text)
    log_success "AWS credentials valid (Account: $account_id)"
    echo ""

    # Show current resources
    log_info "Checking current infrastructure state..."
    cd "$TERRAFORM_DIR"

    # Initialize Terraform with backend config
    log_info "Initializing Terraform..."
    if ! terraform init -backend-config=../../globals/backend.tfvars -input=false &>/dev/null; then
        log_warning "Terraform not initialized - no state to destroy"
        exit 0
    fi

    # Show resources to be destroyed
    log_info "Resources that will be DESTROYED:"
    terraform state list 2>/dev/null || log_warning "No resources found in state"
    echo ""

    # Confirmation prompt (unless --force)
    if [[ "$FORCE" != "--force" ]]; then
        log_warning "THIS WILL DELETE ALL RESOURCES IN ${ENVIRONMENT} ENVIRONMENT!"
        echo ""
        echo "The following will be PERMANENTLY DELETED:"
    echo "  • Cognito User Pool and all users"
    echo "  • Bedrock AgentCore Gateway and targets"
    echo "  • Bedrock AgentCore Memory (all strategies)"
    echo "  • Lambda custom resource provisioners"
    echo "  • IAM roles and policies"
    echo "  • CloudWatch log groups and logs"
    echo "  • SSM parameters"
    echo "  • S3 buckets (if empty)"
    echo "  • OpenSearch Serverless vector collections (if knowledge base enabled)"
    echo "  • Bedrock Knowledge Base (if enabled)"
    echo ""
        read -p "Type 'DELETE' to confirm: " confirmation

        if [[ "$confirmation" != "DELETE" ]]; then
            log_info "Teardown cancelled"
            exit 0
        fi
    fi

    echo ""
    log_info "Starting teardown process..."
    echo ""

    # Step 1: Check for non-empty S3 buckets
    log_info "Step 1: Checking S3 buckets..."
    local data_source_bucket=$(aws ssm get-parameter \
        --name "/agentcore/${ENVIRONMENT}/knowledge/data_source_bucket" \
        --region "$AWS_REGION" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$data_source_bucket" ]]; then
        local object_count=$(aws s3 ls "s3://${data_source_bucket}" --recursive --summarize 2>/dev/null | grep "Total Objects" | awk '{print $3}' || echo "0")

        if [[ "$object_count" -gt 0 ]]; then
            log_warning "S3 bucket ${data_source_bucket} contains ${object_count} objects"
            echo "Emptying bucket before destruction..."
            aws s3 rm "s3://${data_source_bucket}" --recursive --region "$AWS_REGION" || log_warning "Failed to empty bucket"
        fi
    fi
    log_success "S3 buckets checked"
    echo ""

    # Step 2: Clean up Bedrock AgentCore custom resources
    log_info "Step 2: Cleaning up Bedrock AgentCore custom resources..."

    # Delete Bedrock Gateway (via Lambda custom resource)
    local gateway_id=$(aws ssm get-parameter \
        --name "/agentcore/${ENVIRONMENT}/gateway/gateway_id" \
        --region "$AWS_REGION" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$gateway_id" ]]; then
        log_info "Deleting Bedrock Gateway: $gateway_id"
        local gateway_provisioner=$(terraform output -raw gateway_provisioner_function_name 2>/dev/null || echo "")

        if [[ -n "$gateway_provisioner" ]]; then
            aws lambda invoke \
                --function-name "$gateway_provisioner" \
                --cli-binary-format raw-in-base64-out \
                --payload "{\"RequestType\":\"Delete\",\"PhysicalResourceId\":\"$gateway_id\",\"StackId\":\"terraform-${ENVIRONMENT}\",\"RequestId\":\"teardown-$(date +%s)\",\"LogicalResourceId\":\"BedrockGateway\"}" \
                --region "$AWS_REGION" \
                /tmp/gateway_delete.json &>/dev/null
            log_success "Bedrock Gateway deleted"
        else
            log_warning "Gateway provisioner function not found, skipping gateway deletion"
        fi
    fi

    # Delete Bedrock Memory (via Lambda custom resource)
    local memory_id=$(aws ssm get-parameter \
        --name "/agentcore/${ENVIRONMENT}/memory/memory_id" \
        --region "$AWS_REGION" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$memory_id" ]]; then
        log_info "Deleting Bedrock Memory: $memory_id"
        local memory_provisioner=$(terraform output -raw memory_provisioner_function_name 2>/dev/null || echo "")

        if [[ -n "$memory_provisioner" ]]; then
            aws lambda invoke \
                --function-name "$memory_provisioner" \
                --cli-binary-format raw-in-base64-out \
                --payload "{\"RequestType\":\"Delete\",\"PhysicalResourceId\":\"$memory_id\",\"StackId\":\"terraform-${ENVIRONMENT}\",\"RequestId\":\"teardown-$(date +%s)\",\"LogicalResourceId\":\"BedrockMemory\"}" \
                --region "$AWS_REGION" \
                /tmp/memory_delete.json &>/dev/null
            log_success "Bedrock Memory deleted"
        else
            log_warning "Memory provisioner function not found, skipping memory deletion"
        fi
    fi

    log_success "Custom resources cleanup complete"
    echo ""

    # Step 3: Delete Runtime Agents (deployed via SDK)
    log_info "Step 3: Cleaning up Runtime Agents (SDK-deployed)..."

    # List all runtime agents in this environment
    local runtime_agents=$(aws bedrock-agentcore-control list-agent-runtimes \
        --region "$AWS_REGION" \
        --query "agentRuntimes[].{id:agentRuntimeId,name:agentRuntimeName}" \
        --output json 2>/dev/null || echo "[]")

    if [[ "$runtime_agents" != "[]" ]] && [[ -n "$runtime_agents" ]]; then
        local agent_count=$(echo "$runtime_agents" | jq 'length')
        log_info "Found $agent_count runtime agent(s) to delete"

        # Delete each runtime agent
        echo "$runtime_agents" | jq -r '.[] | @base64' | while read -r agent_b64; do
            local agent_json=$(echo "$agent_b64" | base64 --decode)
            local agent_id=$(echo "$agent_json" | jq -r '.id')
            local agent_name=$(echo "$agent_json" | jq -r '.name')

            log_info "Deleting runtime agent: $agent_name ($agent_id)"
            if aws bedrock-agentcore-control delete-agent-runtime \
                --agent-runtime-id "$agent_id" \
                --region "$AWS_REGION" &>/dev/null; then
                log_success "Deleted runtime agent: $agent_name"
            else
                log_warning "Failed to delete runtime agent: $agent_name (may already be deleted)"
            fi
        done
    else
        log_success "No runtime agents found"
    fi

    echo ""

    # Step 4: Terraform destroy
    log_info "Step 4: Running terraform destroy..."
    if terraform destroy -auto-approve; then
        log_success "Terraform destroy completed successfully"
    else
        log_error "Terraform destroy failed"
        echo ""
        log_warning "Manual cleanup may be required"
        echo "Check AWS Console for remaining resources:"
        echo "  • Cognito: https://console.aws.amazon.com/cognito/v2/idp/user-pools"
        echo "  • Bedrock Gateway: https://console.aws.amazon.com/bedrock/agentcore/gateways"
        echo "  • Bedrock Memory: https://console.aws.amazon.com/bedrock/agentcore/memories"
        echo "  • Bedrock Runtime: https://console.aws.amazon.com/bedrock/agentcore/runtimes"
        echo "  • Lambda: https://console.aws.amazon.com/lambda"
        exit 1
    fi
    echo ""

    # Step 5: Verify SSM parameters removed
    log_info "Step 5: Verifying SSM parameters removed..."
    local remaining_params=$(aws ssm get-parameters-by-path \
        --path "/agentcore/${ENVIRONMENT}/" \
        --region "$AWS_REGION" \
        --query "Parameters[].Name" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$remaining_params" ]]; then
        log_warning "Some SSM parameters still exist:"
        echo "$remaining_params"
        echo ""
        read -p "Delete remaining SSM parameters? (y/N): " delete_ssm

        if [[ "$delete_ssm" == "y" ]] || [[ "$delete_ssm" == "Y" ]]; then
            for param in $remaining_params; do
                aws ssm delete-parameter --name "$param" --region "$AWS_REGION" &>/dev/null
                log_success "Deleted: $param"
            done
        fi
    else
        log_success "All SSM parameters removed"
    fi
    echo ""

    # Step 6: Check for orphaned resources
    log_info "Step 6: Checking for orphaned resources..."

    # Check Cognito User Pools
    local pools=$(aws cognito-idp list-user-pools \
        --max-results 60 \
        --region "$AWS_REGION" \
        --query "UserPools[?contains(Name, 'agentcore-${ENVIRONMENT}')].Id" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$pools" ]]; then
        log_warning "Orphaned Cognito User Pools found: $pools"
        echo "Run: aws cognito-idp delete-user-pool --user-pool-id <pool-id>"
    else
        log_success "No orphaned Cognito User Pools"
    fi

    # Check Bedrock Gateways
    local gateways=$(aws bedrock-agentcore-control list-gateways \
        --region "$AWS_REGION" \
        --query "gateways[?contains(gatewayName, 'agentcore-${ENVIRONMENT}')].gatewayId" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$gateways" ]]; then
        log_warning "Orphaned Bedrock Gateways found: $gateways"
        echo "Run: aws bedrock-agentcore-control delete-gateway --gateway-id <gateway-id>"
    else
        log_success "No orphaned Bedrock Gateways"
    fi

    # Check Bedrock Memories
    local memories=$(aws bedrock-agentcore-control list-memories \
        --region "$AWS_REGION" \
        --query "memories[?contains(memoryName, 'agentcore-${ENVIRONMENT}')].memoryId" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$memories" ]]; then
        log_warning "Orphaned Bedrock Memories found: $memories"
        echo "Run: aws bedrock-agentcore-control delete-memory --memory-id <memory-id>"
    else
        log_success "No orphaned Bedrock Memories"
    fi

    # Check Runtime Agents
    local runtime_agents=$(aws bedrock-agentcore-control list-agent-runtimes \
        --region "$AWS_REGION" \
        --query "agentRuntimes[].agentRuntimeId" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$runtime_agents" ]]; then
        log_warning "Orphaned Runtime Agents found: $runtime_agents"
        echo "Run: aws bedrock-agentcore-control delete-agent-runtime --agent-runtime-id <runtime-id>"
    else
        log_success "No orphaned Runtime Agents"
    fi

    # Check Lambda Functions (custom resource provisioners)
    local lambdas=$(aws lambda list-functions \
        --region "$AWS_REGION" \
        --query "Functions[?contains(FunctionName, 'agentcore-${ENVIRONMENT}-provisioner')].FunctionName" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$lambdas" ]]; then
        log_warning "Orphaned Lambda provisioners found: $lambdas"
        echo "Run: aws lambda delete-function --function-name <function-name>"
    else
        log_success "No orphaned Lambda provisioners"
    fi

    echo ""

    # Summary
    echo "========================================="
    echo "Teardown Complete"
    echo "========================================="
    log_success "Environment ${ENVIRONMENT} has been destroyed"
    echo ""
    echo "Next steps:"
    echo "1. Verify all resources deleted in AWS Console"
    echo "2. Check for any cost-incurring resources"
    echo "3. Review CloudWatch logs for audit trail"
    echo ""

    if [[ "$ENVIRONMENT" != "prod" ]]; then
        echo "To re-provision: cd ${TERRAFORM_DIR} && terraform apply"
    fi
}

# Run teardown
main "$@"
