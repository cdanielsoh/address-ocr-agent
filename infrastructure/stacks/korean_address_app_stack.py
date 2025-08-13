from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
    aws_s3 as s3,
    RemovalPolicy,
    CfnOutput,
    Tags
)
from constructs import Construct

class KoreanAddressAppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, environment: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.environment = environment
        
        # Create VPC
        self.vpc = self._create_vpc()
        
        # Create S3 bucket for images
        self.images_bucket = self._create_s3_bucket()
        
        # Create IAM role for EC2
        self.ec2_role = self._create_ec2_role()
        
        # Create security groups
        self.alb_sg, self.ec2_sg = self._create_security_groups()
        
        # Create Application Load Balancer
        self.alb = self._create_alb()
        
        # Create Auto Scaling Group
        self.asg = self._create_auto_scaling_group()
        
        # Add tags
        self._add_tags()
        
        # Create outputs
        self._create_outputs()
    
    def _create_vpc(self) -> ec2.Vpc:
        """Create VPC with public and private subnets"""
        return ec2.Vpc(
            self, "VPC",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=1,  # Single AZ for PoC
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC,
                    name="PublicSubnet",
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    name="PrivateSubnet",
                    cidr_mask=24
                )
            ]
        )
    
    def _create_s3_bucket(self) -> s3.Bucket:
        """Create S3 bucket for image storage"""
        from aws_cdk import Duration
        return s3.Bucket(
            self, "ImagesBucket",
            bucket_name=f"korean-address-images-{self.account}-{self.environment}",
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteAfter30Days",
                    expiration=Duration.days(30),
                    enabled=True
                )
            ],
            removal_policy=RemovalPolicy.DESTROY if self.environment == "dev" else RemovalPolicy.RETAIN,
            auto_delete_objects=self.environment == "dev"
        )
    
    def _create_ec2_role(self) -> iam.Role:
        """Create IAM role for EC2 instances"""
        role = iam.Role(
            self, "EC2Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess")
            ]
        )
        
        
        # Add S3 permissions
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject"
                ],
                resources=[f"{self.images_bucket.bucket_arn}/*"]
            )
        )
        
        # Add Bedrock permissions for Strands Agents
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )
        
        # Add SageMaker permissions for Upstage OCR
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sagemaker:InvokeEndpoint"
                ],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/endpoint-document-ocr-1",
                    f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/Endpoint-Document-OCR-1"
                ]
            )
        )
        
        return role
    
    def _create_security_groups(self):
        """Create security groups for ALB and EC2"""
        # ALB Security Group
        alb_sg = ec2.SecurityGroup(
            self, "ALBSecurityGroup",
            vpc=self.vpc,
            description="Security group for Application Load Balancer",
            allow_all_outbound=True
        )
        
        alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="HTTP access"
        )
        
        alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="HTTPS access"
        )
        
        # EC2 Security Group
        ec2_sg = ec2.SecurityGroup(
            self, "EC2SecurityGroup",
            vpc=self.vpc,
            description="Security group for EC2 instances",
            allow_all_outbound=True
        )
        
        ec2_sg.add_ingress_rule(
            peer=alb_sg,
            connection=ec2.Port.tcp(3001),
            description="FastAPI from ALB"
        )
        
        return alb_sg, ec2_sg
    
    def _create_alb(self) -> elbv2.ApplicationLoadBalancer:
        """Create Application Load Balancer"""
        return elbv2.ApplicationLoadBalancer(
            self, "ALB",
            vpc=self.vpc,
            internet_facing=True,
            security_group=self.alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        )
    
    def _create_auto_scaling_group(self) -> autoscaling.AutoScalingGroup:
        """Create Auto Scaling Group with EC2 instances"""
        # User data script
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "yum update -y",
            "yum install -y python3 python3-pip git",
            "pip3 install virtualenv",
            
            # Clone and setup application (replace with your repo)
            "cd /home/ec2-user",
            "git clone https://github.com/your-repo/korean-address-extractor.git || echo 'Using local files'",
            "cd korean-address-extractor/backend || cd /opt/korean-address-extractor/backend",
            
            # Setup Python environment
            "python3 -m venv venv",
            "source venv/bin/activate",
            "pip install -r requirements.txt",
            
            # Setup environment variables
            f"echo 'export AWS_REGION=ap-northeast-2' >> /home/ec2-user/.bashrc",
            f"echo 'export AWS_DEFAULT_REGION=us-west-2' >> /home/ec2-user/.bashrc",
            f"echo 'export USE_STRANDS_AGENT=true' >> /home/ec2-user/.bashrc",
            f"echo 'export SAGEMAKER_OCR_ENDPOINT_NAME=Endpoint-Document-OCR-1' >> /home/ec2-user/.bashrc",
            f"echo 'export S3_BUCKET_NAME={self.images_bucket.bucket_name}' >> /home/ec2-user/.bashrc",
            
            # Start the application
            "source /home/ec2-user/.bashrc",
            "cd /home/ec2-user/korean-address-extractor/backend",
            "source venv/bin/activate",
            "nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 3001 > /var/log/app.log 2>&1 &"
        )
        
        # Create launch template
        launch_template = ec2.LaunchTemplate(
            self, "LaunchTemplate",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MEDIUM),
            machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023),
            security_group=self.ec2_sg,
            role=self.ec2_role,
            user_data=user_data
        )
        
        # Create Auto Scaling Group
        asg = autoscaling.AutoScalingGroup(
            self, "ASG",
            vpc=self.vpc,
            launch_template=launch_template,
            min_capacity=1,
            max_capacity=2,
            desired_capacity=1,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            health_check=autoscaling.HealthCheck.elb(grace=Duration.minutes(5))
        )
        
        # Create target group
        target_group = elbv2.ApplicationTargetGroup(
            self, "TargetGroup",
            port=3001,
            protocol=elbv2.ApplicationProtocol.HTTP,
            vpc=self.vpc,
            targets=[asg],
            health_check=elbv2.HealthCheck(
                path="/api/health",
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )
        
        # Add listener to ALB
        self.alb.add_listener(
            "Listener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_target_groups=[target_group]
        )
        
        return asg
    
    def _add_tags(self):
        """Add tags to all resources"""
        Tags.of(self).add("Environment", self.environment)
        Tags.of(self).add("Project", "KoreanAddressExtractor")
        Tags.of(self).add("ManagedBy", "CDK")
    
    def _create_outputs(self):
        """Create CloudFormation outputs"""
        CfnOutput(
            self, "LoadBalancerDNS",
            value=self.alb.load_balancer_dns_name,
            description="DNS name of the load balancer"
        )
        
        CfnOutput(
            self, "S3BucketName",
            value=self.images_bucket.bucket_name,
            description="Name of the S3 bucket for images"
        )