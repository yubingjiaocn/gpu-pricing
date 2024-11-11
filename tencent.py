import requests
import pandas as pd
import json
import csv
from typing import Dict, List

# Conversion rate from CNY to USD
CNY_TO_USD = 0.138

def get_zone_from_region(region: str) -> str:
    """Get a valid zone from the region (e.g., na-siliconvalley-2 from na-siliconvalley)."""
    return f"{region}-2"

def get_instance_types_with_gpu(region: str) -> List[Dict]:
    """Fetch all Tencent Cloud instance types with GPUs."""
    url = "https://workbench.tencentcloud.com/cgi/api"

    zone = get_zone_from_region(region)

    payload = {
        "serviceType": "cvm",
        "action": "DescribeZoneInstanceConfigInfos",
        "region": region,
        "data": {
            "Filters": [
                {
                    "name": "zone",
                    "Values": [zone]
                },
                {
                    "name": "instance-charge-type",
                    "Values": ["POSTPAID_BY_HOUR"]
                }
            ],
            "Platform": "LINUX",
            "Version": "2017-03-12"
        },
        "cgiName": "api"
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        if 'data' not in data or 'Response' not in data['data']:
            print("Error: Unexpected response format")
            return []

        instances = []
        for instance in data['data']['Response'].get('InstanceTypeQuotaSet', []):
            # Check if instance has GPU
            if instance.get('Gpu', 0) > 0:
                # Extract GPU family from instance type (e.g., GN10X from GN10X.2XLARGE40)
                instance_type = instance.get('InstanceType', '')
                gpu_family = instance_type.split('.')[0] if '.' in instance_type else 'Unknown'

                # Convert price from CNY to USD
                price_cny = instance.get('Price', {}).get('UnitPrice', 0)
                price_usd = price_cny * CNY_TO_USD

                instances.append({
                    'Instance Type': instance_type,
                    'vCPUs': instance.get('Cpu', 0),
                    'Memory (GB)': instance.get('Memory', 0) * 1.074,  # Convert GiB to GB
                    'GPU Type': instance.get('Externals', {}).get('GPUDesc', "0 * N/A").split(" * ")[1],
                    'GPU Count': instance.get('GpuCount', 0),
                    'On-Demand Price ($/hr)': price_usd
                })

        return instances

    except requests.exceptions.RequestException as e:
        print(f"Error fetching instance types: {str(e)}")
        return []

def standardize_instance_data(instance: Dict, region: str) -> Dict:
    """Standardize instance data format."""
    return {
        'Provider': 'Tencent',
        'Region': region,
        'Instance Type': instance['Instance Type'],
        'vCPUs': instance['vCPUs'],
        'Memory (GB)': instance['Memory (GB)'],  # Already converted to GB
        'GPU Type': instance['GPU Type'],
        'GPU Count': instance['GPU Count'],
        'On-Demand Price ($/hr)': instance['On-Demand Price ($/hr)'],
        'Spot Price ($/hr)': 0.0  # Tencent doesn't provide spot pricing in this API
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

    return standardized_instances

def main():
    # Default region if running standalone
    region = 'na-siliconvalley'

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

    # Sort by instance type properly
    df = df.sort_values('Instance Type', key=lambda x: x.str.lower())

    # Format numeric columns
    df['Memory (GB)'] = df['Memory (GB)'].map('{:.1f}'.format)
    df['On-Demand Price ($/hr)'] = df['On-Demand Price ($/hr)'].map('{:.4f}'.format)
    df['Spot Price ($/hr)'] = df['Spot Price ($/hr)'].map('{:.4f}'.format)

    # Save to CSV
    df.to_csv('tencent.csv',
              index=False,
              sep=',',
              quoting=csv.QUOTE_MINIMAL)

    print("\nResults saved to tencent.csv")

    # Display first few rows to verify formatting
    print("\nFirst few rows of the data:")
    print(df.head().to_string())

if __name__ == "__main__":
    main()
