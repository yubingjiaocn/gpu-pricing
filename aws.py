import boto3
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List
import time
import csv

def get_instance_types_with_gpu(region: str) -> List[Dict]:
    """Fetch all EC2 instance types with GPUs."""
    ec2_client = boto3.client('ec2', region_name=region)

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
                            'Memory (GB)': (instance['MemoryInfo']['SizeInMiB'] / 1024) * 1.074,  # Convert GiB to GB
                            'GPU Type': gpu_info['Gpus'][0]['Name'],
                            'GPU Count': sum(gpu['Count'] for gpu in gpu_info['Gpus'])
                        })
    except Exception as e:
        print(f"Error fetching instance types: {str(e)}")
        return []

    return instance_types

def get_on_demand_price(instance_type: str, region: str) -> float:
    """Get on-demand price for an instance type in the specified region."""
    pricing_client = boto3.client('pricing', region_name='us-east-1')  # Pricing API only available in us-east-1

    try:
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                {'Type': 'TERM_MATCH', 'Field': 'regionCode', 'Value': region},
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

def get_spot_price_90d_average(instance_type: str, region: str) -> float:
    """Get 90-day average spot price across all AZs in the specified region."""
    ec2_client = boto3.client('ec2', region_name=region)
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

def standardize_instance_data(instance: Dict, region: str) -> Dict:
    """Standardize instance data format."""
    instance_type = instance['Instance Type']

    # Get pricing information
    on_demand_price = get_on_demand_price(instance_type, region)
    spot_price = get_spot_price_90d_average(instance_type, region)

    return {
        'Provider': 'AWS',
        'Region': region,
        'Instance Type': instance_type,
        'vCPUs': instance['vCPUs'],
        'Memory (GB)': instance['Memory (GB)'],
        'GPU Type': instance['GPU Type'],
        'GPU Count': instance['GPU Count'],
        'On-Demand Price ($/hr)': on_demand_price,
        'Spot Price ($/hr)': spot_price
    }

def get_standardized_gpu_instances(region: str) -> List[Dict]:
    """Get standardized GPU instance information for the specified region."""
    # Get all GPU instances
    print("Fetching GPU instance types...")
    gpu_instances = get_instance_types_with_gpu(region)

    if not gpu_instances:
        print("No GPU instances found or error occurred.")
        return []

    print(f"Found {len(gpu_instances)} GPU instance types")

    # Standardize each instance
    print("Standardizing instance data...")
    standardized_instances = []
    for instance in gpu_instances:
        print(f"Processing {instance['Instance Type']}...")
        standardized = standardize_instance_data(instance, region)
        standardized_instances.append(standardized)
        time.sleep(0.5)  # Add delay to avoid API throttling

    return standardized_instances

def main():
    # Default region if running standalone
    region = 'us-east-1'

    # Get standardized GPU instances
    gpu_instances = get_standardized_gpu_instances(region)

    if not gpu_instances:
        print("No GPU instances found or error occurred.")
        return

    # Create DataFrame
    df = pd.DataFrame(gpu_instances)
    df = df[[
        'Provider',
        'Region',
        'Instance Type',
        'vCPUs',
        'Memory (GB)',
        'GPU Type',
        'GPU Count',
        'On-Demand Price ($/hr)',
        'Spot Price ($/hr)'
    ]]

    # Sort by instance type
    df.sort_values('Instance Type', inplace=True)

    # Format numeric columns
    df['Memory (GB)'] = df['Memory (GB)'].map('{:.1f}'.format)
    df['On-Demand Price ($/hr)'] = df['On-Demand Price ($/hr)'].map('{:.4f}'.format)
    df['Spot Price ($/hr)'] = df['Spot Price ($/hr)'].map('{:.4f}'.format)

    # Save to CSV
    df.to_csv('aws.csv',
              index=False,
              sep=',',
              quoting=csv.QUOTE_MINIMAL)

    print("\nResults saved to aws.csv")

    # Display first few rows to verify formatting
    print("\nFirst few rows of the data:")
    print(df.head().to_string())

if __name__ == "__main__":
    main()
