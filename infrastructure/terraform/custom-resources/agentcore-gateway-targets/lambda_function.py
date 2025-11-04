"""
Bedrock AgentCore Gateway Targets Custom Resource Handler

Registers/updates/deletes Gateway Targets (MCP tools) for a Bedrock AgentCore Gateway.
Handles Create, Update, and Delete operations with idempotency.

Author: AgentCore Template
Created: 2025-10-24
"""

from __future__ import annotations

import copy
import json
import os
import uuid
from typing import Any

import boto3
import cfnresponse
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

logger = Logger(service="agentcore-gateway-targets")
tracer = Tracer(service="agentcore-gateway-targets")

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

_control_client = None
_ssm_client = None


def get_control_client():
    """Get or create bedrock-agentcore-control client."""
    global _control_client
    if _control_client is None:
        _control_client = boto3.client("bedrock-agentcore-control", region_name=AWS_REGION)
    return _control_client


def get_ssm_client():
    """Get or create SSM client."""
    global _ssm_client
    if _ssm_client is None:
        _ssm_client = boto3.client("ssm", region_name=AWS_REGION)
    return _ssm_client


class TargetProvisioningError(Exception):
    pass


def _get_gateway_id(ssm_prefix: str) -> str:
    resp = get_ssm_client().get_parameter(Name=f"{ssm_prefix}/gateway_id")
    return resp["Parameter"]["Value"]


def _list_targets(gateway_id: str) -> list[dict[str, Any]]:
    paginator = get_control_client().get_paginator("list_gateway_targets")
    results: list[dict[str, Any]] = []
    for page in paginator.paginate(gatewayIdentifier=gateway_id):
        if "items" in page:
            results.extend(page.get("items", []))
        if "targets" in page:  # backwards compatibility if API changes
            results.extend(page.get("targets", []))
    return results


def _get_target_details(gateway_id: str, target_id: str) -> dict[str, Any]:
    return get_control_client().get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)


def _find_target_by_name(targets: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for t in targets:
        if t.get("name") == name:
            return t
    return None


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _canonicalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        canonical_items = [_canonicalize(item) for item in value]
        return sorted(canonical_items, key=lambda item: json.dumps(item, sort_keys=True))
    return value


def _structures_equal(first: Any, second: Any) -> bool:
    return json.dumps(_canonicalize(first), sort_keys=True) == json.dumps(
        _canonicalize(second), sort_keys=True
    )


def _build_tool_schema(tool: dict[str, Any]) -> dict[str, Any]:
    """
    Build the tool schema for a gateway target.

    The 'schema' field in the tool dict must be a dict or list representing the tool's schema.
    The function will wrap single schema dicts in an 'inlinePayload' list unless already structured.

    Expected formats:
        1. Single schema dict (will be wrapped):
           tool = {"name": "my_tool", "lambdaArn": "...", "schema": {"type": "object", ...}}

        2. Full schema structure (used as-is):
           tool = {"name": "my_tool", "lambdaArn": "...", "schema": {"inlinePayload": [...]}}

        3. List of schemas (will be wrapped):
           tool = {"name": "my_tool", "lambdaArn": "...", "schema": [{...}, {...}]}

    Args:
        tool: Tool configuration dict with 'schema' field

    Returns:
        Schema dict with 'inlinePayload' or 's3' structure

    Raises:
        TargetProvisioningError: If schema is missing or invalid
    """
    schema = tool.get("schema")
    if not schema:
        raise TargetProvisioningError(f"Tool '{tool.get('name')}' is missing schema definition")

    # Allow users to provide full schema structure (including inlinePayload or s3) or a single tool
    if isinstance(schema, dict):
        if "inlinePayload" in schema or "s3" in schema:
            return copy.deepcopy(schema)
        return {"inlinePayload": [copy.deepcopy(schema)]}

    if isinstance(schema, list):
        return {"inlinePayload": copy.deepcopy(schema)}

    raise TargetProvisioningError(
        f"Unsupported schema format for tool '{tool.get('name')}'. Expected dict or list."
    )


def _build_target_configuration(tool: dict[str, Any]) -> dict[str, Any]:
    lambda_arn = tool.get("lambdaArn")
    if not lambda_arn:
        raise TargetProvisioningError(f"Tool '{tool.get('name')}' is missing lambdaArn")

    return {
        "mcp": {
            "lambda": {
                "lambdaArn": lambda_arn,
                "toolSchema": _build_tool_schema(tool),
            }
        }
    }


def _build_credential_provider_configurations(
    tool: dict[str, Any],
) -> list[dict[str, Any]]:
    configs = tool.get("credentialProviderConfigurations")
    if configs:
        return copy.deepcopy(configs)
    return [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]


@tracer.capture_method
def _ensure_target(gateway_id: str, tool: dict[str, Any]) -> tuple[str, str]:
    """Create or update a gateway target for given tool.

    Returns: (action, targetId) where action in {"created", "updated", "unchanged"}
    """
    name = tool["name"]
    target_configuration = _build_target_configuration(tool)
    credential_configs = _build_credential_provider_configurations(tool)
    desired_lambda_arn = target_configuration["mcp"]["lambda"]["lambdaArn"]
    desired_schema = target_configuration["mcp"]["lambda"].get("toolSchema", {})

    existing_targets = _list_targets(gateway_id)
    existing = _find_target_by_name(existing_targets, name)

    if existing is None:
        # Create
        logger.info(f"Creating gateway target: {name}")
        response = get_control_client().create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=name,
            targetConfiguration=target_configuration,
            credentialProviderConfigurations=credential_configs,
            clientToken=str(uuid.uuid4()),
            description=tool.get("description") or f"Global tool {name}",
        )
        target_id = response.get("targetId") or response.get("gatewayTargetId") or name
        return "created", target_id

    # Compare and update if needed
    target_id = existing.get("targetId") or existing.get("gatewayTargetId") or name
    existing_details = _get_target_details(gateway_id, target_id)
    lambda_config = existing_details.get("targetConfiguration", {}).get("mcp", {}).get("lambda", {})
    existing_lambda = lambda_config.get("lambdaArn")
    existing_schema = lambda_config.get("toolSchema") or {}
    existing_credentials = existing_details.get("credentialProviderConfigurations", [])

    needs_update = False
    if existing_lambda != desired_lambda_arn:
        needs_update = True

    if not _structures_equal(existing_schema, desired_schema):
        needs_update = True

    if not _structures_equal(existing_credentials, credential_configs):
        needs_update = True

    if needs_update:
        logger.info(f"Updating gateway target: {name}")
        response = get_control_client().update_gateway_target(
            gatewayIdentifier=gateway_id,
            targetId=target_id,
            name=name,
            targetConfiguration=target_configuration,
            credentialProviderConfigurations=credential_configs,
            description=tool.get("description") or f"Global tool {name}",
        )
        target_id = (
            response.get("targetId")
            or response.get("gatewayTargetId")
            or existing.get("targetId")
            or name
        )
        return "updated", target_id

    return "unchanged", target_id


@tracer.capture_method
def _delete_target_by_name(gateway_id: str, name: str) -> bool:
    targets = _list_targets(gateway_id)
    existing = _find_target_by_name(targets, name)
    if not existing:
        logger.warning(f"Target not found for deletion: {name}")
        return False

    target_id = existing.get("targetId") or existing.get("gatewayTargetId") or name
    logger.info(f"Deleting gateway target: {name} ({target_id})")
    get_control_client().delete_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
    return True


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], context: LambdaContext) -> None:
    logger.info("Received event", extra={"event": event})

    request_type = event.get("RequestType", "Create")
    props = event.get("ResourceProperties", {})

    try:
        environment = props["Environment"]
        tools: list[dict[str, Any]] = props.get("Tools", [])
        ssm_prefix = props.get("SSMPrefix", f"/agentcore/{environment}/gateway")

        gateway_id = props.get("GatewayId") or _get_gateway_id(ssm_prefix)

        if request_type == "Create" or request_type == "Update":
            created = updated = unchanged = 0
            for tool in tools:
                action, _ = _ensure_target(gateway_id, tool)
                if action == "created":
                    created += 1
                elif action == "updated":
                    updated += 1
                else:
                    unchanged += 1

            result = {
                "Created": created,
                "Updated": updated,
                "Unchanged": unchanged,
                "GatewayId": gateway_id,
            }
            cfnresponse.send(event, context, cfnresponse.SUCCESS, result, gateway_id)
            return

        if request_type == "Delete":
            deleted = 0
            for tool in tools:
                try:
                    if _delete_target_by_name(gateway_id, tool["name"]):
                        deleted += 1
                except ClientError as e:
                    if e.response["Error"].get("Code") == "ResourceNotFoundException":
                        logger.warning(f"Target not found during delete: {tool['name']}")
                    else:
                        raise

            result = {"Deleted": deleted, "GatewayId": gateway_id}
            cfnresponse.send(event, context, cfnresponse.SUCCESS, result, gateway_id)
            return

        raise TargetProvisioningError(f"Unknown request type: {request_type}")

    except Exception as e:
        logger.error(f"Handler failed: {str(e)}", exc_info=True)
        cfnresponse.send(
            event,
            context,
            cfnresponse.FAILED,
            {"Error": str(e)},
            props.get("GatewayId", "failed-to-register-targets"),
        )
        return
