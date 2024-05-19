#!/usr/bin/env python
from constructs import Construct
from cdktf import App, TerraformStack, TerraformOutput
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.default_vpc import DefaultVpc
from cdktf_cdktf_provider_aws.default_subnet import DefaultSubnet
from cdktf_cdktf_provider_aws.launch_template import (
    LaunchTemplate,
    LaunchTemplateIamInstanceProfile,
)
from cdktf_cdktf_provider_aws.lb import Lb
from cdktf_cdktf_provider_aws.lb_target_group import LbTargetGroup
from cdktf_cdktf_provider_aws.lb_listener import LbListener, LbListenerDefaultAction
from cdktf_cdktf_provider_aws.autoscaling_group import (
    AutoscalingGroup,
    AutoscalingGroupLaunchTemplate,
)
from cdktf_cdktf_provider_aws.security_group import (
    SecurityGroup,
    SecurityGroupIngress,
    SecurityGroupEgress,
)
from cdktf_cdktf_provider_aws.data_aws_caller_identity import DataAwsCallerIdentity
import base64


####Valeurs à changer à la main

bucket = "my-cdtf-test-bucket20240518174611015700000001"
dynamo_table = "user_score"
your_repo = "https://github.com/Krrcharles/postagram_ensai.git"

user_data = base64.b64encode(
    f"""#!/bin/bash
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
echo "userdata-end"
""".encode(
        "ascii"
    )
).decode("ascii")


class ServerStack(TerraformStack):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        AwsProvider(self, "AWS", region="us-east-1")
        account_id = DataAwsCallerIdentity(self, "acount_id").account_id

        default_vpc = DefaultVpc(self, "default_vpc")

        # Les AZ de us-east-1 sont de la forme us-east-1x
        # avec x une lettre dans abcdef. Ne permet pas de déployer
        # automatiquement ce code sur une autre région. Le code
        # pour y arriver est vraiment compliqué.
        az_ids = [f"us-east-1{i}" for i in "abcdef"]
        subnets = []
        for i, az_id in enumerate(az_ids):
            subnets.append(
                DefaultSubnet(self, f"default_sub{i}", availability_zone=az_id).id
            )

        security_group = SecurityGroup(
            self,
            "sg-tp",
            ingress=[
                SecurityGroupIngress(
                    from_port=22,
                    to_port=22,
                    cidr_blocks=["0.0.0.0/0"],
                    protocol="TCP",
                ),
                SecurityGroupIngress(
                    from_port=80, to_port=80, cidr_blocks=["0.0.0.0/0"], protocol="TCP"
                ),
                SecurityGroupIngress(
                    from_port=8080,
                    to_port=8080,
                    cidr_blocks=["0.0.0.0/0"],
                    protocol="TCP",
                ),
            ],
            egress=[
                SecurityGroupEgress(
                    from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"], protocol="-1"
                )
            ],
        )

        launch_template = LaunchTemplate(
            self,
            "lt",
            image_id="ami-04b70fa74e45c3917",
            instance_type="t2.micro",
            user_data=user_data,
            vpc_security_group_ids=[security_group.id],
            key_name="vockey",
            iam_instance_profile=LaunchTemplateIamInstanceProfile(
                arn=f"arn:aws:iam::{account_id}:instance-profile/LabInstanceProfile"
            ),
            tags={"Name": "postagram-server"},
        )

        lb = Lb(
            self,
            "lb",
            security_groups=[security_group.id],
            subnets=subnets,
            load_balancer_type="application",
        )

        target_group = LbTargetGroup(
            self,
            "target_group",
            port=80,
            protocol="HTTP",
            vpc_id=default_vpc.id,
            target_type="instance",
        )

        lb_listener = LbListener(
            self,
            "lb-listener",
            load_balancer_arn=lb.arn,
            port=80,
            protocol="HTTP",
            default_action=[
                LbListenerDefaultAction(
                    type="forward", target_group_arn=target_group.arn
                )
            ],
        )

        asg = AutoscalingGroup(
            self,
            "asg",
            launch_template=AutoscalingGroupLaunchTemplate(
                id=launch_template.id, version="$Latest"
            ),
            vpc_zone_identifier=subnets,
            target_group_arns=[target_group.arn],
            min_size=1,
            max_size=3,
            desired_capacity=1,
        )

        # Output dynamo_table id à mettre dans le index.js de la webapp
        TerraformOutput(
            self,
            "URL to put in index.js (http + DNS name):",
            value="http://" + lb.dns_name,
        )


app = App()
ServerStack(app, "cdktf_server")
app.synth()
