import sys
import re
import json
import logging

sys.path.insert(0, "./NewBotoVersion")
import boto3
from botocore.exceptions import ClientError
from botocore.vendored import requests


def check_if_route_exists_in_route_table(_route_table_id, _destination_cidr_block):
    exists = False

    try:
        client = boto3.client('ec2')

        response = client.describe_route_tables(RouteTableIds=[_route_table_id])

        routes = response['RouteTables'][0]['Routes']

    except (ClientError, TypeError) as e:
        logging.error(str(e))

    for route in routes:
        try:
            route_destination_cidr_block = route['DestinationCidrBlock']
        except KeyError:
            continue

        if route_destination_cidr_block == _destination_cidr_block:
            exists = True

            break

    return exists


def check_if_resource_exists_in_cloudformation(_stack_name, _logical_resource_id):
    exists = False

    try:
        client = boto3.client('cloudformation')

        response = client.describe_stack_resource(StackName=_stack_name,
                                                  LogicalResourceId=_logical_resource_id)

        if response['StackResourceDetail']['ResourceStatus'] != 'CREATE_FAILED':
            exists = True

    except (ClientError, TypeError) as e:
        logging.error(str(e))

    return exists


def create_ec2_tgw_route(_event):
    response = {
        'status': 'FAILED',
        'reason': ''
    }

    resource_type = _event['ResourceType']

    if resource_type == 'Custom::TransitGatewayRoute':
        try:
            route_table_id = str(_event['ResourceProperties']['RouteTableId'])
            transit_gateway_id = str(_event['ResourceProperties']['TransitGatewayId'])
            destination_cidr_block = str(_event['ResourceProperties']['DestinationCidrBlock'])

        except KeyError:
            response['reason'] = 'Unknown property'

            logging.error(response['reason'])

            return response

        route_exists = check_if_route_exists_in_route_table(_route_table_id=route_table_id,
                                                            _destination_cidr_block=destination_cidr_block)

        if not route_exists:
            try:
                client = boto3.client('ec2')

                client.create_route(RouteTableId=route_table_id,
                                    TransitGatewayId=transit_gateway_id,
                                    DestinationCidrBlock=destination_cidr_block)

                response['status'] = 'SUCCESS'

            except ClientError as e:
                reason = str(e)

                logging.error(reason)

                response['reason'] = reason

        else:
            response['reason'] = 'The route identified by ' + destination_cidr_block + ' already exists'
    else:
        response['reason'] = 'Unknown resource type'

    return response


def delete_ec2_tgw_route(_event, _update=False):
    response = {
        'status': 'SUCCESS',
        'reason': ''
    }

    resource_type = _event['ResourceType']

    if resource_type == 'Custom::TransitGatewayRoute':
        stack_name = re.search(r'stack\/([^\/]+)', _event['StackId']).group(1)
        logical_resource_id = _event['LogicalResourceId']

        resource_exists = check_if_resource_exists_in_cloudformation(stack_name, logical_resource_id)

        if resource_exists:
            if _update:
                try:
                    route_table_id = str(_event['OldResourceProperties']['RouteTableId'])
                    destination_cidr_block = str(_event['OldResourceProperties']['DestinationCidrBlock'])

                except KeyError:
                    return response

            else:
                route_table_id = str(_event['ResourceProperties']['RouteTableId'])
                destination_cidr_block = str(_event['ResourceProperties']['DestinationCidrBlock'])

            try:
                client = boto3.client('ec2')

                client.delete_route(RouteTableId=route_table_id,
                                    DestinationCidrBlock=destination_cidr_block)

            except (ClientError, TypeError) as e:
                reason = str(e)

                logging.error(reason)

                response['status'] = 'FAILED'
                response['reason'] = reason

    return response


def send_response(_event, _status, _reason):
    url = _event['ResponseURL']

    headers = {
        'Content-Type': ''
    }

    data = {
        'Status': _status,
        'RequestId': _event['RequestId'],
        'LogicalResourceId': _event['LogicalResourceId'],
        'StackId': _event['StackId'],
        'Reason': _reason
    }

    if _event['RequestType'] == 'Create':
        data['PhysicalResourceId'] = _event['LogicalResourceId'] + '-' + _event['RequestId']

    else:
        data['PhysicalResourceId'] = _event['PhysicalResourceId']

    data = json.dumps(data)

    try:
        response = requests.put(url=url,
                                data=data,
                                headers=headers)

    except ConnectionError as e:
        reason = str(e)

        logging.error(reason)

    return response


def handler(event, context):
    response = {}
    request_type = event['RequestType']

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if request_type == 'Create':
        response = create_ec2_tgw_route(event)

    elif request_type == 'Update':
        delete_ec2_tgw_route(_event=event, _update=True)

        response = create_ec2_tgw_route(event)

    elif request_type == 'Delete':
        response = delete_ec2_tgw_route(event)

    else:
        response['status'] = 'FAILED'
        response['reason'] = 'Unknown request type: ' + request_type

        logging.error(response['reason'])

    send_response(event, response['status'], response['reason'])
