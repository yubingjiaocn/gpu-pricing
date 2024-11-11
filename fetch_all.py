import pandas as pd
import aws
import azure
import gcp
import ali
import tencent
from typing import List, Dict, Tuple
import importlib
import time

def get_provider_module(provider: str):
    """Map provider names to their respective modules."""
    provider_map = {
        'aws': aws,
        'azure': azure,
        'gcp': gcp,
        'ali': ali,
        'tencent': tencent
    }
    return provider_map.get(provider.lower())

def fetch_prices(provider_regions: List[Tuple[str, str]]) -> pd.DataFrame:
    """
    Fetch GPU prices for given provider-region pairs.
    Args:
        provider_regions: List of tuples containing (provider, region) pairs
    Returns:
        DataFrame containing combined pricing information
    """
    all_data = []

    for provider, region in provider_regions:
        print(f"\nFetching prices for {provider} in region {region}...")
        module = get_provider_module(provider)

        if not module:
            print(f"Unsupported provider: {provider}")
            continue

        try:
            # Get standardized GPU instances for the provider in the specified region
            instances = module.get_standardized_gpu_instances(region)

            if not instances:
                print(f"No instances found for {provider} in {region}")
                continue

            all_data.extend(instances)
            print(f"Successfully processed {len(instances)} instances for {provider}")

        except Exception as e:
            print(f"Error fetching data for {provider}: {str(e)}")
            continue

    if not all_data:
        print("No data collected from any provider")
        return pd.DataFrame()

    # Create DataFrame with standardized columns
    df = pd.DataFrame(all_data)

    # Ensure all required columns exist
    required_columns = [
        'Provider',
        'Region',
        'Instance Type',
        'vCPUs',
        'Memory (GB)',
        'GPU Type',
        'GPU Count',
        'On-Demand Price ($/hr)',
        'Spot Price ($/hr)'
    ]

    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    # Select and order columns
    df = df[required_columns]

    return df

def main():
    # Provider-region pairs to fetch data from
    provider_regions = [
        ('AWS', 'us-west-2'),
        ('Azure', 'westus2'),
        ('GCP', 'us-west1'),
        ('Ali', 'us-west-1'),
        ('Tencent', 'na-siliconvalley')
    ]

    print("Fetching GPU pricing information from multiple providers...")
    df = fetch_prices(provider_regions)

    if df.empty:
        print("No data collected. Exiting...")
        return

    # Sort by provider and instance type
    df = df.sort_values(['Provider', 'Instance Type'])

    # Format numeric columns
    df['Memory (GB)'] = pd.to_numeric(df['Memory (GB)'], errors='coerce').fillna(0).map('{:.1f}'.format)
    df['On-Demand Price ($/hr)'] = pd.to_numeric(df['On-Demand Price ($/hr)'], errors='coerce').fillna(0).map('{:.4f}'.format)
    df['Spot Price ($/hr)'] = pd.to_numeric(df['Spot Price ($/hr)'], errors='coerce').fillna(0).map('{:.4f}'.format)

    # Save to CSV
    output_file = 'gpu_pricing_comparison.csv'
    df.to_csv(output_file, index=False)

    print(f"\nResults saved to {output_file}")
    print("\nFirst few rows of the data:")
    print(df.head().to_string())

if __name__ == "__main__":
    main()
