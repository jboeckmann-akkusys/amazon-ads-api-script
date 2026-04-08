import argparse
import logging
import os
import sys
import json
import time
import subprocess

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_github_issue(title: str, body: str):
    """Create a GitHub issue using gh CLI (for GitHub Actions)."""
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            logger.info(f"GitHub issue created: {result.stdout.strip()}")
        else:
            logger.warning(f"Failed to create GitHub issue: {result.stderr}")
    except Exception as e:
        logger.warning(f"Could not create GitHub issue: {e}")


def get_access_token():
    """
    Exchange refresh_token for access_token.
    
    Note: The python-amazon-ad-api library handles token refresh internally.
    This function is kept for compatibility but returns credentials dict.
    """
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    refresh_token = os.getenv("REFRESH_TOKEN")
    profile_id = os.getenv("PROFILE_ID")
    
    if not all([client_id, client_secret, refresh_token, profile_id]):
        raise ValueError("Missing required credentials in .env.local")
    
    credentials = dict(
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        profile_id=profile_id
    )
    
    return credentials


def get_targets(profile_id: str, access_token: str, client_id: str) -> list:
    """
    Fetch all targets from Amazon Ads API using python-amazon-ad-api library.
    """
    from ad_api.api import sp
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    
    credentials = dict(
        refresh_token=os.getenv("REFRESH_TOKEN"),
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        profile_id=profile_id
    )
    
    all_targets = []
    start_index = 0
    count = 100
    
    logger.info(f"Fetching targets (profile: {profile_id})")
    
    while True:
        try:
            body = {
                "startIndex": start_index,
                "count": count,
                "stateFilter": {"include": ["ENABLED", "PAUSED"]}
            }
            
            result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
            payload = result.payload
            
            targets = payload.get("targetingClauses", [])
            
            if not targets:
                break
                
            all_targets.extend(targets)
            logger.info(f"Fetched {len(targets)} targets (total: {len(all_targets)})")
            
            total_results = payload.get("totalResults", 0)
            if len(all_targets) >= total_results:
                break
            
            start_index += count
            time.sleep(1)
            
        except Exception as e:
            error_str = str(e)
            if "invalid_grant" in error_str or "refresh_token" in error_str.lower():
                logger.error("REFRESH TOKEN EXPIRED - Creating GitHub issue...")
                create_github_issue(
                    "⚠️ Amazon Ads Refresh Token Expired",
                    "The refresh token has expired. Please re-authorize the application.\n\n"
                    f"Error: {error_str}\n\n"
                    "Steps to fix:\n"
                    "1. Run `python oauth_helper.py --marketplace de` locally\n"
                    "2. Get new authorization code from Amazon\n"
                    "3. Update REFRESH_TOKEN in GitHub Secrets"
                )
            logger.error(f"Error fetching targets: {e}")
            break
    
    return all_targets


def filter_targets(targets: list) -> list:
    """
    Filter targets that should be paused.
    Only includes ENABLED targets with unwanted expression types.
    """
    types_to_pause = {
        "QUERY_BROAD_REL_MATCHES": "loose-match",
        "ASIN_SUBSTITUTE_RELATED": "substitutes",
        "ASIN_ACCESSORY_RELATED": "complements"
    }

    targets_to_pause = []
    enabled_count = 0
    paused_count = 0

    for target in targets:
        target_state = target.get("state", "UNKNOWN")
        
        # === STRICT ENABLED FILTER - KEY FIX ===
        if target_state != "ENABLED":
            if target_state == "PAUSED":
                paused_count += 1
            continue  # Skip non-ENABLED targets immediately
        
        # Only process ENABLED targets
        enabled_count += 1
        
        expression = target.get("expression", [])
        
        found_types = []
        should_pause = False
        
        for expr in expression:
            expr_type = expr.get("type", "")
            if expr_type in types_to_pause:
                should_pause = True
                found_types.append(types_to_pause[expr_type])

        if should_pause:
            target["_found_types"] = found_types
            targets_to_pause.append(target)

    logger.info(f"Target filtering stats:")
    logger.info(f"  - Total targets: {len(targets)}")
    logger.info(f"  - Enabled targets: {enabled_count}")
    logger.info(f"  - Already paused: {paused_count}")
    logger.info(f"  - Targets to update: {len(targets_to_pause)}")

    return targets_to_pause


def update_targets(targets: list, profile_id: str, access_token: str, client_id: str,
                   dry_run: bool = False, test_mode: int = 0) -> dict:
    """
    Update targets to paused state with robust error handling and retry logic.
    
    Features:
    - Batch processing (50 per request for safety)
    - Rate limiting (1 second delay between batches)
    - Retry logic (1 retry on failure, then continue)
    - Full error logging with request/response details
    - Test mode support (update only N targets)
    
    Args:
        targets: List of target objects to pause
        profile_id: Amazon Ads profile ID
        access_token: (unused - kept for compatibility)
        client_id: (unused - kept for compatibility)
        dry_run: If True, simulate batching without sending API requests
        test_mode: If > 0, only update this many targets (for debugging)
    
    Returns:
        dict with success and failed counts
    """
    from ad_api.api import sp
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    
    if not targets:
        logger.info("No targets to update")
        return {"success": 0, "failed": 0, "total": 0}

    # Apply test mode limit if specified
    if test_mode > 0:
        targets = targets[:test_mode]
        logger.info(f"TEST MODE: Limiting to {test_mode} targets for debugging")

    credentials = dict(
        refresh_token=os.getenv("REFRESH_TOKEN"),
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        profile_id=profile_id
    )
    
    batch_size = 100
    total_targets = len(targets)
    num_batches = (total_targets + batch_size - 1) // batch_size
    
    success_count = 0
    failed_count = 0
    processed_count = 0
    retry_count = 0
    
    mode_text = "DRY-RUN" if dry_run else "LIVE"
    logger.info(f"[{mode_text}] Processing {total_targets} targets in {num_batches} batches of max {batch_size}")
    
    # Test mode: Log full debug info for first batch
    if test_mode > 0:
        logger.info("TEST MODE DEBUG - First target sample:")
        logger.info(f"  Target structure: {json.dumps(targets[0], indent=2)[:500]}")
    
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_targets)
        batch = targets[start_idx:end_idx]
        batch_length = len(batch)
        
        processed_count += batch_length
        progress_pct = (processed_count * 100) // total_targets
        
        logger.info(f"[{mode_text}] Batch {batch_num + 1}/{num_batches} ({progress_pct}%) - {batch_length} targets")
        
        if dry_run:
            logger.info(f"  - DRY-RUN: Would pause {batch_length} targets")
            success_count += batch_length
            time.sleep(0.1)
            continue
        
        # Build update payload
        updates = []
        for target in batch:
            updates.append({
                "targetId": target["targetId"],
                "state": "PAUSED"
            })
        
        # Wrap in targetingClauses for API
        payload = {"targetingClauses": updates}
        
        if test_mode > 0 and batch_num == 0:
            logger.info(f"  - DEBUG: Payload sample (first item): {json.dumps(updates[0], indent=2)}")
        
        # Attempt 1: First try
        success = False
        error_details = None
        
        try:
            result = sp.TargetsV3(credentials=credentials).edit_product_targets(body=payload)
            success = True
            success_count += batch_length
            logger.info(f"  - SUCCESS: Updated {batch_length} targets")
            logger.info(f"  - Verification skipped: Amazon Ads API does not support fetching single targets by ID")
            logger.info(f"  - Note: Next run will verify via state filter (only ENABLED targets will be updated)")
            
        except Exception as e:
            error_details = str(e)
            logger.error(f"  - FIRST ATTEMPT FAILED: {error_details}")
            
            # Attempt 2: Retry once
            logger.info(f"  - Retrying (1 more attempt after 2s delay)...")
            time.sleep(2)
            retry_count += 1
            
            try:
                result = sp.TargetsV3(credentials=credentials).edit_product_targets(body=payload)
                success = True
                success_count += batch_length
                logger.info(f"  - RETRY SUCCESS: Updated {batch_length} targets after retry")
                logger.info(f"  - Verification skipped: Amazon Ads API does not support fetching single targets by ID")
                
            except Exception as e2:
                error_details = str(e2)
                logger.error(f"  - RETRY ALSO FAILED: {error_details}")
                failed_count += batch_length
                
                # Log detailed error info
                logger.error(f"  - Failed batch payload (first 2 items):")
                for i, upd in enumerate(updates[:2]):
                    logger.error(f"    [{i+1}] targetId={upd.get('targetId')}, state={upd.get('state')}")
                
                # Check for specific error types
                if "429" in error_details:
                    logger.warning("  - Rate limit detected (429)")
                elif "timeout" in error_details.lower():
                    logger.warning("  - Timeout error detected")
        
        # Rate limiting between batches
        time.sleep(1)
    
    # Final summary
    logger.info("=" * 60)
    logger.info(f"UPDATE COMPLETE [{mode_text}]")
    logger.info(f"  - Total targets: {total_targets}")
    logger.info(f"  - Successful: {success_count}")
    logger.info(f"  - Failed: {failed_count}")
    logger.info(f"  - Retries used: {retry_count}")
    logger.info("=" * 60)
    
    return {
        "success": success_count, 
        "failed": failed_count,
        "total": total_targets,
        "retries": retry_count
    }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Pause non close-match auto targets in Amazon Ads")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--test", type=int, default=0, help="Test mode: update only N targets (for debugging)")
    args = parser.parse_args()

    load_dotenv(".env.local")
    load_dotenv(".env")

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    refresh_token = os.getenv("REFRESH_TOKEN")
    profile_id = os.getenv("PROFILE_ID")

    if not all([client_id, client_secret, refresh_token, profile_id]):
        logger.error("Missing required environment variables. Check .env file.")
        sys.exit(1)

    logger.info(f"Starting script (dry-run mode: {not args.apply}, test mode: {args.test})")
    logger.info(f"Profile ID: {profile_id}")

    logger.info("Getting credentials...")
    credentials = get_access_token()
    logger.info("Credentials loaded successfully")

    logger.info("Fetching all targets...")
    all_targets = get_targets(profile_id, "", client_id)
    logger.info(f"Total targets retrieved: {len(all_targets)}")

    if not all_targets:
        logger.info("No targets found in Amazon Ads")
        sys.exit(0)

    # Analyze expression types
    expr_types = {}
    for t in all_targets:
        for e in t.get("expression", []):
            etype = e.get("type", "UNKNOWN")
            expr_types[etype] = expr_types.get(etype, 0) + 1
    
    logger.info("Expression types found:")
    for etype, count in sorted(expr_types.items()):
        logger.info(f"  - {etype}: {count}")

    logger.info("Sample targets (first 2):")
    for t in all_targets[:2]:
        logger.info(f"  - Target ID: {t.get('targetId')}, Campaign: {t.get('campaignId')}, State: {t.get('state')}")
        logger.info(f"    Expression: {json.dumps(t.get('expression', []))}")

    logger.info("Filtering targets to pause (loose-match, substitutes, complements)...")
    targets_to_pause = filter_targets(all_targets)
    logger.info(f"Targets to pause: {len(targets_to_pause)}")

    if not targets_to_pause:
        logger.info("No targets found that need to be paused")
        sys.exit(0)

    logger.info("Targets to pause (first 10):")
    for target in targets_to_pause[:10]:
        campaign_id = target.get("campaignId", "N/A")
        ad_group_id = target.get("adGroupId", "N/A")
        target_id = target.get("targetId", "N/A")
        found_types = target.get("_found_types", [])
        logger.info(f"  - Target {target_id} (Campaign: {campaign_id}, AdGroup: {ad_group_id}) - Types: {found_types}")

    dry_run = not args.apply
    
    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY-RUN MODE - Simulating batch processing")
        logger.info("=" * 60)
        result = update_targets(targets_to_pause, profile_id, "", client_id, dry_run=True, test_mode=args.test)
        logger.info(f"Update complete (simulated): {result['success']} success, {result['failed']} failed")
    else:
        logger.info("Applying changes (pausing targets)...")
        result = update_targets(targets_to_pause, profile_id, "", client_id, dry_run=False, test_mode=args.test)
        logger.info(f"Update complete: {result['success']} success, {result['failed']} failed, {result.get('retries', 0)} retries")


if __name__ == "__main__":
    main()