#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.korean_address_app_stack import KoreanAddressAppStack

app = cdk.App()

# Get environment from context or default to 'dev'
environment = app.node.try_get_context("environment") or "dev"

KoreanAddressAppStack(
    app, 
    f"KoreanAddressApp-{environment}",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region")
    ),
    environment=environment
)

app.synth()