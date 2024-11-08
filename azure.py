import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List
import time
import csv

def get_pricing_data() -> Dict:
    """Fetch pricing data for US West region."""
    url = "https://azure.microsoft.com/api/v3/pricing/virtual-machines/page/linux/us-west/"
    params = {
        'showLowPriorityOffers': 'false'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pricing data: {str(e)}")
        if hasattr(response, 'text'):
            print(f"Response content: {response.text}")
        return {}

def get_instance_details() -> Dict:
    """Fetch instance details including GPU information."""
    url = "https://azure.microsoft.com/api/v3/pricing/virtual-machines/page/details/linux/"
    params = {
        'culture': 'en-us',
        'showLowPriorityOffers': 'false'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('attributesByOffer', {})
    except requests.exceptions.RequestException as e:
        print(f"Error fetching instance details: {str(e)}")
        if hasattr(response, 'text'):
            print(f"Response content: {response.text}")
        return {}

def parse_gpu_info(gpu_string: str) -> Dict:
    """Parse GPU information from format like '1X V100'."""
    if not gpu_string:
        return None

    try:
        # Split the string into count and type
        count_str, gpu_type = gpu_string.split('X ', 1)
        count = int(count_str.strip())
        gpu_type = f"{gpu_type.strip()}"

        return {
            'gpu_type': gpu_type,
            'gpu_count': count
        }
    except (ValueError, AttributeError):
        return None

def get_gpu_instances() -> List[Dict]:
    """Get all VM sizes with GPUs and their pricing information."""
    print("Fetching pricing data...")
    pricing_data = get_pricing_data()

    print("Fetching instance details...")
    instance_details = get_instance_details()

    if not pricing_data or not instance_details:
        print("Missing required data:")
        print(f"Pricing data: {'Present' if pricing_data else 'Missing'}")
        print(f"Instance details: {'Present' if instance_details else 'Missing'}")
        return []

    # Extract GPU instances and their details
    gpu_instances = {}

    # First identify all GPU instances from instance details
    for instance_type, details in instance_details.items():
        if 'gpu' not in details:
            continue

        gpu_info = parse_gpu_info(details['gpu'])
        if not gpu_info:
            continue

        # Get pricing information if available
        price_info = pricing_data.get(instance_type, {})
        on_demand_price = price_info.get('perhour', 0.0)
        spot_price = price_info.get('perhourspot', 0.0)

        # Get display name from instance details
        display_name = details.get('instanceName', instance_type.replace('linux-', '').replace('-standard', ''))

        # Create instance entry
        gpu_instances[instance_type] = {
            'Instance Type': display_name,
            'vCPUs': details.get('cores', 0),
            'Memory (GB)': details.get('ram', 0),
            'GPU Type': gpu_info['gpu_type'],
            'GPU Count': gpu_info['gpu_count'],
            'On-Demand Price ($/hr)': on_demand_price,
            'Spot Price ($/hr)': spot_price
        }

    return list(gpu_instances.values())

def main():
    # Get all GPU instances
    print("Fetching GPU instance types...")
    gpu_instances = get_gpu_instances()

    if not gpu_instances:
        print("No GPU instances found or error occurred.")
        return

    print(f"\nFound {len(gpu_instances)} GPU instance types")

    # Create DataFrame
    df = pd.DataFrame(gpu_instances)
    df = df[[
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
    df['On-Demand Price ($/hr)'] = df['On-Demand Price ($/hr)'].map('{:.4f}'.format)
    df['Spot Price ($/hr)'] = df['Spot Price ($/hr)'].map('{:.4f}'.format)

    # Save to CSV
    df.to_csv('azure.csv',
              index=False,
              sep=',',
              quoting=csv.QUOTE_MINIMAL)

    print("\nResults saved to azure.csv")

    # Display first few rows to verify formatting
    print("\nFirst few rows of the data:")
    print(df.head().to_string())

if __name__ == "__main__":
    main()
