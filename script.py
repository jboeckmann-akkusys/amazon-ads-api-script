import argparse
import logging
import os
import sys
import json
import time

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
    
    Uses sp.TargetsV3 to fetch targeting clauses.
    The API returns 'targetingClauses' array with target objects.
    
    Changes:
    - Uses ad_api library for authentication and API calls
    - Handles pagination via nextToken
    - Returns targetingClauses (NOT targets array) for filter_targets() compatibility
    
    Note: Expression types returned:
    - QUERY_HIGH_REL_MATCHES = close-match
    - QUERY_BROAD_REL_MATCHES = loose-match
    - ASIN_SUBSTITUTE_RELATED = substitutes
    - ASIN_ACCESSORY_RELATED = complements
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
                "count": count
            }
            
            result = sp.TargetsV3(credentials=credentials).list_product_targets(body=body)
            payload = result.payload
            
            # The API returns targetingClauses array, not targets
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
            logger.error(f"Error fetching targets: {e}")
            break
    
    return all_targets


def filter_targets(targets: list) -> list:
    """
    Filter targets that should be paused.
    
    Expression types (from API):
    - QUERY_BROAD_REL_MATCHES = loose-match
    - ASIN_SUBSTITUTE_RELATED = substitutes
    - ASIN_ACCESSORY_RELATED = complements
    
    Returns targets that match these types (NOT close-match).
    """
    # Map API expression types to display names
    types_to_pause = {
        "QUERY_BROAD_REL_MATCHES": "loose-match",
        "ASIN_SUBSTITUTE_RELATED": "substitutes",
        "ASIN_ACCESSORY_RELATED": "complements"
    }

    targets_to_pause = []

    for target in targets:
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

    return targets_to_pause


def update_targets(targets: list, profile_id: str, access_token: str, client_id: str, dry_run: bool = False) -> dict:
    """
    Update targets to paused state using python-amazon-ad-api library.
    
    Features:
    - Batch processing (max 100 per request)
    - Rate limiting (1 second delay between batches)
    - Progress tracking with detailed logging
    - Error handling (continues on failure)
    - Dry-run mode support
    
    Args:
        targets: List of target objects to pause
        profile_id: Amazon Ads profile ID
        access_token: (unused - kept for compatibility)
        client_id: (unused - kept for compatibility)
        dry_run: If True, simulate batching without sending API requests
    
    Returns:
        dict with success and failed counts
    """
    from ad_api.api import sp
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    
    if not targets:
        logger.info("No targets to update")
        return {"success": 0, "failed": 0, "total": 0}

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
    
    mode_text = "DRY-RUN" if dry_run else "LIVE"
    logger.info(f"[{mode_text}] Processing {total_targets} targets in {num_batches} batches of max {batch_size}")
    
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_targets)
        batch = targets[start_idx:end_idx]
        batch_length = len(batch)
        
        # Calculate progress
        processed_count += batch_length
        progress_pct = (processed_count * 100) // total_targets
        
        # Log batch start
        logger.info(f"[{mode_text}] Processing batch {batch_num + 1} of {num_batches} ({progress_pct}% complete)")
        logger.info(f"  - Batch size: {batch_length} targets")
        
        # In dry-run mode, skip API call but still log
        if dry_run:
            logger.info(f"  - DRY-RUN: Would pause {batch_length} targets")
            logger.info(f"    (Batch {batch_num + 1} skipped - dry-run mode)")
            success_count += batch_length
            time.sleep(0.1)  # Short delay just for show in dry-run
            continue
        
        # Build update payload
        updates = []
        for target in batch:
            updates.append({
                "targetId": target["targetId"],
                "state": "paused"
            })
        
        try:
            result = sp.TargetsV3(credentials=credentials).edit_product_targets(
                body=updates
            )
            
            success_count += batch_length
            logger.info(f"  - SUCCESS: Updated {batch_length} targets to paused")
            
        except Exception as e:
            # Log error but continue with next batch
            failed_count += batch_length
            logger.error(f"  - FAILED: {e}")
            logger.error(f"    Continuing with next batch...")
            # Continue - do NOT stop the script
        
        # Rate limiting between batches
        time.sleep(1)
    
    # Final summary
    logger.info("=" * 50)
    logger.info(f"UPDATE COMPLETE [{mode_text}]")
    logger.info(f"  - Total targets: {total_targets}")
    logger.info(f"  - Total processed: {processed_count}")
    logger.info(f"  - Successful: {success_count}")
    logger.info(f"  - Failed: {failed_count}")
    logger.info("=" * 50)
    
    return {
        "success": success_count, 
        "failed": failed_count,
        "total": total_targets
    }


def main():
    """Main function - unchanged from original."""
    parser = argparse.ArgumentParser(description="Pause non close-match auto targets in Amazon Ads")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
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

    logger.info(f"Starting script (dry-run mode: {not args.apply})")
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

    logger.info("Targets to pause:")
    for target in targets_to_pause[:10]:
        campaign_id = target.get("campaignId", "N/A")
        ad_group_id = target.get("adGroupId", "N/A")
        target_id = target.get("targetId", "N/A")
        found_types = target.get("_found_types", [])
        logger.info(f"  - Target {target_id} (Campaign: {campaign_id}, AdGroup: {ad_group_id}) - Types: {found_types}")

    # Determine dry_run mode
    dry_run = not args.apply
    
    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY-RUN MODE - Simulating batch processing")
        logger.info("=" * 60)
        # Run update_targets in dry-run mode to show batching/logging
        result = update_targets(targets_to_pause, profile_id, "", client_id, dry_run=True)
        logger.info(f"Update complete (simulated): {result['success']} success, {result['failed']} failed")
    else:
        logger.info("Applying changes (pausing targets)...")
        result = update_targets(targets_to_pause, profile_id, "", client_id, dry_run=False)
        logger.info(f"Update complete: {result['success']} success, {result['failed']} failed")


if __name__ == "__main__":
    main()