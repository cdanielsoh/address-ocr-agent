"""Production environment configuration"""

CONFIG = {
    "environment": "prod",
    "instance_type": "t3.large",
    "min_capacity": 2,
    "max_capacity": 5,
    "desired_capacity": 2,
    "enable_logging": True,
    "enable_monitoring": True,
    "s3_lifecycle_days": 30,
    "health_check_grace_period": 300
}