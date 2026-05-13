#!/usr/bin/env python3
"""CDK app entry point — AgentCore infrastructure."""

import aws_cdk as cdk
import cdk_nag
from stacks.agentcore_stack import AgentCoreStack
from stacks.network_stack import NetworkStack
from stacks.whatsapp_stack import WhatsAppStack

app = cdk.App()

domain_slug = app.node.try_get_context("domain_slug") or "my-agent"
agent_name = app.node.try_get_context("agent_name") or "my_multi_agent"
environment = app.node.try_get_context("environment") or "dev"
memory_name = app.node.try_get_context("memory_name") or "MyAgentMemory"

env = cdk.Environment(
    account=app.node.try_get_context("aws_account_id") or cdk.Aws.ACCOUNT_ID,
    region=app.node.try_get_context("aws_region") or "us-east-1",
)

network = NetworkStack(
    app,
    f"{domain_slug}-network-{environment}",
    env=env,
    domain_slug=domain_slug,
    environment=environment,
)

agentcore = AgentCoreStack(
    app,
    f"{domain_slug}-agentcore-{environment}",
    env=env,
    domain_slug=domain_slug,
    agent_name=agent_name,
    environment=environment,
    memory_name=memory_name,
)

WhatsAppStack(
    app,
    f"{domain_slug}-whatsapp-{environment}",
    env=env,
    domain_slug=domain_slug,
    agent_name=agent_name,
    environment=environment,
    runtime_arn=agentcore.runtime_arn,
)

# Tags globais
for key, val in {
    "Project": domain_slug,
    "Environment": environment,
    "ManagedBy": "cdk",
    "Owner": "platform-team",
}.items():
    cdk.Tags.of(app).add(key, val)

# cdk-nag AwsSolutions
cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(verbose=True))

app.synth()
