"""Network Stack — VPC, VPC Endpoints (PrivateLink), Security Groups, WAF."""

import cdk_nag
from aws_cdk import (
    CfnOutput,
    Fn,
    Stack,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_wafv2 as wafv2,
)
from constructs import Construct


class NetworkStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        domain_slug: str,
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        prefix = f"{domain_slug}-{environment}"

        # ── VPC ──
        vpc = ec2.Vpc(
            self,
            "Vpc",
            vpc_name=f"{prefix}-vpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=28,
                ),
            ],
        )

        # ── Security Groups ──
        endpoints_sg = ec2.SecurityGroup(
            self,
            "EndpointsSg",
            vpc=vpc,
            security_group_name=f"{prefix}-endpoints-sg",
            description="SG for VPC Interface Endpoints",
            allow_all_outbound=False,
        )

        runtime_sg = ec2.SecurityGroup(
            self,
            "RuntimeSg",
            vpc=vpc,
            security_group_name=f"{prefix}-runtime-sg",
            description="SG for AgentCore Runtime",
            allow_all_outbound=False,
        )

        lambda_sg = ec2.SecurityGroup(
            self,
            "LambdaSg",
            vpc=vpc,
            security_group_name=f"{prefix}-lambda-sg",
            description="SG for Lambda functions",
            allow_all_outbound=False,
        )

        # Lambda → Runtime (8080)
        runtime_sg.add_ingress_rule(
            peer=lambda_sg,
            connection=ec2.Port.tcp(8080),
            description="Lambda to Runtime on 8080",
        )

        # Runtime → Endpoints (443)
        runtime_sg.add_egress_rule(
            peer=endpoints_sg,
            connection=ec2.Port.tcp(443),
            description="Runtime to VPC Endpoints on 443",
        )

        # Lambda → Endpoints (443)
        lambda_sg.add_egress_rule(
            peer=endpoints_sg,
            connection=ec2.Port.tcp(443),
            description="Lambda to VPC Endpoints on 443",
        )

        # Endpoints accept 443 from Runtime + Lambda
        endpoints_sg.add_ingress_rule(
            peer=runtime_sg,
            connection=ec2.Port.tcp(443),
            description="From Runtime SG",
        )
        endpoints_sg.add_ingress_rule(
            peer=lambda_sg,
            connection=ec2.Port.tcp(443),
            description="From Lambda SG",
        )

        # ── Interface VPC Endpoints (PrivateLink) ──
        interface_services = {
            "bedrock-runtime": ec2.InterfaceVpcEndpointAwsService("bedrock-runtime"),
            "bedrock-agent-runtime": ec2.InterfaceVpcEndpointAwsService("bedrock-agent-runtime"),
            "secretsmanager": ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            "logs": ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            "ssm": ec2.InterfaceVpcEndpointAwsService.SSM,
        }

        for svc_name, svc in interface_services.items():
            vpc.add_interface_endpoint(
                f"Ep{svc_name.replace('-', '').title()}",
                service=svc,
                private_dns_enabled=True,
                security_groups=[endpoints_sg],
                subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            )

        # ── Gateway VPC Endpoints ──
        vpc.add_gateway_endpoint(
            "EpDynamodb",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)],
        )
        vpc.add_gateway_endpoint(
            "EpS3",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)],
        )

        # ── WAF WebACL (API Gateway — WhatsApp webhook) ──
        waf_acl = wafv2.CfnWebACL(
            self,
            "WafAcl",
            name=f"{prefix}-waf",
            scope="REGIONAL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name=f"{prefix}-waf",
                sampled_requests_enabled=True,
            ),
            rules=[
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimitPerIP",
                    priority=1,
                    action=wafv2.CfnWebACL.RuleActionProperty(block={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            limit=1000,
                            aggregate_key_type="IP",
                        ),
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name=f"{prefix}-rate-limit",
                        sampled_requests_enabled=True,
                    ),
                ),
                wafv2.CfnWebACL.RuleProperty(
                    name="AWSManagedCommonRules",
                    priority=2,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesCommonRuleSet",
                        ),
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name=f"{prefix}-common-rules",
                        sampled_requests_enabled=True,
                    ),
                ),
            ],
        )

        # cdk-nag suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions(
            vpc,
            [
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-VPC7",
                    reason="VPC Flow Logs omitted in dev/poc — enable for prod.",
                ),
            ],
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            runtime_sg,
            [
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-EC23",
                    reason="No 0.0.0.0/0 ingress — scoped to Lambda SG only.",
                ),
            ],
        )

        # ── Expose for cross-stack references ──
        self.vpc = vpc
        self.runtime_sg = runtime_sg
        self.lambda_sg = lambda_sg
        self.endpoints_sg = endpoints_sg
        self.waf_acl_arn = waf_acl.attr_arn

        # ── Outputs ──
        CfnOutput(self, "VpcId", value=vpc.vpc_id, description="VPC ID")
        CfnOutput(
            self,
            "PrivateSubnetIds",
            value=Fn.join(",", vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids),
            description="Private Subnet IDs",
        )
        CfnOutput(self, "RuntimeSgId", value=runtime_sg.security_group_id, description="Runtime Security Group ID")
        CfnOutput(self, "LambdaSgId", value=lambda_sg.security_group_id, description="Lambda Security Group ID")
        CfnOutput(self, "WafAclArn", value=waf_acl.attr_arn, description="WAF WebACL ARN")
