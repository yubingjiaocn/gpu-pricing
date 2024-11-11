import json
import pandas as pd
import csv
import re
from typing import Dict, List

def clean_js_array(content):
    """Clean JavaScript array string to make it valid JSON."""
    # Remove 'var instanceTypeDefineItems = ' from start
    if content.startswith('var instanceTypeDefineItems = '):
        content = content[len('var instanceTypeDefineItems = '):]
    # Remove any trailing semicolon
    if content.endswith(';'):
        content = content[:-1]

    # Fix missing commas between properties
    content = re.sub(r'"\s+(?=")', '",', content)

    # Fix missing commas between objects
    content = re.sub(r'}\s+{', '},{', content)

    # Wrap in array if needed
    if not content.startswith('['):
        content = '[' + content + ']'

    return content

def fix_json_content(content):
    """Fix JSON content by adding missing commas."""
    # Split into lines
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        line = line.strip()
        if line and line[0] == '"' and i > 0 and fixed_lines[-1].strip()[-1] != ',':
            # Add comma to previous line if it's missing
            fixed_lines[-1] = fixed_lines[-1].rstrip() + ','
        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def load_instance_types():
    """Load and parse instance type definitions."""
    with open('instanceTypeDefinition.js', 'r') as f:
        content = f.read()
        # First clean the overall structure
        content = clean_js_array(content)
        # Then fix the JSON content
        content = fix_json_content(content)

        try:
            data = json.loads(content)
            # Print first instance for debugging
            if data and len(data) > 0:
                print("\nFirst instance data:")
                print(json.dumps(data[0], indent=2))
            return data
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {str(e)}")
            print(f"First 500 characters of cleaned JSON:")
            print(content[:500])
            return []

def load_pricing():
    """Load and parse pricing data."""
    with open('instancePrice.json', 'r') as f:
        try:
            data = json.loads(f.read())
            # Print first price entry for debugging
            if data and 'pricingInfo' in data:
                first_key = next(iter(data['pricingInfo']))
                print("\nFirst price entry:")
                print(json.dumps({first_key: data['pricingInfo'][first_key]}, indent=2))
            return data.get('pricingInfo', {})
        except json.JSONDecodeError as e:
            print(f"Error parsing pricing JSON: {str(e)}")
            return {}

def get_instances_in_region(pricing_data: Dict, region: str) -> set:
    """Get set of instance types available in the specified region."""
    region_instances = set()
    for key in pricing_data.keys():
        parts = key.split("::")
        if len(parts) >= 2 and parts[0] == region and "vpc" in key and "linux" in key:
            region_instances.add(parts[1])
    return region_instances

def get_gpu_instances(available_instances: set) -> List[Dict]:
    """Get all GPU instances that are available in the specified instance set."""
    instances = load_instance_types()
    gpu_instances = []

    for instance in instances:
        if not isinstance(instance, dict):
            continue

        gpu_amount = instance.get('GPUAmount', 0)
        instance_type = instance.get('InstanceTypeId')

        if gpu_amount > 0 and instance_type and instance_type in available_instances:
            gpu_info = {
                'Instance Type': instance_type,
                'vCPUs': instance.get('CpuCoreCount', 0),
                'Memory (GB)': instance.get('MemorySize', 0),  # Convert GiB to GB
                'GPU Type': instance.get('GPUSpec', ''),
                'GPU Count': gpu_amount
            }
            gpu_instances.append(gpu_info)

            # Print first GPU instance for debugging
            if len(gpu_instances) == 1:
                print("\nFirst GPU instance:")
                print(json.dumps(gpu_info, indent=2))

    return gpu_instances

def get_prices(gpu_instances: List[Dict], region: str) -> List[Dict]:
    """Get pricing information for GPU instances in the specified region."""
    pricing_data = load_pricing()

    for instance in gpu_instances:
        instance_type = instance['Instance Type']
        price = 0.0

        # Look for the Linux VPC price in the specified region
        for key, price_info in pricing_data.items():
            parts = key.split("::")
            if (len(parts) >= 2 and
                parts[0] == region and
                parts[1] == instance_type and
                "vpc" in key and
                "linux" in key):

                if 'hours' in price_info and price_info['hours']:
                    price = float(price_info['hours'][0].get('price', 0))
                    print(f"Found price for {instance_type}: ${price:.4f}/hr")
                    break

        instance['On-Demand Price ($/hr)'] = price

    return gpu_instances

def standardize_instance_data(instance: Dict, region: str) -> Dict:
    """Standardize instance data format."""
    return {
        'Provider': 'Alibaba',
        'Region': region,
        'Instance Type': instance['Instance Type'],
        'vCPUs': instance['vCPUs'],
        'Memory (GB)': instance['Memory (GB)'],  # Already converted to GB
        'GPU Type': instance['GPU Type'],
        'GPU Count': instance['GPU Count'],
        'On-Demand Price ($/hr)': instance['On-Demand Price ($/hr)'],
        'Spot Price ($/hr)': 0.0  # Alibaba doesn't provide spot pricing in this API
    }

def get_standardized_gpu_instances(region: str) -> List[Dict]:
    """Get standardized GPU instance information for the specified region."""
    # Load pricing data first to get available instances
    print("Loading pricing data...")
    pricing_data = load_pricing()

    # Get instances available in the specified region
    print(f"\nFinding instances available in {region}...")
    region_instances = get_instances_in_region(pricing_data, region)
    print(f"Found {len(region_instances)} instances in {region}")

    # Get GPU instances that are available in the region
    print("\nFetching GPU instance types...")
    gpu_instances = get_gpu_instances(region_instances)

    if not gpu_instances:
        print(f"No GPU instances found in {region}.")
        return []

    print(f"\nFound {len(gpu_instances)} GPU instance types in {region}")

    # Get pricing information
    print("\nFetching pricing information...")
    gpu_instances = get_prices(gpu_instances, region)

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
    region = 'us-west-1'

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
    df.to_csv('alibaba.csv',
              index=False,
              sep=',',
              quoting=csv.QUOTE_MINIMAL)

    print("\nResults saved to alibaba.csv")
    print("\nFirst few rows of the data:")
    print(df.head().to_string())

if __name__ == "__main__":
    main()
