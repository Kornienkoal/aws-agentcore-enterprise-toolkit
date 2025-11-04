import json
import logging

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Mock service center database
SERVICE_CENTERS = [
    {
        "name": "Tech Solutions NYC",
        "address": "123 Broadway",
        "city": "New York",
        "region": "NY",
        "postal_code": "10001",
        "country": "US",
        "phone": "+1-212-555-0100",
        "url": "https://techsolutions.example.com/nyc",
    },
    {
        "name": "Manhattan Tech Repair",
        "address": "456 5th Avenue",
        "city": "New York",
        "region": "NY",
        "postal_code": "10018",
        "country": "US",
        "phone": "+1-212-555-0200",
        "url": "https://manhattanrepair.example.com",
    },
    {
        "name": "Silicon Valley Service Center",
        "address": "789 Market Street",
        "city": "San Francisco",
        "region": "CA",
        "postal_code": "94102",
        "country": "US",
        "phone": "+1-415-555-0100",
        "url": "https://svservices.example.com",
    },
    {
        "name": "Bay Area Tech Support",
        "address": "321 Mission Street",
        "city": "San Francisco",
        "region": "CA",
        "postal_code": "94105",
        "country": "US",
        "phone": "+1-415-555-0300",
    },
    {
        "name": "LA Tech Experts",
        "address": "555 Wilshire Blvd",
        "city": "Los Angeles",
        "region": "CA",
        "postal_code": "90017",
        "country": "US",
        "phone": "+1-213-555-0100",
        "url": "https://latechexperts.example.com",
    },
    {
        "name": "Austin Service Hub",
        "address": "100 Congress Ave",
        "city": "Austin",
        "region": "TX",
        "postal_code": "78701",
        "country": "US",
        "phone": "+1-512-555-0100",
        "url": "https://austinservices.example.com",
    },
    {
        "name": "Seattle Tech Care",
        "address": "200 Pine Street",
        "city": "Seattle",
        "region": "WA",
        "postal_code": "98101",
        "country": "US",
        "phone": "+1-206-555-0100",
    },
    {
        "name": "Chicago Support Center",
        "address": "300 Michigan Ave",
        "city": "Chicago",
        "region": "IL",
        "postal_code": "60601",
        "country": "US",
        "phone": "+1-312-555-0100",
        "url": "https://chicagotech.example.com",
    },
]


def handler(event, context):  # noqa: ARG001
    """
    Find authorized service centers by location.

    This is a global MCP tool deployed to AgentCore Gateway.
    Available to all agents via Gateway Target.
    """
    # Log invocation for debugging
    logger.info(
        json.dumps(
            {
                "tool": "service_locator",
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

        city = body.get("city", "").strip()
        region = body.get("region", "").strip()
        country = body.get("country", "US").strip().upper()
        max_results = body.get("max_results", 5)

        logger.info(
            json.dumps(
                {"action": "search_centers", "city": city, "region": region, "country": country}
            )
        )

        # Validate input
        if not city:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "city is required"}),
            }

        # Validate max_results range (note: JSON Schema validation not supported by Bedrock AgentCore API)
        if max_results < 1 or max_results > 10:
            max_results = 5

        # Search service centers
        results = []
        for center in SERVICE_CENTERS:
            # Match city (case-insensitive)
            if center["city"].lower() != city.lower():
                continue

            # Optional region filter
            if region and center["region"].lower() != region.lower():
                continue

            # Optional country filter
            if center["country"].upper() != country:
                continue

            results.append(center)

            # Limit results
            if len(results) >= max_results:
                break

        # Build response
        if not results:
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {
                        "message": f"No service centers found in {city}"
                        + (f", {region}" if region else "")
                        + f" ({country})",
                        "suggestion": "Try a nearby city or remove region filter",
                    }
                ),
            }

        response = {
            "query": {
                "city": city,
                "region": region or None,
                "country": country,
                "max_results": max_results,
            },
            "results_count": len(results),
            "service_centers": results,
        }

        logger.info(json.dumps({"action": "success", "results_count": len(results)}))
        return {"statusCode": 200, "body": json.dumps(response)}

    except Exception as e:
        logger.error(json.dumps({"action": "error", "error": str(e)}), exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
