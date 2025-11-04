"""
Bedrock AgentCore Memory Custom Resource Handler

Manages lifecycle of Bedrock AgentCore Memory service via Terraform custom resource.
Provisions short-term, long-term, and semantic memory strategies.

Author: AgentCore Template
Created: 2025-10-22
"""

import os
from typing import Any

import boto3
import cfnresponse
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

# Initialize Powertools
logger = Logger(service="agentcore-memory-provisioner")
tracer = Tracer(service="agentcore-memory-provisioner")

# Get AWS region from environment
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Lazy-loaded boto3 clients (created on first use, not at import time)
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


class MemoryProvisioningError(Exception):
    """Custom exception for memory provisioning failures"""

    pass


@tracer.capture_method
def create_memory(properties: dict[str, Any]) -> dict[str, str]:
    """
    Create a new Bedrock AgentCore Memory instance with configured strategies.

    Args:
        properties: Resource properties from Terraform

    Returns:
        Dict containing memory_id, memory_arn, enabled_strategies

    Raises:
        MemoryProvisioningError: If provisioning fails
    """
    memory_name = properties["MemoryName"]
    environment = properties["Environment"]
    agent_namespace = properties["AgentNamespace"]
    ssm_prefix = properties["SSMPrefix"]

    # Memory strategy configuration
    event_expiry_days = int(properties.get("EventExpiryDays", 90))

    logger.info(f"Creating Bedrock Memory: {memory_name} with expiry: {event_expiry_days} days")

    try:
        # Build memory configuration - matching working CloudFormation structure
        import uuid

        memory_config = {
            "name": memory_name,
            "description": f"AgentCore Memory for {environment} environment",
            "eventExpiryDuration": event_expiry_days,  # Days, not seconds!
            "memoryStrategies": [
                {
                    "userPreferenceMemoryStrategy": {
                        "name": f"{memory_name}Preferences",
                        "description": "Captures user preferences and behavior",
                        "namespaces": [f"{agent_namespace}/{environment}/{{actorId}}/preferences"],
                    }
                },
                {
                    "semanticMemoryStrategy": {
                        "name": f"{memory_name}Semantic",
                        "description": "Stores facts from conversations",
                        "namespaces": [f"{agent_namespace}/{environment}/{{actorId}}/semantic"],
                    }
                },
            ],
            "clientToken": str(uuid.uuid4()),
        }

        # Try to create memory, handle if it already exists
        memory_id = None
        try:
            response = get_control_client().create_memory(**memory_config)
            memory_id = response["memoryId"]
            logger.info(f"Memory created with ID: {memory_id}")

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConflictException":
                # Memory already exists, list and find it by name
                logger.info(f"Memory {memory_name} already exists, retrieving...")
                paginator = get_control_client().get_paginator("list_memories")
                for page in paginator.paginate():
                    for mem in page.get("memories", []):
                        if mem.get("name") == memory_name:
                            memory_id = mem.get("memoryId")
                            logger.info(f"Found existing memory with ID: {memory_id}")
                            break
                    if memory_id:
                        break

                if not memory_id:
                    raise MemoryProvisioningError(
                        f"Memory {memory_name} exists but couldn't be found in list"
                    ) from e
            else:
                raise

        # Get full memory details
        memory_details = get_control_client().get_memory(memoryId=memory_id)
        # Get full memory details
        memory_details = get_control_client().get_memory(memoryId=memory_id)
        memory_arn = memory_details.get("memoryArn")

        # Store outputs in SSM Parameter Store
        ssm_params = {
            f"{ssm_prefix}/memory_id": memory_id,
            f"{ssm_prefix}/memory_arn": memory_arn,
            f"{ssm_prefix}/enabled_strategies": "userPreferenceMemoryStrategy,semanticMemoryStrategy",
        }

        for param_name, param_value in ssm_params.items():
            try:
                # Check if parameter exists
                get_ssm_client().get_parameter(Name=param_name)
                # Parameter exists, update without tags
                get_ssm_client().put_parameter(
                    Name=param_name, Value=param_value, Type="String", Overwrite=True
                )
                logger.info(f"Updated SSM parameter: {param_name}")
            except ClientError as e:
                if e.response["Error"]["Code"] == "ParameterNotFound":
                    # Parameter doesn't exist, create with tags
                    get_ssm_client().put_parameter(
                        Name=param_name,
                        Value=param_value,
                        Type="String",
                        Tags=[
                            {"Key": "Environment", "Value": environment},
                            {"Key": "AgentNamespace", "Value": agent_namespace},
                            {"Key": "ManagedBy", "Value": "terraform"},
                            {"Key": "Component", "Value": "memory"},
                        ],
                    )
                logger.info(f"Created SSM parameter: {param_name}")

        logger.info(f"Successfully created memory: {memory_id}")

        return {
            "MemoryId": memory_id,
            "MemoryArn": memory_arn,
            "EnabledStrategies": "userPreferenceMemoryStrategy,semanticMemoryStrategy",
        }

    except Exception as e:
        logger.error(f"Failed to create memory: {str(e)}", exc_info=True)
        raise MemoryProvisioningError(f"Create failed: {str(e)}") from e


@tracer.capture_method
def update_memory(memory_id: str, properties: dict[str, Any]) -> dict[str, str]:
    """
    Update an existing Bedrock AgentCore Memory instance.

    Args:
        memory_id: Physical resource ID (memory ID)
        properties: Updated resource properties

    Returns:
        Dict containing updated memory information

    Raises:
        MemoryProvisioningError: If update fails
    """
    logger.info(f"Updating Bedrock Memory: {memory_id}")

    try:
        # Check if memory exists
        try:
            memory_details = get_control_client().get_memory(memoryId=memory_id)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.warning(f"Memory {memory_id} not found, creating new one")
                return create_memory(properties)
            else:
                raise

        # Update memory configuration (if API supports it)
        # Note: Bedrock Memory update capabilities may be limited
        # For now, we'll update SSM parameters and log the update

        memory_arn = memory_details["memoryArn"]
        enabled_strategies = properties.get(
            "EnabledStrategies", ["SHORT_TERM", "LONG_TERM", "SEMANTIC"]
        )

        # Update SSM parameters
        ssm_prefix = properties["SSMPrefix"]
        short_term_ttl = int(properties.get("ShortTermTTLSeconds", 3600))
        long_term_retention = properties.get("LongTermRetention", "INDEFINITE")

        ssm_params = {
            f"{ssm_prefix}/memory_id": memory_id,
            f"{ssm_prefix}/memory_arn": memory_arn,
            f"{ssm_prefix}/enabled_strategies": ",".join(enabled_strategies),
            f"{ssm_prefix}/short_term_ttl": str(short_term_ttl),
            f"{ssm_prefix}/long_term_retention": long_term_retention,
        }

        if "SEMANTIC" in enabled_strategies:
            embedding_model_arn = properties.get("EmbeddingModelArn", "")
            if not embedding_model_arn:
                embedding_model_arn = f"arn:aws:bedrock:{os.environ.get('AWS_REGION')}::foundation-model/amazon.titan-embed-text-v1"
            max_tokens = int(properties.get("MaxTokens", 1536))
            ssm_params[f"{ssm_prefix}/embedding_model_arn"] = embedding_model_arn
            ssm_params[f"{ssm_prefix}/max_tokens"] = str(max_tokens)

        for param_name, param_value in ssm_params.items():
            get_ssm_client().put_parameter(
                Name=param_name, Value=param_value, Type="String", Overwrite=True
            )

        logger.info(f"Successfully updated memory: {memory_id}")

        return {
            "MemoryId": memory_id,
            "MemoryArn": memory_arn,
            "EnabledStrategies": ",".join(enabled_strategies),
        }

    except Exception as e:
        logger.error(f"Failed to update memory: {str(e)}", exc_info=True)
        raise MemoryProvisioningError(f"Update failed: {str(e)}") from e


@tracer.capture_method
def delete_memory(memory_id: str, properties: dict[str, Any]) -> None:
    """
    Delete a Bedrock AgentCore Memory instance and clean up SSM parameters.

    Args:
        memory_id: Physical resource ID (memory ID)
        properties: Resource properties

    Raises:
        MemoryProvisioningError: If deletion fails
    """
    logger.info(f"Deleting Bedrock Memory: {memory_id}")

    try:
        # Delete memory
        try:
            get_control_client().delete_memory(memoryId=memory_id)
            logger.info(f"Deleted memory: {memory_id}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.warning(f"Memory {memory_id} not found, skipping deletion")
            else:
                raise

        # Clean up SSM parameters
        ssm_prefix = properties["SSMPrefix"]
        ssm_params = [
            f"{ssm_prefix}/memory_id",
            f"{ssm_prefix}/memory_arn",
            f"{ssm_prefix}/enabled_strategies",
            f"{ssm_prefix}/short_term_ttl",
            f"{ssm_prefix}/long_term_retention",
            f"{ssm_prefix}/embedding_model_arn",
            f"{ssm_prefix}/max_tokens",
        ]

        for param_name in ssm_params:
            try:
                get_ssm_client().delete_parameter(Name=param_name)
                logger.info(f"Deleted SSM parameter: {param_name}")
            except ClientError as e:
                if e.response["Error"]["Code"] == "ParameterNotFound":
                    logger.warning(f"SSM parameter {param_name} not found, skipping")
                else:
                    raise

        logger.info("Successfully completed memory deletion")

    except Exception as e:
        logger.error(f"Failed to delete memory: {str(e)}", exc_info=True)
        raise MemoryProvisioningError(f"Delete failed: {str(e)}") from e


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], context: LambdaContext) -> None:
    """
    Lambda handler for Terraform custom resource lifecycle.

    Args:
        event: CloudFormation/Terraform custom resource event
        context: Lambda context
    """
    logger.info("Received event", extra={"event": event})

    request_type = event["RequestType"]  # Create, Update, or Delete
    properties = event["ResourceProperties"]
    physical_resource_id = event.get("PhysicalResourceId")

    try:
        if request_type == "Create":
            result = create_memory(properties)
            physical_resource_id = result["MemoryId"]
            cfnresponse.send(event, context, cfnresponse.SUCCESS, result, physical_resource_id)

        elif request_type == "Update":
            if not physical_resource_id:
                raise MemoryProvisioningError("PhysicalResourceId missing for Update")

            result = update_memory(physical_resource_id, properties)
            cfnresponse.send(event, context, cfnresponse.SUCCESS, result, physical_resource_id)

        elif request_type == "Delete":
            if physical_resource_id:
                delete_memory(physical_resource_id, properties)
            else:
                logger.warning("No PhysicalResourceId for Delete, skipping")

            cfnresponse.send(
                event,
                context,
                cfnresponse.SUCCESS,
                {},
                physical_resource_id or "no-resource-created",
            )

        else:
            raise MemoryProvisioningError(f"Unknown request type: {request_type}")

    except Exception as e:
        logger.error(f"Handler failed: {str(e)}", exc_info=True)
        cfnresponse.send(
            event,
            context,
            cfnresponse.FAILED,
            {"Error": str(e)},
            physical_resource_id or "failed-to-create",
        )
