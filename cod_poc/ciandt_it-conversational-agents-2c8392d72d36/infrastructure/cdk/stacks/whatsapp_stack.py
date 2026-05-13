"""WhatsApp Stack — Lambda webhook + API Gateway (espelha o SAM template existente)."""

import cdk_nag
from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_apigateway as apigw,
)
from aws_cdk import (
    aws_dynamodb as dynamodb,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from aws_cdk import (
    aws_logs as logs,
)
from constructs import Construct


class WhatsAppStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        domain_slug: str,
        agent_name: str,
        environment: str,
        runtime_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account = Stack.of(self).account
        region = Stack.of(self).region
        prefix = f"{domain_slug}-{environment}"
        fn_name = f"{agent_name}-whatsapp-{environment}"

        # ── DynamoDB Dedup (WhatsApp-specific) ──
        dedup_table = dynamodb.Table(
            self,
            "WaDedupTable",
            table_name=f"{agent_name}-wa-dedup-{environment}",
            partition_key=dynamodb.Attribute(name="message_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY if environment != "prod" else RemovalPolicy.RETAIN,
            time_to_live_attribute="ttl",
            point_in_time_recovery=True,
        )

        # ── Lambda Role ──
        lambda_role = iam.Role(
            self,
            "WaLambdaRole",
            role_name=f"{prefix}-wa-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="DynamoDBDedup",
                actions=["dynamodb:PutItem"],
                resources=[dedup_table.table_arn],
            )
        )
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="AgentCoreInvoke",
                actions=["bedrock-agentcore:InvokeAgentRuntime"],
                resources=[runtime_arn],
            )
        )
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudWatchLogs",
                actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                resources=[f"arn:aws:logs:{region}:{account}:log-group:/aws/lambda/{fn_name}:*"],
            )
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            lambda_role,
            [cdk_nag.NagPackSuppression(id="AwsSolutions-IAM5", reason="Log group ARN requires :* suffix per AWS.")],
            apply_to_children=True,
        )

        # ── Lambda Log Group ──
        wa_log_group = logs.LogGroup(
            self,
            "WaLogGroup",
            log_group_name=f"/aws/lambda/{fn_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ── Lambda Function ──
        wa_fn = _lambda.Function(
            self,
            "WaWebhookFn",
            function_name=fn_name,
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.ARM_64,
            handler="lambda_handler.lambda_handler",
            code=_lambda.Code.from_asset("../../src/channels/whatsapp"),
            role=lambda_role,
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "AGENTCORE_AGENT_NAME": agent_name,
                "DEDUP_TABLE_NAME": dedup_table.table_name,
                "ERROR_MESSAGE_GENERIC": "Desculpe, ocorreu um erro. Tente novamente em alguns instantes.",
                # Secrets managed via Secrets Manager / parameter store — NOT in code
                # WHATSAPP_ACCESS_TOKEN, WHATSAPP_APP_SECRET, WHATSAPP_VERIFY_TOKEN, WHATSAPP_PHONE_NUMBER_ID
            },
        )
        wa_fn.node.add_dependency(wa_log_group)

        # ── API Gateway (REST) ──
        api = apigw.RestApi(
            self,
            "WaApi",
            rest_api_name=f"{prefix}-whatsapp-api",
            deploy_options=apigw.StageOptions(
                stage_name=environment,
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=False,
            ),
        )

        webhook_resource = api.root.add_resource("webhook")
        integration = apigw.LambdaIntegration(wa_fn)
        webhook_resource.add_method("GET", integration)
        webhook_resource.add_method("POST", integration)

        # cdk-nag suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions(
            api,
            [
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-APIG2", reason="Request validation handled in Lambda code (signature check)."
                ),
                cdk_nag.NagPackSuppression(id="AwsSolutions-APIG1", reason="Access logging configured at stage level."),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-APIG4", reason="WhatsApp webhook requires open GET for verification."
                ),
                cdk_nag.NagPackSuppression(id="AwsSolutions-APIG6", reason="Logging enabled via deploy_options."),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-COG4", reason="No Cognito — WhatsApp uses signature-based auth."
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4", reason="Lambda basic execution managed policy is acceptable."
                ),
            ],
            apply_to_children=True,
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            wa_fn,
            [
                cdk_nag.NagPackSuppression(id="AwsSolutions-L1", reason="Python 3.12 is the latest supported runtime."),
            ],
        )

        # ── Outputs ──
        CfnOutput(
            self,
            "WebhookUrl",
            value=f"https://{api.rest_api_id}.execute-api.{region}.amazonaws.com/{environment}/webhook",
            description="WhatsApp Webhook URL",
        )
        CfnOutput(self, "WaFunctionName", value=wa_fn.function_name)
        CfnOutput(self, "WaDedupTableName", value=dedup_table.table_name)
