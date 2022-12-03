import os
import boto3

from botocore.config import Config

main_boto_region = os.environ.get('MAIN_BOTO_REGION', 'eu-central-1')
aws_config = Config(retries={'max_attempts': 30}, region_name='eu-central-1')
aws_config_ddb = Config(retries={'max_attempts': 30}, region_name=os.environ.get('AWS_REGION', 'eu-central-1'))

# Cognito Client.
cognito_client = boto3.client('cognito-idp', region_name=main_boto_region)

# Simple Queue Service Client.
sqs_client = boto3.client('sqs', config=aws_config)

# Simple Notification Service Client.
sns_client = boto3.client('sns', region_name=main_boto_region)

# Simple Email Service Client.
# SES is available only in us-east-1 region, so region_name is hardcoded.
ses_client = boto3.client('ses', config=Config(retries={'max_attempts': 30}, region_name='us-east-1'))

# S3 Resource.
# Resources represent an object-oriented interface to AWS services. Every resource instance has attributes and methods.
s3_resource = boto3.resource('s3', region_name=main_boto_region)

# S3 Client.
# Clients provide a low-level interface to AWS services whose methods map close to 1:1 with service APIs.
s3_client = boto3.client('s3', region_name=main_boto_region)

# Lambda Client.
lambda_client = boto3.client('lambda', region_name=main_boto_region)

# DynamoDB Client.
# DynamoDB has cross region resources for optimisation for calls from various regions.
dynamodb_client = boto3.client('dynamodb', config=aws_config_ddb)
