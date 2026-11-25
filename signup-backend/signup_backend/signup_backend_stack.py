from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    CfnOutput,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_ssm as ssm,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
)

from constructs import Construct

class SignupBackendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        site_bucket = s3.Bucket(
            self, "SiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        distribution = cloudfront.Distribution(
            self, "SiteDistribution",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
        )

        site_url = "https://" + distribution.distribution_domain_name

        s3deploy.BucketDeployment(
            self, "DeploySite",
            sources=[s3deploy.Source.asset("../signup-frontend/dist")],
            destination_bucket=site_bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )

        table = dynamodb.Table(
            self, "RegistrationsTable",
            partition_key=dynamodb.Attribute(
                name="registration_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        stripe_key = ssm.StringParameter.from_secure_string_parameter_attributes(
            self, "StripeKey", parameter_name="/signup/stripe-secret-key",
        )
        webhook_secret = ssm.StringParameter.from_secure_string_parameter_attributes(
            self, "WebhookSecret", parameter_name="/signup/stripe-webhook-secret",
        )

        register_fn = _lambda.Function(
            self, "RegisterFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(10),
            environment={
                "TABLE_NAME": table.table_name,
                "STRIPE_KEY_PARAM": "/signup/stripe-secret-key",
                "SITE_URL": site_url,
                },
        )
        table.grant_write_data(register_fn)
        stripe_key.grant_read(register_fn)

        webhook_fn = _lambda.Function(
            self, "WebhookFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="webhook_function.lambda_handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "TABLE_NAME": table.table_name,
                "WEBHOOK_SECRET_PARAM": "/signup/stripe-webhook-secret",
            },
        )
        table.grant_write_data(webhook_fn)
        webhook_secret.grant_read(webhook_fn)

        api = apigwv2.HttpApi(
            self, "SignupApi",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["http://localhost:5173", site_url],
                allow_methods=[apigwv2.CorsHttpMethod.POST],
                allow_headers=["content-type"],
            ),
        )

        api.add_routes(
            path="/register",
            methods=[apigwv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration("RegisterIntegration", register_fn),
        )
        api.add_routes(
            path="/webhook",
            methods=[apigwv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration("WebhookIntegration", webhook_fn),
        )

        stage = api.default_stage.node.default_child
        stage.default_route_settings = apigwv2.CfnStage.RouteSettingsProperty(
            throttling_rate_limit=5,
            throttling_burst_limit=10,
        )

        CfnOutput(self, "SiteUrl", value=site_url)
        CfnOutput(self, "RegisterUrl", value=api.api_endpoint + "/register")
        CfnOutput(self, "WebhookUrl", value=api.api_endpoint + "/webhook")
