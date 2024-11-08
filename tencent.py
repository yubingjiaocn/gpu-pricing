import requests
import pandas as pd
import json
import csv
from typing import Dict, List

def get_instance_types_with_gpu() -> List[Dict]:
    """Fetch all Tencent Cloud instance types with GPUs."""
    url = "https://workbench.tencentcloud.com/cgi/api"

    payload = {
        "serviceType": "cvm",
        "action": "DescribeZoneInstanceConfigInfos",
        "region": "na-siliconvalley",
        "data": {
            "Filters": [
                {
                    "name": "zone",
                    "Values": ["na-siliconvalley-2"]
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

                instances.append({
                    'Instance Type': instance_type,
                    'vCPUs': instance.get('Cpu', 0),
                    'Memory (GiB)': instance.get('Memory', 0),
                    'GPU Type': instance.get('Externals', {}).get('GPUDesc', "0 * N/A").split(" * ")[1],
                    'GPU Count': instance.get('GpuCount', 0),
                    'On-Demand Price ($/hr)': instance.get('Price', {}).get('UnitPrice', 0)
                })

        return instances

    except requests.exceptions.RequestException as e:
        print(f"Error fetching instance types: {str(e)}")
        return []

def main():
    # Get all GPU instances
    print("Fetching GPU instance types...")
    gpu_instances = get_instance_types_with_gpu()

    if not gpu_instances:
        print("No GPU instances found or error occurred.")
        return

    print(f"Found {len(gpu_instances)} GPU instance types")

    # Create DataFrame
    df = pd.DataFrame(gpu_instances)
    df = df[[
        'Instance Type',
        'vCPUs',
        'Memory (GiB)',
        'GPU Type',
        'GPU Count',
        'On-Demand Price ($/hr)'
    ]]

    # Sort by instance type properly
    df = df.sort_values('Instance Type', key=lambda x: x.str.lower())

    # Format numeric columns
    df['Memory (GiB)'] = df['Memory (GiB)'].map('{:.1f}'.format)
    df['On-Demand Price ($/hr)'] = df['On-Demand Price (CNY/hr)'].map('{:.4f}'.format)

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
