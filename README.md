# Amazon Ads API Script

Automated script to pause non close-match auto-targets in Amazon Sponsored Products.

## Overview

This script:
- Retrieves all Sponsored Products auto-targets from Amazon Ads API
- Identifies ENABLED targets that are NOT "close-match" (loose-match, substitutes, complements)
- Pauses only the targets that need updating (idempotent - safe for frequent runs)
- Runs automatically every 5 minutes via GitHub Actions or Render.com Cron Job

## Features

- **Delta-based filtering**: Only updates targets that are ENABLED and need pausing
- **Early exit**: Skips API calls if no targets need updating
- **Batch processing**: 100 targets per batch with rate limiting
- **Idempotent**: Safe to run frequently - won't re-pause already paused targets
- **GitHub Actions**: Automated execution every 5 minutes
- **Render.com Cron Job**: Also compatible with Render.com for hosting

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
4. Obtain a `REFRESH_TOKEN` through OAuth authorization (run `python oauth_helper.py --marketplace de`)
5. Find your `PROFILE_ID` in your Amazon Ads account settings

## Usage

### Dry-run (default)

Preview which targets would be paused without making any changes:

```bash
python script.py
```

### Apply changes

To actually pause the targets:

```bash
python script.py --apply
```

### Limit number of updates

Use `--max-updates N` to limit how many targets are updated in a run:

```bash
python script.py --apply --max-updates 100
```

### Test mode

Use `--test N` for debugging - updates only N targets:

```bash
python script.py --apply --test 5
```

## Command Line Options

| Flag | Description | Default |
|------|-------------|---------|
| `--apply` | Apply changes (without this, runs in dry-run mode) | dry-run |
| `--test N` | Test mode: only update N targets for debugging | 0 (disabled) |
| `--max-updates N` | Limit total number of targets to update | 0 (disabled) |

## Target Types

### Close-match (NOT paused - kept active)
- `QUERY_HIGH_REL_MATCHES` - High relevance (close match)

### Non close-match (WILL be paused)
- `QUERY_BROAD_REL_MATCHES` - Loose-match
- `ASIN_SUBSTITUTE_RELATED` - Substitutes
- `ASIN_ACCESSORY_RELATED` - Complements

## Filtering Logic

The script only targets targets that meet ALL criteria:
1. **State = ENABLED** (already paused targets are skipped)
2. **Expression type** is one of: loose-match, substitutes, complements

This ensures:
- No unnecessary API calls for already-paused targets
- Delta detection - only newly reactivated targets are updated
- Safe for frequent runs (idempotent)

## Deployment Options

### GitHub Actions

The script runs automatically via GitHub Actions:
- **Schedule**: Every 5 minutes (`*/5 * * * *`)
- **Concurrency**: Prevents overlapping runs
- **Mode**: Always runs in apply mode (`--apply`)

### Render.com Cron Job

The script is also compatible with Render.com Cron Jobs:

1. Create a new Web Service on Render.com
2. Set Build Command: `pip install -r requirements.txt`
3. Set Start Command: `python script.py --apply`
4. Add environment variables in Render dashboard:
   - `CLIENT_ID`
   - `CLIENT_SECRET`
   - `REFRESH_TOKEN`
   - `PROFILE_ID`
5. Configure a Cron Schedule (e.g., every 15 minutes)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CLIENT_ID` | OAuth client ID from Amazon |
| `CLIENT_SECRET` | OAuth client secret |
| `REFRESH_TOKEN` | OAuth refresh token |
| `PROFILE_ID` | Amazon Ads profile ID |

## Marketplace

This script is configured for the **EU** marketplace (Germany). The library handles the marketplace automatically based on credentials.

## Logging

Logs are output to stdout with timestamps. To save logs to a file:

```bash
python script.py --apply > script.log 2>&1
```

## Troubleshooting

### "Missing required environment variables"
Ensure your environment variables are set (`.env` file or system environment).

### "Import could not be resolved"
Run `pip install -r requirements.txt` to install dependencies.

### API errors
- Check your credentials are valid
- Ensure your API application has appropriate permissions
- Verify your profile ID is correct
- If refresh token expires, run `python oauth_helper.py --marketplace de` to get a new one

### Targets not pausing in UI
- The API state is authoritative - if it says PAUSED, the backend is correct
- Amazon UI may have 5-30 minute delay in reflecting API changes
- Check parent Campaign/Ad Group status - if they're paused, targeting may appear active

## Files

```
amazon-ads-api-script/
├── script.py                      # Main automation script
├── oauth_helper.py               # OAuth authorization helper
├── requirements.txt              # Python dependencies
├── .env.example                 # Environment variable template
└── .github/workflows/
    └── amazon-ads.yml           # GitHub Actions workflow
```
