import boto3
import time
import logging
import sys

logging.basicConfig(level=logging.INFO)

ec2 = boto3.client("ec2")


def delete_instances(vpc_id):
    instances = ec2.describe_instances(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["Reservations"]
    if not instances:
        return
    instance_ids = [i["InstanceId"] for i in instances]
    ec2.terminate_instances(InstanceIds=instance_ids)
    ec2.get_waiter("instance_terminated").wait(InstanceIds=instance_ids)
    logging.info(f"Deleted {len(instance_ids)} instances")


def delete_endpoints(vpc_id):
    endpoints = ec2.describe_vpc_endpoints(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["VpcEndpoints"]
    if not endpoints:
        return
    endpoint_ids = [i["VpcEndpointId"] for i in endpoints]
    ec2.delete_vpc_endpoints(VpcEndpointIds=endpoint_ids)
    while True:
        endpoints = ec2.describe_vpc_endpoints(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )["VpcEndpoints"]
        if endpoints:
            logging.info(f"Found {len(endpoints)} endpoints. Waiting...")
            time.sleep(10)
        break
    logging.info(f"Deleted {len(endpoint_ids)} endpoints")


def delete_subnets(vpc_id):
    subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])[
        "Subnets"
    ]
    if not subnets:
        return
    subnet_ids = [s["SubnetId"] for s in subnets]
    for subnet_id in subnet_ids:
        ec2.delete_subnet(SubnetId=subnet_id)
    while True:
        subnets = ec2.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )["Subnets"]
        if subnets:
            logging.info(f"Found {len(subnets)} subnets. Waiting...")
            time.sleep(10)
        break
    logging.info(f"Deleted {len(subnet_ids)} subnets.")


def delete_nat_gateways(vpc_id):
    gateways = ec2.describe_nat_gateways(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["NatGateways"]
    if not gateways:
        return
    for gw in gateways:
        ec2.delete_nat_gateway(NatGatewayId=gw["NatGatewayId"])
    ec2.get_waiter("nat_gateway_deleted").wait(
        NatGatewayIds=[g["NatGatewayId"] for g in gateways]
    )
    logging.info(f"Deleted {len(gateways)} nat gateways")


def delete_vpc(vpc_id):
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Vpcs"]
    if not vpcs:
        return
    logging.info(f"Deleting {vpc_id}")
    delete_instances(vpc_id)
    delete_endpoints(vpc_id)
    delete_nat_gateways(vpc_id)
    delete_subnets(vpc_id)
    ec2.delete_vpc(VpcId=vpc_id)
    while True:
        vpcs = ec2.describe_vpcs(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])[
            "Vpcs"
        ]
        if vpcs:
            logging.info(f"Found {len(vpcs)} vpcs. Waiting...")
            time.sleep(10)
        break
    logging.info(f"Deleted {vpc_id}")


name = sys.argv[1]
vpcs = ec2.describe_vpcs(Filters=[{"Name": f"tag:Name", "Values": [name]}])["Vpcs"]
for vpc in vpcs:
    delete_vpc(vpc["VpcId"])
