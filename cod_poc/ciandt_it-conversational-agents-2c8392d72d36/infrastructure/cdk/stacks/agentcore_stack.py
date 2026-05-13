"""AgentCore Stack — Runtime, RuntimeEndpoint, Memory, Gateway, GatewayTarget, ECR, IAM, DynamoDB."""

import cdk_nag
from aws_cdk import (
    CfnOutput,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_bedrockagentcore as agentcore,
)
from aws_cdk import (
    aws_dynamodb as dynamodb,
)
from aws_cdk import (
    aws_ecr as ecr,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_logs as logs,
)
from constructs import Construct


class AgentCoreStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        domain_slug: str,
        agent_name: str,
        environment: str,
        memory_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account = Stack.of(self).account
        region = Stack.of(self).region
        prefix = f"{domain_slug}-{environment}"

        # ── ECR Repository ──
        ecr_repo = ecr.Repository(
            self,
            "EcrRepo",
            repository_name=f"{prefix}-runtime",
            removal_policy=RemovalPolicy.RETAIN if environment == "prod" else RemovalPolicy.DESTROY,
            empty_on_delete=environment != "prod",
            image_scan_on_push=True,
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=10, description="Keep last 10 images")],
        )

        # ── CloudWatch Log Group ──
        log_group = logs.LogGroup(
            self,
            "RuntimeLogGroup",
            log_group_name=f"/agentcore/{prefix}/runtime",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ── IAM Role: AgentCore Runtime ──
        runtime_role = iam.Role(
            self,
            "RuntimeRole",
            role_name=f"{prefix}-runtime-role",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
        )

        runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRPull",
                actions=[
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:BatchCheckLayerAvailability",
                ],
                resources=[ecr_repo.repository_arn],
            )
        )
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRAuth",
                actions=["ecr:GetAuthorizationToken"],
                resources=[f"arn:aws:ecr:{region}:{account}:*"],
            )
        )
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockInvoke",
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[f"arn:aws:bedrock:{region}::foundation-model/*"],
            )
        )
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockKB",
                actions=["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
                resources=[f"arn:aws:bedrock:{region}:{account}:knowledge-base/*"],
            )
        )
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="AgentCoreMemoryAccess",
                actions=[
                    "bedrock-agentcore:InvokeMemory",
                    "bedrock-agentcore:CreateMemoryEvent",
                    "bedrock-agentcore:GetMemory",
                ],
                resources=[f"arn:aws:bedrock-agentcore:{region}:{account}:memory/*"],
            )
        )
        runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudWatchLogs",
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[log_group.log_group_arn],
            )
        )

        # cdk-nag suppressions para o Role
        cdk_nag.NagSuppressions.add_resource_suppressions(
            runtime_role,
            [
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Wildcard scoped to account/region for foundation-model/*, knowledge-base/*, memory/*. ECR auth requires ecr:* ARN pattern.",
                ),
            ],
            apply_to_children=True,
        )

        # ── IAM Role: Memory Execution ──
        memory_role = iam.Role(
            self,
            "MemoryRole",
            role_name=f"{prefix}-memory-role",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
        )
        memory_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockEmbeddings",
                actions=["bedrock:InvokeModel"],
                resources=[f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2*"],
            )
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            memory_role,
            [cdk_nag.NagPackSuppression(id="AwsSolutions-IAM5", reason="Wildcard on titan-embed version suffix only.")],
            apply_to_children=True,
        )

        # ── AgentCore Runtime (L1 CfnResource) ──
        runtime = agentcore.CfnRuntime(
            self,
            "Runtime",
            agent_runtime_name=agent_name,
            agent_runtime_artifact=agentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                container_configuration=agentcore.CfnRuntime.ContainerConfigurationProperty(
                    container_uri=f"{account}.dkr.ecr.{region}.amazonaws.com/{prefix}-runtime:latest",
                ),
            ),
            role_arn=runtime_role.role_arn,
            description=f"AgentCore Runtime for {domain_slug} ({environment})",
        )

        # ── RuntimeEndpoint ──
        endpoint = agentcore.CfnRuntimeEndpoint(
            self,
            "RuntimeEndpoint",
            agent_runtime_id=runtime.attr_agent_runtime_id,
            name=f"{prefix}-endpoint",
            description=f"Endpoint for {agent_name}",
        )
        endpoint.add_dependency(runtime)

        # ── AgentCore Memory ──
        memory = agentcore.CfnMemory(
            self,
            "Memory",
            memory_name=memory_name,
            event_expiry_duration=90,
            description=f"Memory for {domain_slug} agents",
            memory_execution_role_arn=memory_role.role_arn,
            memory_strategies=[
                agentcore.CfnMemory.MemoryStrategyProperty(
                    semantic_memory_strategy=agentcore.CfnMemory.SemanticMemoryStrategyProperty(
                        model_id=f"arn:aws:bedrock:{region}::foundation-model/anthropic.claude-sonnet-4-6",
                        name=f"{memory_name}-semantic",
                    ),
                ),
            ],
        )

        # ── IAM Role: Gateway ──
        gateway_role = iam.Role(
            self,
            "GatewayRole",
            role_name=f"{prefix}-gateway-role",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
        )
        gateway_role.add_to_policy(
            iam.PolicyStatement(
                sid="GatewayLambdaInvoke",
                actions=["lambda:InvokeFunction"],
                resources=[f"arn:aws:lambda:{region}:{account}:function:{prefix}-*"],
            )
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            gateway_role,
            [
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5", reason="Wildcard scoped to prefix-* functions in this account/region."
                )
            ],
            apply_to_children=True,
        )

        # ── AgentCore Gateway ──
        gateway = agentcore.CfnGateway(
            self,
            "Gateway",
            name=f"{prefix}-gateway",
            protocol_type="MCP",
            authorizer_type="AWS_IAM",
            gateway_role_arn=gateway_role.role_arn,
            description=f"MCP Gateway for {domain_slug}",
        )

        # ── AgentCore Gateway Target ──
        gateway_target = agentcore.CfnGatewayTarget(
            self,
            "GatewayTarget",
            gateway_identifier=gateway.attr_gateway_id,
            name=f"{prefix}-tools",
            description=f"Tool target for {domain_slug} gateway",
            target_configuration=agentcore.CfnGatewayTarget.TargetConfigurationProperty(
                lambda_target_configuration=agentcore.CfnGatewayTarget.LambdaTargetConfigurationProperty(
                    lambda_arn=f"arn:aws:lambda:{region}:{account}:function:{prefix}-tools",
                ),
            ),
        )
        gateway_target.add_dependency(gateway)

        # ── DynamoDB Dedup Table ──
        dedup_table = dynamodb.Table(
            self,
            "DedupTable",
            table_name=f"{agent_name}-dedup-{environment}",
            partition_key=dynamodb.Attribute(name="message_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY if environment != "prod" else RemovalPolicy.RETAIN,
            time_to_live_attribute="ttl",
            point_in_time_recovery=True,
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            dedup_table,
            [cdk_nag.NagPackSuppression(id="AwsSolutions-DDB3", reason="PITR enabled.")],
        )

        # ── Outputs ──
        self.runtime_arn = runtime.attr_agent_runtime_arn
        CfnOutput(self, "RuntimeArn", value=runtime.attr_agent_runtime_arn, description="AgentCore Runtime ARN")
        CfnOutput(self, "RuntimeId", value=runtime.attr_agent_runtime_id, description="AgentCore Runtime ID")
        CfnOutput(self, "EndpointId", value=endpoint.ref, description="Runtime Endpoint ID")
        CfnOutput(self, "MemoryId", value=memory.attr_memory_id, description="AgentCore Memory ID")
        CfnOutput(self, "GatewayArn", value=gateway.attr_gateway_arn, description="AgentCore Gateway ARN")
        CfnOutput(self, "EcrUri", value=ecr_repo.repository_uri, description="ECR Repository URI")
        CfnOutput(self, "DedupTableName", value=dedup_table.table_name, description="DynamoDB Dedup Table")
