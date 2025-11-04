import json
import logging

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):  # noqa: ARG001
    """
    Search the internet for information (mock implementation).

    This is a global MCP tool deployed to AgentCore Gateway.
    In production, this would integrate with a real search API (Google, Bing, etc.).
    """
    # Log invocation for debugging
    logger.info(
        json.dumps(
            {
                "tool": "web_search",
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
        query = body.get("query", "")
        max_results = body.get("max_results", 5)

        logger.info(json.dumps({"action": "search", "query": query, "max_results": max_results}))

        # Validate input
        if not query:
            return {"error": "query is required"}

        # Mock search results
        # In production, replace with actual search API call:
        # - Google Custom Search API
        # - Bing Search API
        # - DuckDuckGo API
        # - Tavily AI Search API
        results = [
            {
                "title": f"Result 1 for: {query}",
                "url": "https://example.com/result1",
                "snippet": f"This is a mock search result for the query: {query}. In production, this would connect to a real search API like Google Custom Search or Tavily.",
                "relevance_score": 0.95,
            },
            {
                "title": f"{query} - Complete Guide",
                "url": "https://example.com/guide",
                "snippet": f"A comprehensive guide about {query} with detailed information and best practices.",
                "relevance_score": 0.88,
            },
            {
                "title": f"Latest Updates on {query}",
                "url": "https://example.com/news",
                "snippet": "Recent news and updates related to your search query.",
                "relevance_score": 0.75,
            },
        ]

        # Limit results
        results = results[:max_results]

        logger.info(json.dumps({"action": "success", "results_count": len(results)}))
        return {
            "query": query,
            "results": results,
            "total": len(results),
            "source": "mock",  # In production, indicate actual search provider
        }

    except Exception as e:
        logger.error(json.dumps({"action": "error", "error": str(e)}), exc_info=True)
        return {"error": str(e)}
