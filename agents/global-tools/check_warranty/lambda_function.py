import json
import logging
from datetime import datetime

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Mock warranty database
WARRANTY_DB = {
    "laptop-x1": {
        "product_id": "laptop-x1",
        "product_name": "Professional Laptop X1",
        "purchase_date": "2024-01-15",
        "warranty_months": 24,
        "warranty_type": "Standard",
        "expires": "2026-01-15",
    },
    "monitor-hd27": {
        "product_id": "monitor-hd27",
        "product_name": "27-inch HD Monitor",
        "purchase_date": "2024-06-01",
        "warranty_months": 12,
        "warranty_type": "Standard",
        "expires": "2025-06-01",
    },
    "keyboard-k95": {
        "product_id": "keyboard-k95",
        "product_name": "Mechanical Keyboard K95",
        "purchase_date": "2023-12-10",
        "warranty_months": 36,
        "warranty_type": "Extended",
        "expires": "2026-12-10",
    },
}


def handler(event, context):  # noqa: ARG001
    """
    Check warranty status and coverage for a product.

    This is a global MCP tool deployed to AgentCore Gateway.
    Available to all agents via Gateway Target.
    """
    # Log invocation for debugging
    logger.info(
        json.dumps(
            {
                "tool": "check_warranty",
                "request_id": context.aws_request_id,
                "event_keys": list(event.keys()) if isinstance(event, dict) else "not_dict",
                "has_body": "body" in event if isinstance(event, dict) else False,
                "event_type": type(event).__name__,
            }
        )
    )

    try:
        # Parse input - handle both API Gateway and direct invocation formats
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        elif isinstance(event.get("body"), dict):
            body = event["body"]
        else:
            body = event
        product_id = body.get("product_id", "")
        user_id = body.get("user_id", "unknown")

        logger.info(json.dumps({"action": "warranty_lookup", "product_id": product_id}))

        # Validate input
        if not product_id:
            return {"error": "product_id is required"}

        # Look up warranty
        warranty = WARRANTY_DB.get(product_id)

        if not warranty:
            return {
                "error": f"Warranty not found for product: {product_id}",
                "available_products": list(WARRANTY_DB.keys()),
            }

        # Calculate warranty status
        expires_date = datetime.strptime(warranty["expires"], "%Y-%m-%d")
        today = datetime.now()
        is_active = today < expires_date
        days_remaining = (expires_date - today).days if is_active else 0

        # Build response - return data directly for Gateway MCP
        result = {
            **warranty,
            "is_active": is_active,
            "days_remaining": days_remaining,
            "status": "active" if is_active else "expired",
            "checked_by": user_id,
            "checked_at": today.isoformat(),
        }

        logger.info(
            json.dumps(
                {"action": "success", "status": result["status"], "days_remaining": days_remaining}
            )
        )
        return result

    except Exception as e:
        logger.error(json.dumps({"action": "error", "error": str(e)}), exc_info=True)
        return {"error": str(e)}
