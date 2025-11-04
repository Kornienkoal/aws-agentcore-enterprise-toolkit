"""
Bedrock AgentCore Gateway Custom Resource Handler

Manages lifecycle of Bedrock AgentCore Gateway resources via Terraform custom resource.
Handles Create, Update, and Delete operations with idempotency.

Author: AgentCore Template
Created: 2025-10-22
"""

import os
import time
import uuid
from typing import Any

import boto3
import cfnresponse
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

# Initialize Powertools
logger = Logger(service="agentcore-gateway-provisioner")
tracer = Tracer(service="agentcore-gateway-provisioner")

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


class GatewayProvisioningError(Exception):
    """Custom exception for gateway provisioning failures"""

    pass


@tracer.capture_method
def create_gateway(properties: dict[str, Any]) -> dict[str, str]:
    """
    Create a new Bedrock AgentCore Gateway.

    Args:
        properties: Resource properties from Terraform

    Returns:
        Dict containing gateway_id, gateway_arn, invoke_url

    Raises:
        GatewayProvisioningError: If provisioning fails
    """
    gateway_name = properties["GatewayName"]
    gateway_role_arn = properties["GatewayRoleArn"]
    environment = properties["Environment"]
    agent_namespace = properties["AgentNamespace"]
    ssm_prefix = properties["SSMPrefix"]

    logger.info(f"Creating Bedrock Gateway: {gateway_name}")

    try:
        # Get Cognito configuration from SSM for JWT authorization
        # Identity SSM parameters are stored under /agentcore/{env}/identity/* by Terraform
        cognito_pool_id = get_ssm_client().get_parameter(
            Name=f"/agentcore/{environment}/identity/pool_id"
        )["Parameter"]["Value"]

        cognito_client_id = get_ssm_client().get_parameter(
            Name=f"/agentcore/{environment}/identity/machine_client_id"
        )["Parameter"]["Value"]

        # Construct the OIDC discovery URL for Cognito
        region = os.environ.get("AWS_REGION", "us-east-1")
        discovery_url = f"https://cognito-idp.{region}.amazonaws.com/{cognito_pool_id}/.well-known/openid-configuration"

        logger.info(
            f"Using JWT authorizer with discovery URL: {discovery_url}, client: {cognito_client_id}"
        )

        # Try to create gateway, handle if it already exists
        gateway_id = None
        try:
            response = get_control_client().create_gateway(
                name=gateway_name,
                roleArn=gateway_role_arn,
                protocolType="MCP",
                authorizerType="CUSTOM_JWT",
                authorizerConfiguration={
                    "customJWTAuthorizer": {
                        "discoveryUrl": discovery_url,
                        "allowedClients": [cognito_client_id],
                    }
                },
                description=f"AgentCore Gateway for {environment} environment",
                clientToken=str(uuid.uuid4()),
            )
            gateway_id = response["gatewayId"]
            logger.info(f"Gateway created with ID: {gateway_id}")

        except get_control_client().exceptions.ConflictException as e:
            # Gateway already exists, list and find it by name
            logger.info(f"Gateway {gateway_name} already exists, retrieving...")
            paginator = get_control_client().get_paginator("list_gateways")
            for page in paginator.paginate():
                for gw in page.get("gateways", []):
                    if gw.get("name") == gateway_name:
                        gateway_id = gw.get("gatewayId")
                        logger.info(f"Found existing gateway with ID: {gateway_id}")
                        break
                if gateway_id:
                    break

            if not gateway_id:
                raise GatewayProvisioningError(
                    f"Gateway {gateway_name} exists but couldn't be found in list"
                ) from e

        # Wait for gateway to become active
        max_attempts = 30
        poll_interval = 10
        for attempt in range(max_attempts):
            gateway_details = get_control_client().get_gateway(gatewayIdentifier=gateway_id)
            status = gateway_details.get("status")
            logger.info(f"Gateway status check {attempt + 1}/{max_attempts}: {status}")

            if status in ["ACTIVE", "READY"]:
                logger.info(f"Gateway is {status} and ready")
                break
            if status == "FAILED":
                failure_reasons = gateway_details.get("statusReasons", ["Unknown"])
                raise GatewayProvisioningError(f"Gateway creation failed: {failure_reasons}")
            time.sleep(poll_interval)
        else:
            raise GatewayProvisioningError(
                f"Gateway did not become ACTIVE within {max_attempts * poll_interval}s"
            )

        gateway_arn = gateway_details.get("gatewayArn")
        invoke_url = gateway_details.get(
            "gatewayUrl",
            f"https://{gateway_id}.bedrock-gateway.{os.environ.get('AWS_REGION')}.amazonaws.com",
        )

        # Store outputs in SSM Parameter Store
        ssm_params = {
            f"{ssm_prefix}/gateway_id": gateway_id,
            f"{ssm_prefix}/gateway_arn": gateway_arn,
            f"{ssm_prefix}/invoke_url": invoke_url,
            f"{ssm_prefix}/role_arn": gateway_role_arn,
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
                            {"Key": "Component", "Value": "gateway"},
                        ],
                    )
                    logger.info(f"Created SSM parameter: {param_name}")
                else:
                    raise

        logger.info(f"Successfully created gateway: {gateway_id}")

        return {
            "GatewayId": gateway_id,
            "GatewayArn": gateway_arn,
            "InvokeUrl": invoke_url,
            "RoleArn": gateway_role_arn,
        }

    except Exception as e:
        logger.error(f"Failed to create gateway: {str(e)}", exc_info=True)
        raise GatewayProvisioningError(f"Create failed: {str(e)}") from e


@tracer.capture_method
def update_gateway(gateway_id: str, properties: dict[str, Any]) -> dict[str, str]:
    """
    Update an existing Bedrock AgentCore Gateway.

    Args:
        gateway_id: Physical resource ID (gateway ID)
        properties: Updated resource properties

    Returns:
        Dict containing updated gateway information

    Raises:
        GatewayProvisioningError: If update fails
    """
    gateway_role_arn = properties["GatewayRoleArn"]
    environment = properties["Environment"]

    logger.info(f"Updating Bedrock Gateway: {gateway_id}")

    try:
        # Check if gateway exists
        try:
            gateway_details = get_control_client().get_gateway(gatewayIdentifier=gateway_id)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.warning(f"Gateway {gateway_id} not found, creating new one")
                return create_gateway(properties)
            else:
                raise

        # Update gateway configuration
        response = get_control_client().update_gateway(
            gatewayIdentifier=gateway_id,
            roleArn=gateway_role_arn,
            description=f"AgentCore Gateway for {environment} environment (updated)",
        )

        gateway_arn = response["gatewayArn"]
        invoke_url = gateway_details.get(
            "gatewayInvokeUrl",
            f"https://{gateway_id}.bedrock-gateway.{os.environ.get('AWS_REGION')}.amazonaws.com",
        )

        # Update SSM parameters
        ssm_prefix = properties["SSMPrefix"]
        ssm_params = {
            f"{ssm_prefix}/gateway_id": gateway_id,
            f"{ssm_prefix}/gateway_arn": gateway_arn,
            f"{ssm_prefix}/invoke_url": invoke_url,
            f"{ssm_prefix}/role_arn": gateway_role_arn,
        }

        for param_name, param_value in ssm_params.items():
            get_ssm_client().put_parameter(
                Name=param_name, Value=param_value, Type="String", Overwrite=True
            )

        logger.info(f"Successfully updated gateway: {gateway_id}")

        return {
            "GatewayId": gateway_id,
            "GatewayArn": gateway_arn,
            "InvokeUrl": invoke_url,
            "RoleArn": gateway_role_arn,
        }

    except Exception as e:
        logger.error(f"Failed to update gateway: {str(e)}", exc_info=True)
        raise GatewayProvisioningError(f"Update failed: {str(e)}") from e


@tracer.capture_method
def delete_gateway(gateway_id: str, properties: dict[str, Any]) -> None:
    """
    Delete a Bedrock AgentCore Gateway and clean up SSM parameters.

    Args:
        gateway_id: Physical resource ID (gateway ID)
        properties: Resource properties

    Raises:
        GatewayProvisioningError: If deletion fails
    """
    logger.info(f"Deleting Bedrock Gateway: {gateway_id}")

    try:
        # Delete gateway
        try:
            get_control_client().delete_gateway(gatewayId=gateway_id)
            logger.info(f"Deleted gateway: {gateway_id}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.warning(f"Gateway {gateway_id} not found, skipping deletion")
            else:
                raise

        # Clean up SSM parameters
        ssm_prefix = properties["SSMPrefix"]
        ssm_params = [
            f"{ssm_prefix}/gateway_id",
            f"{ssm_prefix}/gateway_arn",
            f"{ssm_prefix}/invoke_url",
            f"{ssm_prefix}/role_arn",
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

        logger.info("Successfully completed gateway deletion")

    except Exception as e:
        logger.error(f"Failed to delete gateway: {str(e)}", exc_info=True)
        raise GatewayProvisioningError(f"Delete failed: {str(e)}") from e


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
            result = create_gateway(properties)
            physical_resource_id = result["GatewayId"]
            cfnresponse.send(event, context, cfnresponse.SUCCESS, result, physical_resource_id)

        elif request_type == "Update":
            if not physical_resource_id:
                raise GatewayProvisioningError("PhysicalResourceId missing for Update")

            result = update_gateway(physical_resource_id, properties)
            cfnresponse.send(event, context, cfnresponse.SUCCESS, result, physical_resource_id)

        elif request_type == "Delete":
            if physical_resource_id:
                delete_gateway(physical_resource_id, properties)
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
            raise GatewayProvisioningError(f"Unknown request type: {request_type}")

    except Exception as e:
        logger.error(f"Handler failed: {str(e)}", exc_info=True)
        cfnresponse.send(
            event,
            context,
            cfnresponse.FAILED,
            {"Error": str(e)},
            physical_resource_id or "failed-to-create",
        )
