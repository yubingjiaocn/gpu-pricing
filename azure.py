import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List
import time
import csv
import re
import io

def convert_region_name(region: str) -> str:
    """Convert region name to Azure's format."""
    region_map = {
        'us-west': 'westus',
        'us-east': 'eastus',
        'us-central': 'centralus',
        'eu-west': 'westeurope',
        'eu-central': 'centraleurope',
        'ap-east': 'eastasia',
        'ap-southeast': 'southeastasia',
        'china-east': 'chinaeast',
        'china-east2': 'chinaeast2',
        'china-north': 'chinanorth',
        'china-north2': 'chinanorth2'
    }
    return region_map.get(region.lower(), region.lower().replace('-', ''))

def get_vm_pricing_data(region: str) -> List[Dict]:
    """Fetch pricing data for Virtual Machines from Azure retail prices API."""
    azure_region = convert_region_name(region)

    # Use China-specific endpoint if region is in China
    if 'china' in region.lower():
        base_url = "https://prices.azure.cn/api/retail/pricesheet/download"
        params = {
            'api-version': '2023-06-01-preview'
        }

        print(f"Fetching VM pricing data for China region: {azure_region}")

        try:
            # Get the download URL
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            download_url = data.get('DownloadUrl')
            if not download_url:
                print("Error: No download URL found in response")
                return []

            # Download the CSV file
            csv_response = requests.get(download_url)
            csv_response.raise_for_status()

            # Parse CSV content
            all_items = []
            csv_content = csv_response.content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_content))

            for row in csv_reader:
                # Filter for Virtual Machines in the specified region
                if (row.get('serviceName') == 'Virtual Machines' and
                    row.get('armRegionName', '').lower() == azure_region.lower()):
                    all_items.append({
                        'armSkuName': row.get('armSkuName', ''),
                        'skuName': row.get('skuName', ''),
                        'retailPrice': float(row.get('retailPrice', 0)),
                        'isPrimaryMeterRegion': row.get('isPrimaryMeterRegion', '').lower() == 'true'
                    })

            print(f"Retrieved {len(all_items)} pricing records for China region")
            return all_items

        except requests.exceptions.RequestException as e:
            print(f"Error fetching China pricing data: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Response content: {e.response.text}")
            return []

    # Original implementation for non-China regions
    base_url = "https://prices.azure.com/api/retail/prices"
    filter_query = f"serviceName eq 'Virtual Machines' and armRegionName eq '{azure_region}'"
    params = {
        'api-version': '2023-01-01-preview',
        '$filter': filter_query
    }

    print(f"Fetching VM pricing data for region: {azure_region}")

    all_items = []

    try:
        while True:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            items = data.get('Items', [])
            primary_items = [item for item in items
                           if item.get('isPrimaryMeterRegion', False)]
            all_items.extend(primary_items)

            next_page = data.get('NextPageLink')
            if not next_page:
                break

            base_url = next_page
            params = {}
            time.sleep(0.5)

        print(f"Retrieved {len(all_items)} pricing records")
        return all_items
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pricing data: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Response content: {e.response.text}")
        return []

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
        instance_details = data.get('attributesByOffer', {})
        print(f"Retrieved {len(instance_details)} instance details")
        return instance_details
    except requests.exceptions.RequestException as e:
        print(f"Error fetching instance details: {str(e)}")
        if hasattr(response, 'text'):
            print(f"Response content: {response.text}")
        return {}

def parse_gpu_info(gpu_string: str) -> Dict:
    """Parse GPU information from format like '1X V100' or '8x A100 (NVlink)'."""
    if not gpu_string:
        return None

    try:
        # Handle fractional GPUs (like "1/2X A10")
        if '/' in gpu_string:
            parts = gpu_string.split('X ', 1)
            if len(parts) != 2:
                return None
            fraction = float(eval(parts[0]))  # safely evaluate fraction
            gpu_type = parts[1].strip()
            return {
                'gpu_type': gpu_type,
                'gpu_count': fraction
            }

        # Handle standard format and formats with parentheses
        match = re.match(r'(\d+)(?:x|X)\s+(.+?)(?:\s+\(.*\))?$', gpu_string)
        if match:
            count = int(match.group(1))
            gpu_type = match.group(2).strip()
            return {
                'gpu_type': gpu_type,
                'gpu_count': count
            }

        return None
    except (ValueError, AttributeError) as e:
        print(f"Error parsing GPU string '{gpu_string}': {str(e)}")
        return None

def normalize_instance_name(name: str) -> str:
    """Normalize instance name to match between pricing and details APIs."""
    # Remove common prefixes and suffixes
    name = name.replace('Standard_', '')
    name = name.replace('linux-', '')
    name = name.replace('-standard', '')

    # Convert to lowercase for case-insensitive matching
    name = name.lower()

    # Remove 'v' from version numbers (e.g., 'v5' -> '5')
    name = re.sub(r'v(\d)', r'\1', name)

    # Remove underscore and dash variations
    name = name.replace('_', '')
    name = name.replace('-', '')

    return name

def get_gpu_instances(region: str) -> List[Dict]:
    """Get all VM sizes with GPUs and their pricing information."""
    print("Fetching pricing data...")
    pricing_data = get_vm_pricing_data(region)

    print("\nFetching instance details...")
    instance_details = get_instance_details()

    if not pricing_data or not instance_details:
        print("\nMissing required data:")
        print(f"Pricing data: {'Present' if pricing_data else 'Missing'}")
        print(f"Instance details: {'Present' if instance_details else 'Missing'}")
        return []

    # Create pricing lookup dictionary with normalized names
    pricing_lookup = {}
    for item in pricing_data:
        sku_name = item.get('armSkuName', '')
        if not sku_name:
            continue

        normalized_name = normalize_instance_name(sku_name)
        if normalized_name not in pricing_lookup:
            pricing_lookup[normalized_name] = {
                'on_demand': 0.0,
                'spot': 0.0,
                'original_name': item.get('armSkuName', '')  # Keep original name for reference
            }

        # Update pricing based on the type
        if 'Spot' in item.get('skuName', ''):
            pricing_lookup[normalized_name]['spot'] = item.get('retailPrice', 0.0)
        else:
            pricing_lookup[normalized_name]['on_demand'] = item.get('retailPrice', 0.0)

    # Process instances with GPU information
    gpu_instances = []
    print("\nProcessing GPU instances...")

    for instance_key, details in instance_details.items():
        if 'gpu' not in details:
            continue

        gpu_info = parse_gpu_info(details['gpu'])
        if not gpu_info:
            continue

        normalized_name = normalize_instance_name(instance_key)

        # Try to find pricing using different name variations
        pricing = None
        name_variations = [
            normalized_name,
            f"standard{normalized_name}",
            normalized_name.replace('r', ''),  # Try without memory optimized 'r' suffix
            normalized_name.replace('s', '')   # Try without SSD suffix
        ]

        for variant in name_variations:
            if variant in pricing_lookup:
                pricing = pricing_lookup[variant]
                break

        if pricing and pricing['on_demand'] > 0.0:  # Only include instances with pricing data
            instance = {
                'Instance Type': details.get('instanceName', pricing['original_name']),
                'vCPUs': details.get('cores', 0),
                'Memory (GB)': details.get('ram', 0),
                'GPU Type': gpu_info['gpu_type'],
                'GPU Count': gpu_info['gpu_count'],
                'On-Demand Price ($/hr)': pricing['on_demand'],
                'Spot Price ($/hr)': pricing['spot'],
                'Region': region
            }
            gpu_instances.append(instance)

    print(f"\nFound {len(gpu_instances)} complete GPU instances with pricing")
    return gpu_instances

def standardize_instance_data(instance: Dict) -> Dict:
    """Standardize instance data format."""
    return {
        'Provider': 'Azure',
        'Region': instance['Region'],
        'Instance Type': instance['Instance Type'],
        'vCPUs': instance['vCPUs'],
        'Memory (GB)': instance['Memory (GB)'],
        'GPU Type': instance['GPU Type'],
        'GPU Count': instance['GPU Count'],
        'On-Demand Price ($/hr)': instance['On-Demand Price ($/hr)'],
        'Spot Price ($/hr)': instance['Spot Price ($/hr)']
    }

def get_standardized_gpu_instances(region: str) -> List[Dict]:
    """Get standardized GPU instance information for the specified region."""
    print("Fetching GPU instance types...")
    gpu_instances = get_gpu_instances(region)

    if not gpu_instances:
        print("No GPU instances found or error occurred.")
        return []

    print(f"Found {len(gpu_instances)} GPU instance types")

    print("Standardizing instance data...")
    standardized_instances = []
    for instance in gpu_instances:
        standardized = standardize_instance_data(instance)
        standardized_instances.append(standardized)

    return standardized_instances

def main():
    # Default region if running standalone
    region = 'china-east2'  # Changed default to China region for testing

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
