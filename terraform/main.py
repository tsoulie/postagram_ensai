#!/usr/bin/env python

from constructs import Construct
from cdktf import App, TerraformStack
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.default_vpc import DefaultVpc
from cdktf_cdktf_provider_aws.default_subnet import DefaultSubnet
from cdktf_cdktf_provider_aws.lambda_function import LambdaFunction
from cdktf_cdktf_provider_aws.lambda_permission import LambdaPermission
from cdktf_cdktf_provider_aws.data_aws_caller_identity import DataAwsCallerIdentity
from cdktf_cdktf_provider_aws.s3_bucket import S3Bucket
from cdktf_cdktf_provider_aws.s3_bucket_cors_configuration import S3BucketCorsConfiguration, S3BucketCorsConfigurationCorsRule
from cdktf_cdktf_provider_aws.s3_bucket_notification import S3BucketNotification, S3BucketNotificationLambdaFunction
from cdktf_cdktf_provider_aws.dynamodb_table import DynamodbTable, DynamodbTableAttribute, DynamodbTableGlobalSecondaryIndex
from cdktf_cdktf_provider_aws.ec2_instance import Ec2Instance
from cdktf_cdktf_provider_aws.security_group import SecurityGroup
from cdktf_cdktf_provider_aws.security_group_rule import SecurityGroupRule
from cdktf_cdktf_provider_aws.elb import LoadBalancer, LoadBalancerListener, LoadBalancerHealthCheck
import os


class MyStack(TerraformStack):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        vpc = DefaultVpc(self, "DefaultVPC")
        subnet = DefaultSubnet(self, "DefaultSubnet",
                               availability_zone="us-east-1a")

        security_group = SecurityGroup(self, "SecurityGroup",
                                       vpc_id=vpc.id,
                                       description="Allow SSH and HTTP",
                                       ingress=[
                                           SecurityGroupRule(
                                               protocol="tcp",
                                               from_port=22,
                                               to_port=22,
                                               cidr_blocks=["0.0.0.0/0"]
                                           ),
                                           SecurityGroupRule(
                                               protocol="tcp",
                                               from_port=80,
                                               to_port=80,
                                               cidr_blocks=["0.0.0.0/0"]
                                           )
                                       ],
                                       egress=[
                                           SecurityGroupRule(
                                               protocol="-1",
                                               from_port=0,
                                               to_port=0,
                                               cidr_blocks=["0.0.0.0/0"]
                                           )
                                       ])

        ec2_instance = Ec2Instance(self, "Ec2Instance",
                                   ami="ami-0c55b159cbfafe1f0",
                                   instance_type="t2.micro",
                                   subnet_id=subnet.id,
                                   vpc_security_group_ids=[security_group.id],
                                   tags={"Name": "CDKTF-Instance"})

        load_balancer = LoadBalancer(self, "LoadBalancer",
                                     availability_zones=["us-east-1a"],
                                     security_groups=[security_group.id],
                                     instances=[ec2_instance.id],
                                     listener=[LoadBalancerListener(
                                         instance_port=80,
                                         instance_protocol="HTTP",
                                         lb_port=80,
                                         lb_protocol="HTTP"
                                     )],
                                     health_check=LoadBalancerHealthCheck(
                                         target="HTTP:80/",
                                         interval=30,
                                         timeout=5,
                                         healthy_threshold=2,
                                         unhealthy_threshold=2
                                     ))


app = App()
MyStack(app, "ter")

app.synth()
