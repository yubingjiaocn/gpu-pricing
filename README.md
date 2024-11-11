# GPU Pricing Comparison Tool

A Python tool that fetches and compares GPU instance pricing across major cloud service providers (CSPs) including AWS, Azure, GCP, Alibaba Cloud, and Tencent Cloud. The tool supports both global and China regions, providing both on-demand and spot pricing information.

## Features

- Fetches GPU instance pricing from multiple cloud providers
- Supports both global and China regions
- Provides both on-demand and spot pricing (where available)
- Standardized output format across all providers
- Comprehensive instance details including vCPUs, Memory, GPU Type, and Count

| Cloud Provider  | Authentication Required | Spot Pricing Support |
|----------------|:----------------------:|:-------------------:|
| AWS            | Yes                    | Yes*                 |
| Azure          | No                     | Yes                 |
| GCP            | Yes                    | Yes**                |
| Alibaba Cloud  | No                     | No                  |
| Tencent Cloud  | No                     | No                  |

\* Provides 90-days average price
\*\* GCP uses preemptible VM pricing instead of spot pricing

## Prerequisites

### Python Dependencies
```bash
pip install -r requirements.txt
```

### Cloud Provider Authentication

#### AWS
- Requires AWS credentials configured
- Set up AWS credentials in `~/.aws/credentials` or via environment variables:
  ```bash
  export AWS_ACCESS_KEY_ID="your_access_key"
  export AWS_SECRET_ACCESS_KEY="your_secret_key"
  ```
- Requires `pricing:GetProducts` and `ec2:DescribeSpotPriceHistory` permission

#### Azure
- No authentication required
- Uses public retail prices API

#### Google Cloud Platform
- Requires GCP project ID and authentication
- Requires Virtual Machines API and Billings API enabled
- Set up environment variables:
  ```bash
  export GOOGLE_CLOUD_PROJECT="your_project_id"
  ```
- Authenticate using one of these methods:
  1. Service account key file:
     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
     ```
  2. gcloud CLI:
     ```bash
     gcloud auth application-default login
     ```

#### Alibaba Cloud
- No authentication required
- Uses public JSON file

#### Tencent Cloud
- No authentication required
- Uses public workbench API

## Usage

To fetch pricing from all providers:
```bash
python fetch_all.py
```

To fetch pricing from a specific provider:
```bash
python aws.py    # For AWS
python azure.py  # For Azure
python gcp.py    # For GCP
python ali.py    # For Alibaba Cloud
python tencent.py # For Tencent Cloud
```

## Modifying Regions

To fetch prices from different regions, modify the `provider_regions` list in `fetch_all.py`:

```python
provider_regions = [
    ('AWS', 'us-west-2'),
    ('Azure', 'westus2'),
    ('GCP', 'us-west1'),
    ('Ali', 'us-west-1'),
    ('Tencent', 'na-siliconvalley-2')
]
```

### Region Documentation

For a complete list of available region codes, refer to each provider's official documentation:

- AWS Region Codes: [AWS Regions and Endpoints](https://docs.aws.amazon.com/general/latest/gr/rande.html#regional-endpoints)
- Azure Region Codes: [Azure Region Names](https://learn.microsoft.com/en-us/azure/virtual-machines/regions#region-names)
- GCP Region Codes: [GCP Region List](https://cloud.google.com/compute/docs/regions-zones#available)
- Alibaba Cloud Region Codes: [Alibaba Region IDs](https://www.alibabacloud.com/help/en/elastic-compute-service/latest/regions-and-zones#concept-uxw-rt4-xdb)
- Tencent Cloud Region Codes: [Tencent Region List](https://www.tencentcloud.com/document/api/213/15692)

## Output Format

The tool generates a standardized CSV file with the following columns:
- Provider: Cloud service provider name
- Region: Data center region
- Instance Type: Instance type identifier
- vCPUs: Number of virtual CPUs
- Memory (GB): RAM in gigabytes
- GPU Type: Model of GPU
- GPU Count: Number of GPUs
- On-Demand Price ($/hr): Hourly price for on-demand instances
- Spot Price ($/hr): Average hourly price for spot instances (where available)

## Notes

- Pricing data is fetched in real-time and may vary
- Spot prices are typically averages over a period (where available)
- Some regions or instance types may not be available
- Rate limiting is implemented to avoid API throttling
- China region support varies by provider

## Disclaimer

This project is proudly developed with the assistance of AI technology. Over 90% of the codebase was written through collaboration with AI assistants:
- Cline: A software engineering focused AI that helped with core implementation and technical documentation
- Claude: An AI assistant that contributed to architecture design and code refinements

This AI-driven development approach allowed for rapid implementation while maintaining high code quality and comprehensive documentation.
