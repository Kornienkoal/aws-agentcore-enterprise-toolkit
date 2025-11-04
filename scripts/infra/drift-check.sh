#!/usr/bin/env bash
# AgentCore Infrastructure Drift Detection
#
# Detects configuration drift between Terraform state and actual AWS resources.
# Implements: T051 [US3] - Drift detection using terraform plan -detailed-exitcode
#
# Usage:
#   ./scripts/infra/drift-check.sh <environment>
#
# Example:
#   ./scripts/infra/drift-check.sh dev
#
# Exit Codes:
#   0 = No drift detected
#   1 = Error occurred
#   2 = Drift detected

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-}"
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
    echo "Usage: $0 <environment>"
    echo "Example: $0 dev"
    exit 1
fi

if [[ ! -d "$TERRAFORM_DIR" ]]; then
    log_error "Terraform directory not found: $TERRAFORM_DIR"
    exit 1
fi

# Main drift detection
main() {
    echo "========================================="
    echo "AgentCore Infrastructure Drift Detection"
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

    # Navigate to Terraform directory
    cd "$TERRAFORM_DIR"

    # Initialize Terraform (if needed)
    if [[ ! -d ".terraform" ]]; then
        log_info "Initializing Terraform..."
        if ! terraform init -backend-config=../../globals/backend.tfvars &>/dev/null; then
            log_error "Terraform initialization failed"
            exit 1
        fi
        log_success "Terraform initialized"
        echo ""
    fi

    # Run terraform plan with detailed exit code
    log_info "Running drift detection (terraform plan -detailed-exitcode)..."
    echo ""

    local plan_output
    local exit_code

    # Capture plan output and exit code
    set +e
    plan_output=$(terraform plan -detailed-exitcode -no-color 2>&1)
    exit_code=$?
    set -e

    # Analyze exit code
    case $exit_code in
        0)
            # No changes needed
            echo ""
            log_success "NO DRIFT DETECTED"
            echo ""
            echo "Infrastructure matches Terraform configuration."
            echo "All resources are in sync with the state file."
            echo ""

            # Show resource summary
            log_info "Resource Summary:"
            terraform state list | wc -l | xargs echo "  Total resources managed:"
            echo ""

            exit 0
            ;;

        1)
            # Error occurred
            echo "$plan_output"
            echo ""
            log_error "TERRAFORM PLAN FAILED"
            echo ""
            echo "An error occurred while checking for drift."
            echo "Review the output above for details."
            echo ""
            exit 1
            ;;

        2)
            # Drift detected
            echo "$plan_output"
            echo ""
            log_warning "DRIFT DETECTED"
            echo ""
            echo "Infrastructure has drifted from Terraform configuration."
            echo ""

            # Parse and summarize changes
            local additions=$(echo "$plan_output" | grep -c "will be created" || echo "0")
            local changes=$(echo "$plan_output" | grep -c "will be updated" || echo "0")
            local deletions=$(echo "$plan_output" | grep -c "will be destroyed" || echo "0")

            echo "Summary of changes:"
            echo "  • Resources to add:    $additions"
            echo "  • Resources to change: $changes"
            echo "  • Resources to delete: $deletions"
            echo ""

            # Extract specific drifted resources
            log_info "Drifted Resources:"
            echo "$plan_output" | grep -E "^  # " | sed 's/^  # /  - /' || echo "  (See plan output above)"
            echo ""

            # Provide actionable guidance
            echo "========================================="
            echo "Drift Remediation Options"
            echo "========================================="
            echo ""
            echo "Option 1: Apply changes to match configuration"
            echo "  cd $TERRAFORM_DIR"
            echo "  terraform apply"
            echo ""
            echo "Option 2: Update configuration to match current state"
            echo "  Review changes and update .tf files"
            echo "  Then run: terraform plan"
            echo ""
            echo "Option 3: Import manually created resources"
            echo "  terraform import <resource_type>.<name> <resource_id>"
            echo ""
            echo "Option 4: Remove resources from state (if intentionally managed elsewhere)"
            echo "  terraform state rm <resource_address>"
            echo ""

            # Check for common drift causes
            log_info "Common Drift Causes:"
            echo "  • Manual changes via AWS Console"
            echo "  • Changes by other automation/scripts"
            echo "  • Missing lifecycle ignore rules for dynamic attributes"
            echo "  • AWS service-managed updates (e.g., AMI IDs, DNS records)"
            echo ""

            exit 2
            ;;

        *)
            # Unexpected exit code
            echo "$plan_output"
            echo ""
            log_error "UNEXPECTED EXIT CODE: $exit_code"
            exit 1
            ;;
    esac
}

# Run drift detection
main "$@"
