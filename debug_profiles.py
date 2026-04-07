"""
Debug script to test Amazon Ads API authentication.
Tests CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN and retrieves available profiles.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv(".env.local")

# Get credentials from environment
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")


def get_access_token():
    """
    Exchange refresh_token for access_token.

    Endpoint: https://api.amazon.com/auth/o2/token
    Method: POST with form data

    Returns:
        access_token string if successful, None if failed
    """
    url = "https://api.amazon.com/auth/o2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    print("\n" + "=" * 50)
    print("STEP 1: Getting access token")
    print("=" * 50)
    print(f"Endpoint: {url}")
    print(f"Client ID: {CLIENT_ID[:20]}..." if CLIENT_ID else "Client ID: NOT SET")

    try:
        response = requests.post(url, data=data)
        print(f"Response Status Code: {response.status_code}")

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            print(f"Token Type: {token_data.get('token_type')}")
            print(f"Expires In: {token_data.get('expires_in')} seconds")
            print(f"Access Token Length: {len(access_token) if access_token else 0}")
            print("Access Token: OBTAINED SUCCESSFULLY")
            return access_token
        else:
            print(f"Error: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request Failed: {e}")
        return None


def get_profiles(access_token):
    """
    Fetch available advertising profiles.

    Endpoint: https://advertising-api-eu.amazon.com/v2/profiles
    Method: GET with headers

    Returns:
        JSON response if successful, None if failed
    """
    url = "https://advertising-api-eu.amazon.com/v2/profiles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": CLIENT_ID,
        "Content-Type": "application/json"
    }

    print("\n" + "=" * 50)
    print("STEP 2: Getting profiles")
    print("=" * 50)
    print(f"Endpoint: {url}")
    print(f"Authorization: Bearer {access_token[:20]}..." if access_token else "Authorization: NOT SET")
    print(f"ClientId: {CLIENT_ID[:20]}..." if CLIENT_ID else "ClientId: NOT SET")

    try:
        response = requests.get(url, headers=headers)
        print(f"Response Status Code: {response.status_code}")

        if response.status_code == 200:
            profiles = response.json()
            print(f"Number of profiles: {len(profiles)}")

            if profiles:
                print("\nAvailable Profiles:")
                print("-" * 40)
                for i, profile in enumerate(profiles, 1):
                    profile_id = profile.get("profileId", "N/A")
                    country_code = profile.get("countryCode", "N/A")
                    profile_type = profile.get("profileType", "N/A")
                    name = profile.get("name", "N/A")
                    print(f"  {i}. Profile ID: {profile_id}")
                    print(f"     Country: {country_code}")
                    print(f"     Type: {profile_type}")
                    print(f"     Name: {name}")
            else:
                print("Response is empty (no profiles found)")

            return profiles

        elif response.status_code == 401:
            print("\n!!! AUTHENTICATION ERROR !!!")
            print("The access token was rejected.")
            print(f"Details: {response.text}")
            return None

        elif response.status_code == 403:
            print("\n!!! AUTHORIZATION ERROR !!!")
            print("The client is not authorized to access this resource.")
            print(f"Details: {response.text}")
            return None

        else:
            print(f"\n!!! UNEXPECTED ERROR !!!")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request Failed: {e}")
        return None


def main():
    """Main function to run the debug script."""
    print("=" * 50)
    print("Amazon Ads API - Debug Script")
    print("=" * 50)

    # Check if credentials are loaded
    print("\nCredentials Check:")
    print(f"  CLIENT_ID: {'SET' if CLIENT_ID else 'MISSING'}")
    print(f"  CLIENT_SECRET: {'SET' if CLIENT_SECRET else 'MISSING'}")
    print(f"  REFRESH_TOKEN: {'SET' if REFRESH_TOKEN else 'MISSING'}")

    # Validate credentials exist
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("\nERROR: Missing required environment variables!")
        print("Please check .env.local file")
        return

    # Step 1: Get access token
    access_token = get_access_token()

    if not access_token:
        print("\n!!! FAILED TO OBTAIN ACCESS TOKEN !!!")
        print("Check your CLIENT_ID, CLIENT_SECRET, and REFRESH_TOKEN")
        print("\nCommon causes:")
        print("  - CLIENT_ID or CLIENT_SECRET is incorrect")
        print("  - REFRESH_TOKEN has expired")
        print("  - App not approved for Amazon Ads API")
        return

    # Step 2: Get profiles
    profiles = get_profiles(access_token)

    if profiles is None:
        print("\n!!! FAILED TO RETRIEVE PROFILES !!!")
        print("\nPossible causes:")
        print("  - CLIENT_ID not authorized for Amazon Ads API")
        print("  - Need to use different API endpoint (US vs EU)")
        print("  - Token scope does not include advertising")
        return

    print("\n" + "=" * 50)
    print("DEBUG COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()