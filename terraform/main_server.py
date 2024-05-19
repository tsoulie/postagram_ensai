#!/usr/bin/env python
from constructs import Construct
from cdktf import App, TerraformStack, TerraformOutput
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.vpc import Vpc
from cdktf_cdktf_provider_aws.subnet import Subnet
from cdktf_cdktf_provider_aws.internet_gateway import InternetGateway
from cdktf_cdktf_provider_aws.route_table import RouteTable
from cdktf_cdktf_provider_aws.route import Route
from cdktf_cdktf_provider_aws.route_table_association import RouteTableAssociation
from cdktf_cdktf_provider_aws.security_group import SecurityGroup, SecurityGroupIngress, SecurityGroupEgress
from cdktf_cdktf_provider_aws.instance import Instance
from cdktf_cdktf_provider_aws.lb import Lb
from cdktf_cdktf_provider_aws.lb_target_group import LbTargetGroup
from cdktf_cdktf_provider_aws.lb_listener import LbListener, LbListenerDefaultAction
from cdktf_cdktf_provider_aws.launch_template import LaunchTemplate
from cdktf_cdktf_provider_aws.autoscaling_group import AutoscalingGroup

import base64

####Valeurs à changer à la main

bucket = "my-cdtf-test-bucket20240518174611015700000001"
dynamo_table = "user_score"
your_repo = "https://github.com/tsoulie/postagram_ensai.git"

user_data = base64.b64encode(f"""
#!/bin/bash
echo "userdata-start"        
apt update
apt install -y python3-pip python3.12-venv
git clone {your_repo} projet
cd projet/webservice
rm .env
echo 'BUCKET={bucket}' >> .env
echo 'DYNAMO_TABLE={dynamo_table}' >> .env
python3 -m venv venv
source venv/bin/activate
chmod -R a+rwx venv
pip3 install -r requirements.txt
python3 app.py
echo "userdata-end""".encode("ascii")).decode("ascii")


class MyStack(TerraformStack):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        AwsProvider(self, "AWS", region="us-east-1")

        # Create the VPC
        vpc = Vpc(self, "DefaultVPC",
                  cidr_block="10.0.0.0/16")

        # Create Subnets
        subnet = Subnet(self, "DefaultSubnet",
                        availability_zone="us-east-1a",
                        vpc_id=vpc.id,
                        cidr_block="10.0.1.0/24")

        subnet2 = Subnet(self, "DefaultSubnet2",
                         availability_zone="us-east-1b",
                         vpc_id=vpc.id,
                         cidr_block="10.0.2.0/24")

        subnet3 = Subnet(self, "DefaultSubnet3",
                         availability_zone="us-east-1c",
                         vpc_id=vpc.id,
                         cidr_block="10.0.3.0/24")

        # Create the Internet Gateway
        internet_gateway = InternetGateway(self, "InternetGateway",
                                           vpc_id=vpc.id)

        # Create a route table
        route_table = RouteTable(self, "RouteTable",
                                 vpc_id=vpc.id)

        # Create a route to the Internet Gateway
        Route(self, "Route",
              route_table_id=route_table.id,
              destination_cidr_block="0.0.0.0/0",
              gateway_id=internet_gateway.id)

        # Associate the route table with the public subnets
        RouteTableAssociation(self, "RouteTableAssociation1",
                              subnet_id=subnet.id,
                              route_table_id=route_table.id)

        RouteTableAssociation(self, "RouteTableAssociation2",
                              subnet_id=subnet2.id,
                              route_table_id=route_table.id)

        RouteTableAssociation(self, "RouteTableAssociation3",
                              subnet_id=subnet3.id,
                              route_table_id=route_table.id)

        # Security Group
        security_group = SecurityGroup(self, "SecurityGroup",
                                       vpc_id=vpc.id,
                                       description="Allow SSH and HTTP",
                                       ingress=[
                                           SecurityGroupIngress(
                                               protocol="tcp",
                                               from_port=22,
                                               to_port=22,
                                               cidr_blocks=["0.0.0.0/0"]
                                           ),
                                           SecurityGroupIngress(
                                               protocol="tcp",
                                               from_port=80,
                                               to_port=80,
                                               cidr_blocks=["0.0.0.0/0"]
                                           )
                                       ],
                                       egress=[
                                           SecurityGroupEgress(
                                               protocol="-1",
                                               from_port=0,
                                               to_port=0,
                                               cidr_blocks=["0.0.0.0/0"]
                                           )
                                       ])

        # EC2 Instance
        ec2_instance = Instance(self, "Ec2Instance",
                                ami="ami-0bb84b8ffd87024d8",
                                instance_type="t2.micro",
                                subnet_id=subnet.id,
                                key_name="vockey",
                                vpc_security_group_ids=[security_group.id],
                                user_data=user_data,
                                tags={"Name": "CDKTF-Instance"})

        # Load Balancer
        load_balancer = Lb(self, "LoadBalancer",
                           name="my-lb",
                           internal=False,
                           load_balancer_type="application",
                           security_groups=[security_group.id],
                           subnets=[subnet3.id, subnet2.id])

        # Target Group
        target_group = LbTargetGroup(self, "TargetGroup",
                                     port=80,
                                     protocol="HTTP",
                                     vpc_id=vpc.id,
                                     target_type="instance",
                                     health_check={
                                         "protocol": "HTTP",
                                         "path": "/",
                                         "interval": 30,
                                         "timeout": 5,
                                         "healthy_threshold": 2,
                                         "unhealthy_threshold": 2
                                     })

        # Load Balancer Listener
        lb_listener = LbListener(self, "LbListener",
                                 load_balancer_arn=load_balancer.arn,
                                 port=80,
                                 protocol="HTTP",
                                 default_action=[LbListenerDefaultAction(
                                     type="forward",
                                     target_group_arn=target_group.arn
                                 )])

        # Launch Template
        launch_template = LaunchTemplate(self, "LaunchTemplate",
                                         name_prefix="example",
                                         instance_type="t2.micro",
                                         image_id="ami-0bb84b8ffd87024d8",
                                         user_data=user_data,
                                         vpc_security_group_ids=[security_group.id])

        # Auto Scaling Group
        autoscaling_group = AutoscalingGroup(self, "AutoScalingGroup",
                                             min_size=1,
                                             max_size=2,
                                             desired_capacity=1,
                                             vpc_zone_identifier=[subnet.id, subnet2.id],
                                             launch_template={
                                                 "id": launch_template.id,
                                                 "version": "$Latest"
                                             },
                                             target_group_arns=[target_group.arn])


        TerraformOutput(
            self,
            "URL to put in index.js (http + DNS name):",
            value="http://" + load_balancer.dns_name,
        )


app = App()
MyStack(app, "cdktf_server")
app.synth()
