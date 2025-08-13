"""Development environment configuration"""

CONFIG = {
    "environment": "dev",
    "instance_type": "t3.medium",
    "min_capacity": 1,
    "max_capacity": 2,
    "desired_capacity": 1,
    "enable_logging": True,
    "enable_monitoring": False,
    "s3_lifecycle_days": 7,
    "health_check_grace_period": 300
}