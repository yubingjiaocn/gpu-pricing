import boto3
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List
import time
import csv

def get_instance_types_with_gpu() -> List[Dict]:
    """Fetch all EC2 instance types with GPUs."""
    ec2_client = boto3.client('ec2', region_name='us-west-2')

    # Get all instance types
    instance_types = []
    paginator = ec2_client.get_paginator('describe_instance_types')

    try:
        # First, get all instance types
        for page in paginator.paginate():
            for instance in page['InstanceTypes']:
                if 'GpuInfo' in instance:
                    gpu_info = instance['GpuInfo']
                    if 'Gpus' in gpu_info and gpu_info['Gpus']:
                        instance_types.append({
                            'Instance Type': instance['InstanceType'],
                            'vCPUs': instance['VCpuInfo']['DefaultVCpus'],
                            'Memory (GiB)': instance['MemoryInfo']['SizeInMiB'] / 1024,  # Convert MiB to GiB
                            'GPU Type': gpu_info['Gpus'][0]['Name'],
                            'GPU Count': sum(gpu['Count'] for gpu in gpu_info['Gpus'])
                        })
    except Exception as e:
        print(f"Error fetching instance types: {str(e)}")
        return []

    return instance_types

def get_on_demand_price(instance_type: str) -> float:
    """Get on-demand price for an instance type in us-east-1."""
    pricing_client = boto3.client('pricing', region_name='us-east-1')

    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': 'us-east-1'},
                {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'}
            ]
        )

        if response['PriceList']:
            price_data = json.loads(response['PriceList'][0])
            terms = price_data['terms']['OnDemand']
            price_dimensions = list(terms.values())[0]['priceDimensions']
            price = float(list(price_dimensions.values())[0]['pricePerUnit']['USD'])
            return price
    except Exception as e:
        print(f"Error getting on-demand price for {instance_type}: {str(e)}")

    return 0.0

def get_spot_price_90d_average(instance_type: str) -> float:
    """Get 90-day average spot price across all AZs in us-east-1."""
    ec2_client = boto3.client('ec2', region_name='us-east-1')
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=90)

    try:
        prices = []
        paginator = ec2_client.get_paginator('describe_spot_price_history')

        for page in paginator.paginate(
            InstanceTypes=[instance_type],
            ProductDescriptions=['Linux/UNIX'],
            StartTime=start_time,
            EndTime=end_time
        ):
            prices.extend([float(price['SpotPrice']) for price in page['SpotPriceHistory']])

        if prices:
            return sum(prices) / len(prices)
    except Exception as e:
        print(f"Error getting spot price for {instance_type}: {str(e)}")

    return 0.0

def main():
    # Get all GPU instances
    print("Fetching GPU instance types...")
    gpu_instances = get_instance_types_with_gpu()

    if not gpu_instances:
        print("No GPU instances found or error occurred.")
        return

    print(f"Found {len(gpu_instances)} GPU instance types")

    # Get pricing information
    print("Fetching pricing information...")
    for instance in gpu_instances:
        instance_type = instance['Instance Type']
        print(f"Processing {instance_type}...")

        # Get on-demand price
        instance['On-Demand Price ($/hr)'] = get_on_demand_price(instance_type)

        # Get spot price
        instance['Spot Price 90d Avg ($/hr)'] = get_spot_price_90d_average(instance_type)

        # Add some delay to avoid API throttling
        time.sleep(0.5)

    # Create DataFrame and save to CSV
    df = pd.DataFrame(gpu_instances)
    df = df[[
        'Instance Type',
        'vCPUs',
        'Memory (GiB)',
        'GPU Type',
        'GPU Count',
        'On-Demand Price ($/hr)',
        'Spot Price 90d Avg ($/hr)'
    ]]

    # Sort by instance type
    df.sort_values('Instance Type', inplace=True)

    # Format numeric columns
    df['Memory (GiB)'] = df['Memory (GiB)'].map('{:.1f}'.format)  # Format memory to 1 decimal place
    df['On-Demand Price ($/hr)'] = df['On-Demand Price ($/hr)'].map('{:.4f}'.format)
    df['Spot Price 90d Avg ($/hr)'] = df['Spot Price 90d Avg ($/hr)'].map('{:.4f}'.format)

    # Save to CSV with proper formatting
    df.to_csv('aws.csv',
              index=False,
              sep=',',
              quoting=csv.QUOTE_MINIMAL)  # Only quote fields that contain special characters

    print("\nResults saved to aws.csv")

    # Display first few rows to verify formatting
    print("\nFirst few rows of the data:")
    print(df.head().to_string())

if __name__ == "__main__":
    main()
