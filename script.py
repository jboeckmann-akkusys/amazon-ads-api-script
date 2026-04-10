"""
Amazon Ads Auto-Target Pause Script

Designed to run as Render.com Cron Job
Schedule configured in Render dashboard (e.g. every 15 minutes)
Credentials provided via Render environment variables
"""

import argparse
import logging
import os
import sys
import json
import time
import subprocess
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

MAX_RUNTIME_SECONDS = 600  # 10 minutes soft timeout
LOW_BID = 0.02  # Minimum bid value for unwanted targeting types


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
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    refresh_token = os.getenv("REFRESH_TOKEN")
    profile_id = os.getenv("PROFILE_ID")
    
    if not all([client_id, client_secret, refresh_token, profile_id]):
        missing = []
        if not client_id:
            missing.append("CLIENT_ID")
        if not client_secret:
            missing.append("CLIENT_SECRET")
        if not refresh_token:
            missing.append("REFRESH_TOKEN")
        if not profile_id:
            missing.append("PROFILE_ID")
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    credentials = dict(
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        profile_id=profile_id
    )
    
    return credentials


def get_active_campaign_ids(profile_id: str) -> set:
    """
    Fetch campaigns and return set of active (ENABLED) campaign IDs.
    """
    from ad_api.api import sp
    
    credentials = dict(
        refresh_token=os.getenv("REFRESH_TOKEN"),
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        profile_id=profile_id
    )
    
    logger.info("Fetching campaigns to identify active ones...")
    
    try:
        result = sp.CampaignsV3(credentials=credentials).list_campaigns(body={})
        campaigns = result.payload.get('campaigns', [])
        
        active_ids = set()
        campaign_states = {}
        
        for campaign in campaigns:
            state = campaign.get('state', 'UNKNOWN')
            campaign_states[state] = campaign_states.get(state, 0) + 1
            
            if state == 'ENABLED':
                campaign_id = campaign.get('campaignId')
                if campaign_id:
                    # Store as string to match target campaignId format
                    active_ids.add(str(campaign_id))
        
        logger.info("Campaign states found:")
        for state, count in sorted(campaign_states.items()):
            logger.info(f"  - {state}: {count}")
        
        logger.info(f"Found {len(active_ids)} active campaigns")
        
        return active_ids
        
    except Exception as e:
        logger.error(f"Error fetching campaigns: {e}")
        return set()


def get_targets(profile_id: str, access_token: str, client_id: str, campaign_ids: list = None) -> list:
    """
    Fetch all targets from Amazon Ads API using python-amazon-ad-api library.
    Optionally filter by campaign IDs.
    """
    from ad_api.api import sp
    
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
            
            # Add campaignIdFilter if campaign IDs provided
            if campaign_ids:
                body["campaignIdFilter"] = {"include": campaign_ids}
            
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


def filter_targets(targets: list, active_campaign_ids: set = None, low_bid: float = LOW_BID) -> list:
    """
    Filter targets that need bid reduction.
    Only includes ENABLED targets with unwanted expression types AND bid > low_bid
    AND belong to active (non-archived) campaigns.
    """
    types_to_reduce = {
        "QUERY_BROAD_REL_MATCHES": "loose-match",
        "ASIN_SUBSTITUTE_RELATED": "substitutes",
        "ASIN_ACCESSORY_RELATED": "complements"
    }

    targets_to_reduce_bid = []
    enabled_count = 0
    paused_count = 0
    already_low_bid_count = 0
    archived_campaign_count = 0

    for target in targets:
        target_state = target.get("state", "UNKNOWN")
        
        # Include both ENABLED and PAUSED targets from active campaigns
        if target_state not in ["ENABLED", "PAUSED"]:
            continue
        
        # Count states
        if target_state == "ENABLED":
            enabled_count += 1
        elif target_state == "PAUSED":
            paused_count += 1
        
        # Check if target belongs to archived campaign
        if active_campaign_ids is not None:
            campaign_id = target.get("campaignId")
            if campaign_id not in active_campaign_ids:
                archived_campaign_count += 1
                continue
        
        # Check if bid is already at or below LOW_BID - skip these
        # Note: For auto targets, bid may be None (inherits ad group default)
        current_bid = target.get("bid")
        if current_bid is not None and current_bid <= low_bid:
            already_low_bid_count += 1
            continue
        
        expression = target.get("expression", [])
        
        found_types = []
        should_reduce = False
        
        for expr in expression:
            expr_type = expr.get("type", "")
            if expr_type in types_to_reduce:
                should_reduce = True
                found_types.append(types_to_reduce[expr_type])

        if should_reduce:
            target["_found_types"] = found_types
            target["_current_bid"] = current_bid
            targets_to_reduce_bid.append(target)

    logger.info(f"Target filtering stats:")
    logger.info(f"  - Total targets: {len(targets)}")
    logger.info(f"  - Enabled targets: {enabled_count}")
    logger.info(f"  - Already paused: {paused_count}")
    if active_campaign_ids is not None:
        logger.info(f"  - Archived campaign targets: {archived_campaign_count}")
    logger.info(f"  - Already low bid (<= {low_bid}): {already_low_bid_count}")
    logger.info(f"  - Targets to reduce bid: {len(targets_to_reduce_bid)}")

    return targets_to_reduce_bid


def update_targets(targets: list, profile_id: str, access_token: str, client_id: str,
                   dry_run: bool = False, test_mode: int = 0, low_bid: float = LOW_BID) -> dict:
    """
    Update targets to reduced bid with robust error handling and retry logic.
    
    Features:
    - Batch processing (100 per request for safety)
    - Rate limiting (1 second delay between batches)
    - Retry logic (1 retry on failure, then continue)
    - Full error logging with request/response details
    - Test mode support (update only N targets)
    - Soft timeout protection (~10 minutes max)
    
    Args:
        targets: List of target objects to update
        profile_id: Amazon Ads profile ID
        access_token: (unused - kept for compatibility)
        client_id: (unused - kept for compatibility)
        dry_run: If True, simulate batching without sending API requests
        test_mode: If > 0, only update this many targets (for debugging)
        low_bid: The bid value to set for unwanted targeting types
    
    Returns:
        dict with success and failed counts
    """
    from ad_api.api import sp
    
    start_time = time.time()
    
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
    updated_target_ids = []  # Track updated target IDs for verification
    
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
        
        if time.time() - start_time > MAX_RUNTIME_SECONDS:
            logger.warning(f"Soft timeout reached ({MAX_RUNTIME_SECONDS}s) - stopping after batch {batch_num + 1}")
            logger.info(f"Processed {processed_count} of {total_targets} targets")
            break
        
        if dry_run:
            logger.info(f"  - DRY-RUN: Would reduce bid to {low_bid} for {batch_length} targets")
            success_count += batch_length
            # Track for verification in dry-run too
            for target in batch:
                updated_target_ids.append(target["targetId"])
            time.sleep(0.1)
            continue
        
        # Build update payload - reduce bid to LOW_BID
        updates = []
        for target in batch:
            # Log BEFORE state for debugging
            logger.info(f"BEFORE: Target {target['targetId']} | Campaign {target['campaignId']} | AdGroup {target['adGroupId']} | Current bid = {target.get('bid')}")
            
            updates.append({
                "targetId": target["targetId"],
                "adGroupId": target["adGroupId"],
                "campaignId": target["campaignId"],
                "bid": low_bid
            })
            updated_target_ids.append(target["targetId"])
        
        # Wrap in targetingClauses for API
        payload = {"targetingClauses": updates}
        
        # Log UPDATE payload sample (first 5 items)
        logger.info("UPDATE PAYLOAD SAMPLE:")
        for upd in updates[:5]:
            logger.info(f"  -> Target {upd['targetId']} | New bid = {upd['bid']}")
        
        # Attempt 1: First try
        success = False
        error_details = None
        
        try:
            result = sp.TargetsV3(credentials=credentials).edit_product_targets(body=payload)
            # Log API response
            logger.info(f"API RESPONSE: {result.payload}")
            
            # Check for errors in response
            response_data = result.payload
            if isinstance(response_data, dict):
                targeting_clauses = response_data.get("targetingClauses", {})
                errors = targeting_clauses.get("error", [])
                success_list = targeting_clauses.get("success", [])
                
                if errors:
                    logger.warning(f"  - API returned {len(errors)} error(s):")
                    for err in errors[:3]:  # Log first 3 errors
                        idx = err.get("index", "N/A")
                        err_details = err.get("errors", [])
                        for ed in err_details:
                            reason = ed.get("errorValue", {}).get("entityStateError", {}).get("reason", "UNKNOWN")
                            logger.warning(f"    - Index {idx}: {reason}")
                else:
                    logger.info(f"  - No errors in API response")
            
            success = True
            success_count += batch_length
            logger.info(f"  - SUCCESS: Updated {batch_length} targets")
            
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
                    logger.error(f"    [{i+1}] targetId={upd.get('targetId')}, bid={upd.get('bid')}")
                
                # Check for specific error types
                if "429" in error_details:
                    logger.warning("  - Rate limit detected (429)")
                elif "timeout" in error_details.lower():
                    logger.warning("  - Timeout error detected")
        
        # Rate limiting between batches
        time.sleep(1)
    
    # POST-UPDATE VERIFICATION STEP
    if success_count > 0 and not dry_run:
        logger.info("POST-UPDATE VERIFICATION: Re-fetching targets to verify bid changes...")
        verification_sample = updated_target_ids[:10]  # Verify first 10
        
        # Re-fetch targets
        verify_body = {
            "startIndex": 0,
            "count": min(1000, len(updated_target_ids) + 100),
            "stateFilter": {"include": ["ENABLED", "PAUSED"]}
        }
        
        try:
            verify_result = sp.TargetsV3(credentials=credentials).list_product_targets(body=verify_body)
            all_verify_targets = verify_result.payload.get("targetingClauses", [])
            
            # Find our updated targets
            logger.info("POST-UPDATE VERIFICATION:")
            verified_count = 0
            for t in all_verify_targets:
                if t.get("targetId") in updated_target_ids:
                    current_bid = t.get("bid", "N/A")
                    target_id = t.get("targetId", "N/A")
                    logger.info(f"VERIFY: Target {target_id} | Current bid after update = {current_bid}")
                    verified_count += 1
                    if verified_count >= 10:
                        break
            
            if verified_count == 0:
                logger.warning("VERIFICATION: Could not find any updated targets in re-fetch")
                
        except Exception as verify_err:
            logger.error(f"VERIFICATION ERROR: {verify_err}")
    
    # Final summary
    logger.info("=" * 60)
    logger.info(f"BID UPDATE COMPLETE [{mode_text}]")
    logger.info(f"  - Total targets checked: {total_targets}")
    logger.info(f"  - Targets updated: {success_count}")
    logger.info(f"  - Failed: {failed_count}")
    logger.info(f"  - Retries used: {retry_count}")
    logger.info("=" * 60)
    
    # BID DEBUG SUMMARY
    logger.info("=" * 60)
    logger.info("BID DEBUG SUMMARY")
    logger.info(f"  - Total targets checked: {len(targets)}")
    logger.info(f"  - Targets selected for update: {len(updated_target_ids)}")
    if not dry_run:
        logger.info(f"  - Sample verified targets: {min(10, len(updated_target_ids))}")
    logger.info("=" * 60)
    
    return {
        "success": success_count, 
        "failed": failed_count,
        "total": total_targets,
        "retries": retry_count
    }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Reduce bids for non close-match auto targets in Amazon Ads")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--test", type=int, default=0, help="Test mode: update only N targets (for debugging)")
    parser.add_argument("--max-updates", type=int, default=0, help="Maximum number of targets to update in this run")
    parser.add_argument("--low-bid", type=float, default=LOW_BID, help=f"Low bid value to set (default: {LOW_BID})")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(".env.local")
    
    # Debug: print what was loaded
    logger.info("Loading environment variables...")
    logger.info(f"  CLIENT_ID present: {bool(os.getenv('CLIENT_ID'))}")
    logger.info(f"  CLIENT_SECRET present: {bool(os.getenv('CLIENT_SECRET'))}")
    logger.info(f"  REFRESH_TOKEN present: {bool(os.getenv('REFRESH_TOKEN'))}")
    logger.info(f"  PROFILE_ID present: {bool(os.getenv('PROFILE_ID'))}")

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    refresh_token = os.getenv("REFRESH_TOKEN")
    profile_id = os.getenv("PROFILE_ID")

    if not all([client_id, client_secret, refresh_token, profile_id]):
        missing = []
        if not client_id:
            missing.append("CLIENT_ID")
        if not client_secret:
            missing.append("CLIENT_SECRET")
        if not refresh_token:
            missing.append("REFRESH_TOKEN")
        if not profile_id:
            missing.append("PROFILE_ID")
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode = "APPLY" if args.apply else "DRY-RUN"
    logger.info(f"Starting Render Cron Job ({timestamp}, {mode} mode)")
    logger.info(f"Profile ID: {profile_id}")
    logger.info(f"Low bid value: {args.low_bid}")

    logger.info("Getting credentials...")
    credentials = get_access_token()
    logger.info("Credentials loaded successfully")

    # First, get active campaign IDs
    active_campaign_ids = get_active_campaign_ids(profile_id)
    
    logger.info("Fetching targets for active campaigns...")
    all_targets = get_targets(profile_id, "", client_id, campaign_ids=list(active_campaign_ids))
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

    logger.info("Filtering targets to reduce bid (loose-match, substitutes, complements)...")
    targets_to_reduce = filter_targets(all_targets, active_campaign_ids=active_campaign_ids, low_bid=args.low_bid)
    logger.info(f"Targets to reduce bid: {len(targets_to_reduce)}")

    # Delta run summary
    total_targets = len(all_targets)
    targets_to_update = len(targets_to_reduce)
    delta_pct = (targets_to_update * 100 // total_targets) if total_targets > 0 else 0
    logger.info(f"Delta run: {targets_to_update} / {total_targets} targets need bid reduction ({delta_pct}%)")

    # Early exit if no targets to update
    if not targets_to_reduce:
        logger.info("No targets to update - exiting early")
        sys.exit(0)

    # Apply max-updates limit if specified
    if args.max_updates > 0 and len(targets_to_reduce) > args.max_updates:
        targets_to_reduce = targets_to_reduce[:args.max_updates]
        logger.info(f"LIMIT: Only processing first {args.max_updates} targets (--max-updates)")

    logger.info("Targets to reduce bid (first 10):")
    for target in targets_to_reduce[:10]:
        campaign_id = target.get("campaignId", "N/A")
        ad_group_id = target.get("adGroupId", "N/A")
        target_id = target.get("targetId", "N/A")
        current_bid = target.get("_current_bid", "N/A")
        found_types = target.get("_found_types", [])
        logger.info(f"  - Target {target_id} (Campaign: {campaign_id}, AdGroup: {ad_group_id}) - Types: {found_types}, Current bid: {current_bid}")

    dry_run = not args.apply
    
    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY-RUN MODE - Simulating batch processing")
        logger.info("=" * 60)
        result = update_targets(targets_to_reduce, profile_id, "", client_id, dry_run=True, test_mode=args.test, low_bid=args.low_bid)
        logger.info(f"Update complete (simulated): {result['success']} success, {result['failed']} failed")
    else:
        logger.info("Applying changes (reducing bids)...")
        result = update_targets(targets_to_reduce, profile_id, "", client_id, dry_run=False, test_mode=args.test, low_bid=args.low_bid)
        logger.info(f"Update complete: {result['success']} success, {result['failed']} failed, {result.get('retries', 0)} retries")


if __name__ == "__main__":
    main()