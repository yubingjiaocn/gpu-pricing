import requests
import json
import os
from datetime import datetime

    # GraphQL query to get GPU instances from all providers
query_1 = """
query {
    flavor_prices (
        gpu_number: [1, 2, 4, 8, 16],
        license: "linux"
"""

query_3 = """
    )
    {
    flavor {
        name
        slug
        gpu_number
        gpu_model
        cpu_number
        ram
        is_deprecated
    }
    currency
    hourly
    }
}
"""

def run_graphql_query(api_token, provider, zone):
    # GraphQL endpoint
    url = "https://graphql.cloud-mercato.com/graphql"

    # Set up headers with authorization token
    headers = {
        'Authorization': f'Token {api_token}',
        'Content-Type': 'application/json'
    }

    try:
        query_2 = f"""
            provider: "{provider}"
            zone: "{zone}"
        """

        query = query_1 + query_2 + query_3

        query_stripped = ''.join(query.splitlines())
        # Make the request with authorization headers
        response = requests.post(url, json={'query': query_stripped}, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Parse the response
        data = response.json()

        if 'errors' in data:
            print("GraphQL Errors:", data['errors'])
            return

        # Process and display results
        instances = data["data"]['flavor_prices']

        for instance in instances:
            flavor = instance['flavor']
            name = flavor['name']
            slug = flavor['slug']
            gpu_model = flavor['gpu_model'] or 'N/A'
            gpu_count = flavor['gpu_number']
            vcpus = flavor['cpu_number']
            memory = flavor['ram']
            # Format the output line
            hourly = instance['hourly'] or 0

            print(f"{name:<25} {gpu_model:<20} {gpu_count:<10} {vcpus:<8} {memory:<12} {hourly:<12}")

    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    # Try to get token from environment variable
    api_token = os.getenv('CLOUD_MERCATO_TOKEN')

    # If not in environment, prompt for token
    if not api_token:
        api_token = input("Please enter your Cloud Mercato API token: ")

    if not api_token:
        print("Error: API token is required")
        print("You can either:")
        print("1. Set it as an environment variable: export CLOUD_MERCATO_TOKEN='your_token'")
        print("2. Enter it when prompted")
        exit(1)

    run_graphql_query(api_token, "aws", "us-west-2")
