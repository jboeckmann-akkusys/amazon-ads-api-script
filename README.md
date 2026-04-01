# Amazon Ads API Script

Automated script to pause non close-match auto-targets in Amazon Sponsored Products.

## Overview

This script:
- Retrieves all Sponsored Products auto-targets
- Identifies targets that are NOT "close-match" (loose-match, substitutes, complements)
- Pauses those targets (dry-run by default, use `--apply` to apply changes)

## Prerequisites

- Python 3.8+
- Amazon Ads API credentials

## Setup

### 1. Clone or download this repository

```bash
git clone <repository-url>
cd amazon-ads-api-script
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# OAuth credentials (from Amazon Advertising API developer console)
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
REFRESH_TOKEN=your_refresh_token_here

# Your Amazon Ads profile ID
PROFILE_ID=your_profile_id_here
```

### Getting Credentials

1. Register at [Amazon Advertising API](https://advertising.amazon.com/)
2. Create an application in the Developer Console
3. Get your `CLIENT_ID` and `CLIENT_SECRET`
4. Obtain a `REFRESH_TOKEN` through OAuth authorization
5. Find your `PROFILE_ID` in your Amazon Ads account settings

## Usage

### Dry-run (default)

Preview which targets would be paused without making any changes:

```bash
python script.py
```

Sample output:
```
2024-01-15 10:30:00 - INFO - Starting script (dry-run mode: True)
2024-01-15 10:30:00 - INFO - Fetching all targets...
2024-01-15 10:30:05 - INFO - Fetched 100 targets (total so far: 100)
2024-01-15 10:30:05 - INFO - 150 targets retrieved
2024-01-15 10:30:05 - INFO - Filtering auto-targets to pause...
2024-01-15 10:30:05 - INFO - 25 targets to pause
2024-01-15 10:30:05 - INFO - Targets to pause:
2024-01-15 10:30:05 - INFO -   - Target abc123 (Campaign: campaign1, AdGroup: adgroup1) - Types: ['queryBroadRelMatches']
2024-01-15 10:30:05 - INFO - Dry-run mode: no changes applied. Use --apply to apply changes.
```

### Apply changes

To actually pause the targets:

```bash
python script.py --apply
```

## Target Types

### Close-match (NOT paused)
- `queryBroadMatches` - Broad match (close)
- `queryPhraseMatches` - Phrase match (close)
- `queryExactMatches` - Exact match (close)
- `queryHighRelMatches` - High relevance (close)

### Non close-match (WILL be paused)
- `queryBroadRelMatches` - Loose-match
- `asinSubstituteRelated` - Substitutes
- `asinAccessoryRelated` - Complements

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CLIENT_ID` | OAuth client ID from Amazon |
| `CLIENT_SECRET` | OAuth client secret |
| `REFRESH_TOKEN` | OAuth refresh token |
| `PROFILE_ID` | Amazon Ads profile ID |

## Marketplace

This script is configured for the **EU** marketplace. To change to another region, edit `script.py` and update:

```python
marketplace=Marketplaces.EU  # Change to: NA, FE, DE, UK, etc.
```

## Logging

Logs are output to stdout with timestamps. To save logs to a file:

```bash
python script.py --apply > script.log 2>&1
```

## Troubleshooting

### "Missing required environment variables"
Ensure your `.env` file exists and contains all four required variables.

### "Import could not be resolved"
Run `pip install -r requirements.txt` to install dependencies.

### API errors
- Check your credentials are valid
- Ensure your API application has appropriate permissions
- Verify your profile ID is correct