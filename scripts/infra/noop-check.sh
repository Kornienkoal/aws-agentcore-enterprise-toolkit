#!/usr/bin/env bash
# AgentCore No-Op Plan Assertion
#
# Asserts that terraform plan produces no changes when configuration is unchanged.
# Useful for CI/CD to verify idempotent deployments.
# Implements: T052 [US3] - CI-friendly no-op checks
#
# Usage:
#   ./scripts/infra/noop-check.sh <environment>
#
# Example:
#   ./scripts/infra/noop-check.sh dev
#
# Exit Codes:
#   0 = No-op verified (no changes)
#   1 = Changes detected (not idempotent) or error

set -euo pipefail

# Colors for output (disable in CI)
if [[ "${CI:-false}" == "true" ]]; then
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
else
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
fi

# Configuration
ENVIRONMENT="${1:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"
TERRAFORM_DIR="infrastructure/terraform/envs/${ENVIRONMENT}"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Validation
if [[ -z "$ENVIRONMENT" ]]; then
    log_error "Environment required"
    echo "Usage: $0 <environment>"
    exit 1
fi

if [[ ! -d "$TERRAFORM_DIR" ]]; then
    log_error "Terraform directory not found: $TERRAFORM_DIR"
    exit 1
fi

# Main no-op check
main() {
    log_info "AgentCore No-Op Plan Assertion"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Region: ${AWS_REGION}"
    echo ""

    # Check AWS credentials
    log_info "Verifying AWS credentials..."
    if ! aws sts get-caller-identity &>/dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi
    log_success "AWS credentials valid"
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
    fi
    echo ""

    # Run terraform plan with detailed exit code
    log_info "Running terraform plan (expecting no changes)..."
    echo ""

    local plan_output
    local exit_code

    # Capture plan output and exit code
    set +e
    plan_output=$(terraform plan -detailed-exitcode -no-color -input=false 2>&1)
    exit_code=$?
    set -e

    # Analyze exit code
    case $exit_code in
        0)
            # No changes - SUCCESS
            log_success "NO-OP VERIFIED"
            echo ""
            echo "✓ Infrastructure is idempotent"
            echo "✓ No changes detected"
            echo "✓ Plan matches current state"
            echo ""

            # Show resource count
            local resource_count=$(terraform state list 2>/dev/null | wc -l | xargs)
            log_info "Managing ${resource_count} resources"
            echo ""

            exit 0
            ;;

        1)
            # Error occurred - FAILURE
            echo "$plan_output"
            echo ""
            log_error "TERRAFORM PLAN ERROR"
            echo ""
            echo "Plan failed to execute. This indicates a configuration or access issue."
            echo ""
            exit 1
            ;;

        2)
            # Changes detected - FAILURE
            echo "$plan_output"
            echo ""
            log_error "NO-OP ASSERTION FAILED"
            echo ""
            echo "✗ Changes detected when none expected"
            echo "✗ Infrastructure is NOT idempotent"
            echo ""

            # Parse changes
            local additions=$(echo "$plan_output" | grep -c "will be created" || echo "0")
            local changes=$(echo "$plan_output" | grep -c "will be updated" || echo "0")
            local deletions=$(echo "$plan_output" | grep -c "will be destroyed" || echo "0")

            log_warning "Detected Changes:"
            echo "  • Resources to add:    $additions"
            echo "  • Resources to change: $changes"
            echo "  • Resources to delete: $deletions"
            echo ""

            # List affected resources
            log_info "Affected Resources:"
            echo "$plan_output" | grep -E "^  # " | sed 's/^  # /  - /' | head -10 || echo "  (See plan output above)"
            echo ""

            # Provide troubleshooting guidance
            echo "========================================="
            echo "Troubleshooting Non-Idempotent Changes"
            echo "========================================="
            echo ""
            echo "Common causes:"
            echo ""
            echo "1. Dynamic attributes without lifecycle ignore rules"
            echo "   Example: timestamps, computed IDs"
            echo "   Fix: Add lifecycle { ignore_changes = [attribute] }"
            echo ""
            echo "2. Default values changed between Terraform versions"
            echo "   Fix: Explicitly set all attribute values"
            echo ""
            echo "3. Provider version differences"
            echo "   Fix: Pin provider versions in versions.tf"
            echo ""
            echo "4. Terraform state drift"
            echo "   Check: ./scripts/infra/drift-check.sh ${ENVIRONMENT}"
            echo ""
            echo "5. Manual AWS Console changes"
            echo "   Fix: Revert manual changes or import into Terraform"
            echo ""
            echo "6. Non-deterministic resource ordering"
            echo "   Fix: Add explicit depends_on relationships"
            echo ""
            echo "To fix:"
            echo "  1. Review plan output above"
            echo "  2. Identify root cause of changes"
            echo "  3. Update Terraform configuration"
            echo "  4. Apply changes: terraform apply"
            echo "  5. Re-run no-op check"
            echo ""

            exit 1
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

# Run no-op check
main "$@"
