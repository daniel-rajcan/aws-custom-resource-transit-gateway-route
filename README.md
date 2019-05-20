# aws-custom-resource-transit-gateway

AWS lambda written in Python3.7 to support creation of transit gateway route via cloud formation

## Requirements

1. Python 3.7.2 or higher
2. Local directory (NewBotoVersion) with latest boto3 and botocore version
    
## CloudFormation example
    "PrivateTransitGatewayRoute": {
      "Type": "Custom::TransitGatewayRoute",
      "Properties": {
        "ServiceToken": "arn:aws:lambda:<region>:<account_id>:function:<name>",
        "RouteTableId": { "Ref": "PrivateRouteTable" },
        "TransitGatewayId": "tgw-0f8880e8129dd4a1f",
        "DestinationCidrBlock": "10.0.0.0/25"
      }
    },
    
## Notes
Before creation of lambda package the following commands have to be executed in python directory:

 - python3 -m pip install boto3 -t .
 - python3 -m pip install botocore -t .

Inspired by https://www.mandsconsulting.com/lambda-functions-with-newer-version-of-boto3-than-available-by-default/
