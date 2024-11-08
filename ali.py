import json
import pandas as pd
import csv
import re

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

def get_us_west_1_instances(pricing_data):
    """Get set of instance types available in us-west-1."""
    us_west_1_instances = set()
    for key in pricing_data.keys():
        parts = key.split("::")
        if len(parts) >= 2 and parts[0] == "us-west-1" and "vpc" in key and "linux" in key:
            us_west_1_instances.add(parts[1])
    return us_west_1_instances

def get_gpu_instances(available_instances):
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
                'Memory (GiB)': instance.get('MemorySize', 0),
                'GPU Type': instance.get('GPUSpec', ''),
                'GPU Count': gpu_amount
            }
            gpu_instances.append(gpu_info)

            # Print first GPU instance for debugging
            if len(gpu_instances) == 1:
                print("\nFirst GPU instance:")
                print(json.dumps(gpu_info, indent=2))

    return gpu_instances

def get_prices(gpu_instances):
    """Get pricing information for GPU instances."""
    pricing_data = load_pricing()
    target_region = "us-west-1"

    for instance in gpu_instances:
        instance_type = instance['Instance Type']
        price = 0.0

        # Look for the Linux VPC price in us-west-1
        for key, price_info in pricing_data.items():
            parts = key.split("::")
            if (len(parts) >= 2 and
                parts[0] == target_region and
                parts[1] == instance_type and
                "vpc" in key and
                "linux" in key):

                if 'hours' in price_info and price_info['hours']:
                    price = float(price_info['hours'][0].get('price', 0))
                    print(f"Found price for {instance_type}: ${price:.4f}/hr")
                    break

        instance['On-Demand Price ($/hr)'] = price

    return gpu_instances

def main():
    # Load pricing data first to get available instances
    print("Loading pricing data...")
    pricing_data = load_pricing()

    # Get instances available in us-west-1
    print("\nFinding instances available in us-west-1...")
    us_west_1_instances = get_us_west_1_instances(pricing_data)
    print(f"Found {len(us_west_1_instances)} instances in us-west-1")

    # Get GPU instances that are available in us-west-1
    print("\nFetching GPU instance types...")
    gpu_instances = get_gpu_instances(us_west_1_instances)

    if not gpu_instances:
        print("No GPU instances found in us-west-1.")
        return

    print(f"\nFound {len(gpu_instances)} GPU instance types in us-west-1")

    # Get pricing information
    print("\nFetching pricing information...")
    gpu_instances = get_prices(gpu_instances)

    # Create DataFrame
    df = pd.DataFrame(gpu_instances)

    # Remove rows where Instance Type is empty
    df = df[df['Instance Type'].notna() & (df['Instance Type'] != '')]

    df = df[[
        'Instance Type',
        'vCPUs',
        'Memory (GiB)',
        'GPU Type',
        'GPU Count',
        'On-Demand Price ($/hr)'
    ]]

    # Sort by instance type
    df.sort_values('Instance Type', inplace=True)

    # Format numeric columns
    df['Memory (GiB)'] = df['Memory (GiB)'].map('{:.1f}'.format)
    df['On-Demand Price ($/hr)'] = df['On-Demand Price ($/hr)'].map('{:.4f}'.format)

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
