import json
import os
from urllib.parse import urlparse, urlunparse

import requests


def run_scraper_with_urls(json_file_path):
    """
    Reads a JSON file to get LinkedIn profile URLs, cleans them,
    and then triggers a BrightData scraper with those URLs.

    :param json_file_path: Path to the JSON file containing profile URLs.
    """
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{json_file_path}' was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from the file '{json_file_path}'.")
        return

    profiles = data.get('data', [{}])[0].get('profiles', [])
    if not profiles:
        print("No profiles found in the JSON file.")
        return

    urls_to_scrape = []
    for profile in profiles:
        if 'profile_url' in profile and profile['profile_url']:
            parsed_url = urlparse(profile['profile_url'])
            # Remove query parameters from the URL
            clean_url = urlunparse(parsed_url._replace(query=''))
            urls_to_scrape.append({"url": clean_url})

    if not urls_to_scrape:
        print("No valid profile URLs found to scrape.")
        return

    # Your BrightData API details
    # It's recommended to use environment variables for sensitive data like API keys.
    auth_token = os.environ.get("BRIGHTDATA_AUTH_TOKEN", "198c120e0bbcdff6aff623aab8d48779fb974cc1bc0709351c0956e37540667b")
    dataset_id = "gd_l1viktl72bvl7bjuj0"
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    api_url = f"https://api.brightdata.com/datasets/v3/trigger?dataset_id={dataset_id}&include_errors=true"

    try:
        response = requests.post(api_url, headers=headers, json=urls_to_scrape)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        
        print("API call successful.")
        print("Response:", response.json())

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the API request: {e}")


if __name__ == "__main__":
    run_scraper_with_urls('./companies/civeo.json')