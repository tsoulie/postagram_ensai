#!/usr/bin/env python
from constructs import Construct
from cdktf import App, TerraformStack
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.default_vpc import DefaultVpc
from cdktf_cdktf_provider_aws.default_subnet import DefaultSubnet
from cdktf_cdktf_provider_aws.launch_template import LaunchTemplate
from cdktf_cdktf_provider_aws.lb import Lb
from cdktf_cdktf_provider_aws.lb_target_group import LbTargetGroup
from cdktf_cdktf_provider_aws.lb_listener import LbListener, LbListenerDefaultAction
from cdktf_cdktf_provider_aws.autoscaling_group import AutoscalingGroup
from cdktf_cdktf_provider_aws.security_group import SecurityGroup, SecurityGroupIngress, SecurityGroupEgress
from cdktf_cdktf_provider_aws.data_aws_caller_identity import DataAwsCallerIdentity

import base64

bucket=""
dynamo_table=""
your_repo=""


user_data= base64.b64encode(f"""
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

class ServerStack(TerraformStack):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        AwsProvider(self, "AWS", region="us-east-1")
        account_id = DataAwsCallerIdentity(self, "acount_id").account_id

        default_vpc = DefaultVpc(
            self, "default_vpc"
        )
         
        # Les AZ de us-east-1 sont de la forme us-east-1x 
        # avec x une lettre dans abcdef. Ne permet pas de déployer
        # automatiquement ce code sur une autre région. Le code
        # pour y arriver est vraiment compliqué.
        az_ids = [f"us-east-1{i}" for i in "abcdef"]
        subnets= []
        for i,az_id in enumerate(az_ids):
            subnets.append(DefaultSubnet(
            self, f"default_sub{i}",
            availability_zone=az_id
        ).id)
            

        security_group = SecurityGroup(
            self, "sg-tp",
            ingress=[
                SecurityGroupIngress(
                    from_port=22,
                    to_port=22,
                    cidr_blocks=["0.0.0.0/0"],
                    protocol="TCP",
                ),
                SecurityGroupIngress(
                    from_port=80,
                    to_port=80,
                    cidr_blocks=["0.0.0.0/0"],
                    protocol="TCP"
                ),
                SecurityGroupIngress(
                    from_port=8080,
                    to_port=8080,
                    cidr_blocks=["0.0.0.0/0"],
                    protocol="TCP"
                )
            ],
            egress=[
                SecurityGroupEgress(
                    from_port=0,
                    to_port=0,
                    cidr_blocks=["0.0.0.0/0"],
                    protocol="-1"
                )
            ]
            )
        
        launch_template = LaunchTemplate()
        
        lb = Lb()

        target_group=LbTargetGroup()

        lb_listener = LbListener()

        asg = AutoscalingGroup()


app = App()
ServerStack(app, "cdktf_server")
app.synth()
