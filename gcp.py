import os
import json
import pandas as pd
import csv
from google.cloud import compute_v1
from google.cloud import billing_v1
from typing import Dict, List

def get_instance_types_with_gpu() -> List[Dict]:
    """Fetch all Compute Engine instance types with GPUs."""
    machine_types_client = compute_v1.MachineTypesClient()

    # Use us-west1 region
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")

    zone = 'us-west1-b'
    instance_types = []

    try:
        # Get all machine types in the zone
        request = compute_v1.ListMachineTypesRequest(
            project=project_id,
            zone=zone
        )

        machine_types_list = machine_types_client.list(request=request)

        for machine in machine_types_list:
            # Check if the machine type supports GPUs
            if hasattr(machine, 'accelerators') and machine.accelerators:
                for accelerator in machine.accelerators:
                    # Extract GPU type from the full path
                    gpu_type = accelerator.guest_accelerator_type.split('/')[-1]
                    instance_types.append({
                        'Instance Type': machine.name,
                        'vCPUs': machine.guest_cpus,
                        'Memory (GiB)': machine.memory_mb / 1024,  # Convert MB to GiB
                        'GPU Type': gpu_type,
                        'GPU Count': accelerator.guest_accelerator_count,
                        'Zone': zone
                    })

    except Exception as e:
        print(f"Error fetching instance types: {str(e)}")
        return []

    return instance_types

def get_pricing_info(instance_type: str, gpu_type: str, gpu_count: int) -> tuple:
    """Get on-demand and spot pricing for an instance type."""
    billing_client = billing_v1.CloudCatalogClient()
    service_name = "services/6F81-5844-456A"  # Compute Engine service ID

    try:
        # Get all SKUs
        request = billing_v1.ListSkusRequest(
            parent=service_name
        )

        on_demand_price = 0.0
        spot_price = 0.0

        skus = billing_client.list_skus(request)

        # Find instance prices (both on-demand and spot)
        instance_keywords = instance_type.lower().split('-')
        for sku in skus:
            if (all(x in sku.description.lower() for x in instance_keywords) and
                'us-west1' in str(sku.service_regions)):

                # Check if this is spot or on-demand pricing
                is_spot = 'Spot' in sku.description or 'spot' in str(sku.category)

                if is_spot:
                    # Get spot price
                    pricing_info = sku.pricing_info[0]
                    for tier in pricing_info.pricing_expression.tiered_rates:
                        spot_price = tier.unit_price.units + tier.unit_price.nanos / 1e9
                        break
                else:
                    # Get on-demand price
                    pricing_info = sku.pricing_info[0]
                    for tier in pricing_info.pricing_expression.tiered_rates:
                        on_demand_price = tier.unit_price.units + tier.unit_price.nanos / 1e9
                        break

        # Find GPU prices (both on-demand and spot)
        gpu_type_search = gpu_type.replace('nvidia-', '').replace('-', ' ')  # Convert nvidia-tesla-a100 to tesla a100
        for sku in skus:
            if ('gpu' in sku.description.lower() and
                gpu_type_search.lower() in sku.description.lower() and
                'us-west1' in str(sku.service_regions)):

                # Check if this is spot or on-demand pricing
                is_spot = 'Spot' in sku.description or 'spot' in str(sku.category)

                pricing_info = sku.pricing_info[0]
                for tier in pricing_info.pricing_expression.tiered_rates:
                    gpu_price = (tier.unit_price.units + tier.unit_price.nanos / 1e9) * gpu_count
                    if is_spot:
                        spot_price += gpu_price
                    else:
                        on_demand_price += gpu_price
                    break

        return on_demand_price, spot_price

    except Exception as e:
        print(f"Error getting pricing for {instance_type}: {str(e)}")
        return 0.0, 0.0

def main():
    # Verify environment variable
    if not os.getenv('GOOGLE_CLOUD_PROJECT'):
        print("Error: GOOGLE_CLOUD_PROJECT environment variable must be set")
        return

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
        gpu_type = instance['GPU Type']
        gpu_count = instance['GPU Count']
        print(f"Processing {instance_type}...")

        # Get pricing
        on_demand, spot = get_pricing_info(instance_type, gpu_type, gpu_count)
        instance['On-Demand Price ($/hr)'] = on_demand
        instance['Spot Price ($/hr)'] = spot

    # Create DataFrame and save to CSV
    df = pd.DataFrame(gpu_instances)
    df = df[[
        'Instance Type',
        'vCPUs',
        'Memory (GiB)',
        'GPU Type',
        'GPU Count',
        'On-Demand Price ($/hr)',
        'Spot Price ($/hr)'
    ]]

    # Sort by instance type
    df.sort_values('Instance Type', inplace=True)

    # Format numeric columns
    df['Memory (GiB)'] = df['Memory (GiB)'].map('{:.1f}'.format)
    df['On-Demand Price ($/hr)'] = df['On-Demand Price ($/hr)'].map('{:.4f}'.format)
    df['Spot Price ($/hr)'] = df['Spot Price ($/hr)'].map('{:.4f}'.format)

    # Save to CSV
    df.to_csv('gcp.csv',
              index=False,
              sep=',',
              quoting=csv.QUOTE_MINIMAL)

    print("\nResults saved to gcp.csv")

    # Display first few rows
    print("\nFirst few rows of the data:")
    print(df.head().to_string())

if __name__ == "__main__":
    main()
