"""
OAuth Helper Script for Amazon Ads API
Generates authorization URL, exchanges code for tokens, saves refresh token to .env.local
"""

import os
import sys
import requests
from urllib.parse import urlencode

# Try to load existing credentials from .env.local
def load_credentials():
    """Load CLIENT_ID and CLIENT_SECRET from .env.local"""
    env_path = ".env.local"
    
    if not os.path.exists(env_path):
        print(f"Error: {env_path} not found. Please create it with CLIENT_ID and CLIENT_SECRET.")
        sys.exit(1)
    
    # Parse .env.local manually
    credentials = {}
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                credentials[key.strip()] = value.strip()
    
    client_id = credentials.get("CLIENT_ID")
    client_secret = credentials.get("CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Error: CLIENT_ID and CLIENT_SECRET not found in .env.local")
        sys.exit(1)
    
    return client_id, client_secret


def generate_authorization_url(client_id):
    """Generate the Login with Amazon authorization URL"""
    base_url = "https://www.amazon.com/ap/oa"
    
    params = {
        "client_id": client_id,
        "scope": "advertising::campaign_management",
        "response_type": "code",
        "redirect_uri": "https://localhost"
    }
    
    return f"{base_url}?{urlencode(params)}"


def exchange_code_for_token(client_id, client_secret, auth_code):
    """Exchange authorization code for access_token and refresh_token"""
    token_url = "https://api.amazon.com/auth/o2/token"
    
    payload = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "https://localhost"
    }
    
    print("\nExchanging authorization code for tokens...")
    
    try:
        response = requests.post(token_url, data=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: Token exchange failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed - {e}")
        return None


def save_refresh_token(refresh_token):
    """Save refresh_token to .env.local, preserving other values"""
    env_path = ".env.local"
    
    # Read existing content
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    # Find and update REFRESH_TOKEN line, or add it
    found = False
    new_lines = []
    
    for line in lines:
        if line.strip().startswith("REFRESH_TOKEN="):
            new_lines.append(f"REFRESH_TOKEN={refresh_token}\n")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        # Add after CLIENT_SECRET line
        temp_lines = []
        for line in new_lines:
            temp_lines.append(line)
            if line.strip().startswith("CLIENT_SECRET="):
                temp_lines.append(f"REFRESH_TOKEN={refresh_token}\n")
        new_lines = temp_lines
    
    # Write back
    with open(env_path, "w") as f:
        f.writelines(new_lines)
    
    print(f"\n[OK] Saved refresh_token to {env_path}")


def main():
    print("=" * 60)
    print("Amazon Ads API - OAuth Authorization Helper")
    print("=" * 60)
    
    # Step 1: Load credentials
    print("\n[Step 1] Loading credentials from .env.local...")
    client_id, client_secret = load_credentials()
    print(f"  CLIENT_ID: {client_id[:20]}...")
    
    # Step 2: Generate authorization URL
    print("\n[Step 2] Generating authorization URL...")
    auth_url = generate_authorization_url(client_id)
    
    print("\n" + "=" * 60)
    print("AUTHORIZATION URL:")
    print("=" * 60)
    print(auth_url)
    print("=" * 60)
    
    print("\n[Step 3] Instructions:")
    print("  1. Copy the URL above and open it in your browser")
    print("  2. Log in with your Amazon account")
    print("  3. Grant permission for 'Advertising API'")
    print("  4. You will be redirected to: https://localhost?code=...")
    print("  5. Copy the 'code' parameter value from the URL")
    print("-" * 60)
    
    # Step 4: Get authorization code from user
    auth_code = input("\nPaste the authorization code here: ").strip()
    
    if not auth_code:
        print("Error: No code provided")
        sys.exit(1)
    
    # Step 5: Exchange code for tokens
    print("\n[Step 4] Exchanging code for tokens...")
    result = exchange_code_for_token(client_id, client_secret, auth_code)
    
    if result:
        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")
        
        print("\n" + "=" * 60)
        print("TOKEN EXCHANGE SUCCESSFUL!")
        print("=" * 60)
        
        print(f"\nAccess Token (short-lived, ~1 hour):")
        print(f"  {access_token}")
        
        print(f"\n{'=' * 60}")
        print(f"REFRESH TOKEN (long-lived, save this!):")
        print(f"{'=' * 60}")
        print(f"  {refresh_token}")
        print(f"{'=' * 60}")
        
        # Step 6: Save refresh token
        print("\n[Step 5] Saving refresh token to .env.local...")
        save_refresh_token(refresh_token)
        
        print("\n[OK] OAuth flow complete!")
        print("  You can now use REFRESH_TOKEN in your scripts.")
        
    else:
        print("\n[ERROR] Token exchange failed. Please try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()