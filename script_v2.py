"""
Amazon Ads Auto-Target Control Script V2

Controls AUTO CAMPAIGN TARGETING behavior:
- loose-match (QUERY_BROAD_REL_MATCHES) → PAUSE target
- complements (ASIN_ACCESSORY_RELATED) → set bid to LOW_BID (0.02)
- substitutes (ASIN_SUBSTITUTE_RELATED) → reduce bid by 20%, min LOW_BID
- close-match (QUERY_HIGH_REL_MATCHES) → SKIP

Designed to run as Render.com Cron Job
Schedule configured in Render dashboard
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

MAX_RUNTIME_SECONDS = 600
LOW_BID = 0.02
MIN_BID = 0.05
MIN_SUBSTITUTES_BID = 0.40

TYPE_MAPPING = {
    "QUERY_BROAD_REL_MATCHES": "loose-match",
    "ASIN_ACCESSORY_RELATED": "complements",
    "ASIN_SUBSTITUTE_RELATED": "substitutes",
    "QUERY_HIGH_REL_MATCHES": "close-match"
}

AUTO_TYPES = {"loose-match", "complements", "substitutes"}
CLOSE_MATCH = "close-match"


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
    """Exchange refresh_token for access_token."""
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
    """Fetch campaigns and return set of active (ENABLED) campaign IDs."""
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

            if state in ['ENABLED', 'PAUSED']:
                campaign_id = campaign.get('campaignId')
                if campaign_id:
                    active_ids.add(str(campaign_id))

        logger.info("Campaign states found:")
        for state, count in sorted(campaign_states.items()):
            logger.info(f"  - {state}: {count}")

        logger.info(f"Found {len(active_ids)} active campaigns (ENABLED or PAUSED)")

        return active_ids

    except Exception as e:
        logger.error(f"Error fetching campaigns: {e}")
        return set()


def get_targets(profile_id: str, access_token: str, client_id: str, campaign_ids: list = None) -> list:
    """Fetch all targets from Amazon Ads API using python-amazon-ad-api library."""
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


def categorize_targets(targets: list, active_campaign_ids: set = None, force_test_10: bool = False) -> dict:
    """
    Categorize targets by expression type and determine action.

    Returns:
        dict with keys:
        - pause_targets: loose-match targets (ENABLED) to pause
        - low_bid_targets: complements targets to set bid to LOW_BID
        - reduce_bid_targets: substitutes targets to reduce bid by 20%
        - skip_targets: close-match targets (no action)
        - stats: summary statistics
    """
    pause_targets = []
    low_bid_targets = []
    reduce_bid_targets = []
    skip_targets = []

    enabled_count = 0
    paused_count = 0
    archived_campaign_count = 0

    loose_match_count = 0
    complements_count = 0
    substitutes_count = 0
    close_match_count = 0
    unknown_type_count = 0

    for target in targets:
        target_state = target.get("state", "UNKNOWN")

        if target_state not in ["ENABLED", "PAUSED"]:
            continue

        if target_state == "ENABLED":
            enabled_count += 1
        elif target_state == "PAUSED":
            paused_count += 1

        if active_campaign_ids is not None:
            campaign_id = target.get("campaignId")
            if campaign_id not in active_campaign_ids:
                archived_campaign_count += 1
                continue

        expression = target.get("expression", [])

        target_type = None
        for expr in expression:
            expr_type = expr.get("type", "")
            mapped = TYPE_MAPPING.get(expr_type)
            if mapped:
                target_type = mapped
                break

        if target_type is None:
            unknown_type_count += 1
            skip_targets.append(target)
            continue

        current_bid = target.get("bid")

        if target_type == "loose-match":
            loose_match_count += 1
            if target_state == "ENABLED":
                target["_target_type"] = target_type
                target["_current_bid"] = current_bid
                pause_targets.append(target)

        elif target_type == "complements":
            complements_count += 1
            should_update = False

            if target_state == "ENABLED":
                if current_bid is None:
                    should_update = True
                elif current_bid > MIN_BID:
                    should_update = True
            elif target_state == "PAUSED":
                should_update = True

            if should_update or force_test_10:
                target["_target_type"] = target_type
                target["_current_bid"] = current_bid
                target["_new_bid"] = MIN_BID
                target["_new_state"] = "ENABLED" if target_state == "PAUSED" else None
                low_bid_targets.append(target)

        elif target_type == "substitutes":
            substitutes_count += 1
            should_update = False
            current_bid_val = current_bid if current_bid is not None else MIN_SUBSTITUTES_BID

            if target_state == "ENABLED":
                if current_bid is not None and current_bid > MIN_SUBSTITUTES_BID:
                    new_bid = round(current_bid * 0.8, 2)
                    new_bid = max(new_bid, MIN_SUBSTITUTES_BID)
                    should_update = True
                    target["_target_type"] = target_type
                    target["_current_bid"] = current_bid
                    target["_new_bid"] = new_bid
                    reduce_bid_targets.append(target)
            elif target_state == "PAUSED":
                new_bid = round(current_bid_val * 0.8, 2)
                new_bid = max(new_bid, MIN_SUBSTITUTES_BID)
                should_update = True
                target["_target_type"] = target_type
                target["_current_bid"] = current_bid
                target["_new_bid"] = new_bid
                target["_new_state"] = "ENABLED"
                reduce_bid_targets.append(target)

        elif target_type == "close-match":
            close_match_count += 1
            skip_targets.append(target)

    stats = {
        "total": len(targets),
        "enabled": enabled_count,
        "paused": paused_count,
        "archived_campaign": archived_campaign_count,
        "loose_match": loose_match_count,
        "complements": complements_count,
        "substitutes": substitutes_count,
        "close_match": close_match_count,
        "unknown_type": unknown_type_count
    }

    logger.info(f"Target categorization stats:")
    logger.info(f"  - Total targets: {stats['total']}")
    logger.info(f"  - Enabled targets: {stats['enabled']}")
    logger.info(f"  - Already paused: {stats['paused']}")
    if active_campaign_ids is not None:
        logger.info(f"  - Archived campaign targets: {stats['archived_campaign']}")
    logger.info(f"  - loose-match: {stats['loose_match']}")
    logger.info(f"  - complements: {stats['complements']}")
    logger.info(f"  - substitutes: {stats['substitutes']}")
    logger.info(f"  - close-match: {stats['close_match']}")
    logger.info(f"  - Unknown type: {stats['unknown_type']}")
    logger.info(f"  - Targets to PAUSE: {len(pause_targets)}")
    logger.info(f"  - Targets to set LOW_BID: {len(low_bid_targets)}")
    logger.info(f"  - Targets to REDUCE_BID: {len(reduce_bid_targets)}")
    logger.info(f"  - Targets to SKIP: {len(skip_targets)}")

    return {
        "pause_targets": pause_targets,
        "low_bid_targets": low_bid_targets,
        "reduce_bid_targets": reduce_bid_targets,
        "skip_targets": skip_targets,
        "stats": stats
    }


def log_decision(target: dict, action: str):
    """Log decision for a target."""
    target_id = target.get("targetId", "N/A")
    target_type = target.get("_target_type", "N/A")
    current_state = target.get("state", "N/A")
    old_bid = target.get("_current_bid")
    new_bid = target.get("_new_bid")
    new_state = target.get("_new_state")

    if old_bid is not None:
        old_bid = round(old_bid, 4)
    if new_bid is not None:
        new_bid = round(new_bid, 4)

    logger.info(f"[DECISION]")
    logger.info(f"TargetId={target_id}")
    logger.info(f"Type={target_type}")
    logger.info(f"State={current_state}")
    logger.info(f"OldBid={old_bid}")
    logger.info(f"Action={action}")

    if new_bid is not None:
        logger.info(f"NewBid={new_bid}")
    if new_state:
        logger.info(f"NewState={new_state}")


def update_targets(
    categorized: dict,
    profile_id: str,
    dry_run: bool = False,
    test_mode: int = 0,
    force_test_10: bool = False,
    low_bid: float = LOW_BID
) -> dict:
    """
    Update targets with split operations (pause vs bid updates).

    Args:
        categorized: dict from categorize_targets()
        profile_id: Amazon Ads profile ID
        dry_run: If True, simulate without API calls
        test_mode: If > 0, only update this many targets
        force_test_10: Process first 10, always apply (ignores conditions)
        low_bid: The low bid value

    Returns:
        dict with success/failed counts
    """
    from ad_api.api import sp

    start_time = time.time()

    pause_targets = categorized.get("pause_targets", [])
    low_bid_targets = categorized.get("low_bid_targets", [])
    reduce_bid_targets = categorized.get("reduce_bid_targets", [])

    total_to_update = len(pause_targets) + len(low_bid_targets) + len(reduce_bid_targets)

    if total_to_update == 0:
        logger.info("No targets to update")
        return {"success": 0, "failed": 0, "total": 0, "paused": 0, "bid_updated": 0}

    credentials = dict(
        refresh_token=os.getenv("REFRESH_TOKEN"),
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        profile_id=profile_id
    )

    mode_text = "DRY-RUN" if dry_run else "LIVE"
    logger.info(f"[{mode_text}] Processing {total_to_update} targets")

    if test_mode > 0:
        pause_targets = pause_targets[:test_mode]
        low_bid_targets = low_bid_targets[:test_mode]
        reduce_bid_targets = reduce_bid_targets[:test_mode]
        logger.info(f"TEST MODE: Limiting to {test_mode} targets per category")

    if force_test_10:
        pause_targets = pause_targets[:10]
        low_bid_targets = low_bid_targets[:10]
        reduce_bid_targets = reduce_bid_targets[:10]
        logger.info(f"FORCE-TEST-10: Processing first 10 targets per category, always applying")

    pause_count = len(pause_targets)
    bid_count = len(low_bid_targets) + len(reduce_bid_targets)

    logger.info(f"[{mode_text}] Pause operations: {pause_count}, Bid operations: {bid_count}")

    success_pause = 0
    failed_pause = 0
    success_bid = 0
    failed_bid = 0
    updated_target_ids = []

    if pause_targets:
        logger.info(f"Processing {len(pause_targets)} targets for PAUSE...")

        for target in pause_targets[:10]:
            log_decision(target, "PAUSE")

        if not dry_run and (force_test_10 or pause_targets):
            batch_size = 100
            total = len(pause_targets)
            num_batches = (total + batch_size - 1) // batch_size

            for batch_num in range(num_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total)
                batch = pause_targets[start_idx:end_idx]

                if time.time() - start_time > MAX_RUNTIME_SECONDS:
                    logger.warning(f"Soft timeout reached - stopping pause operations")
                    break

                updates = []
                for target in batch:
                    updates.append({
                        "targetId": target["targetId"],
                        "adGroupId": target.get("adGroupId"),
                        "campaignId": target.get("campaignId"),
                        "state": "PAUSED"
                    })
                    updated_target_ids.append(target["targetId"])

                payload = {"targetingClauses": updates}

                try:
                    result = sp.TargetsV3(credentials=credentials).edit_product_targets(body=payload)
                    response_data = result.payload

                    if isinstance(response_data, dict):
                        tc = response_data.get("targetingClauses", {})
                        errors = tc.get("error", [])
                        success_list = tc.get("success", [])

                        if errors:
                            logger.warning(f"  - API returned {len(errors)} error(s):")
                            for err in errors[:3]:
                                idx = err.get("index", "N/A")
                                err_details = err.get("errors", [])
                                for ed in err_details:
                                    reason = ed.get("errorValue", {}).get("entityStateError", {}).get("reason", "UNKNOWN")
                                    logger.warning(f"    - Index {idx}: {reason}")
                            failed_pause += len(errors)
                            success_pause += len(batch) - len(errors)
                        else:
                            success_pause += len(batch)

                    logger.info(f"  - PAUSE batch {batch_num + 1}/{num_batches}: {len(batch)} targets")

                except Exception as e:
                    logger.error(f"  - PAUSE batch failed: {e}")
                    failed_pause += len(batch)

                time.sleep(1)

    if low_bid_targets or reduce_bid_targets:
        logger.info(f"Processing {len(low_bid_targets) + len(reduce_bid_targets)} targets for BID UPDATE...")

        for target in low_bid_targets[:5]:
            action = "ACTIVATE" if target.get("_new_state") == "ENABLED" else "SET_BID"
            log_decision(target, action)

        for target in reduce_bid_targets[:5]:
            action = "ACTIVATE" if target.get("_new_state") == "ENABLED" else "REDUCE_BID"
            log_decision(target, action)

        if not dry_run and (force_test_10 or low_bid_targets or reduce_bid_targets):
            bid_targets = low_bid_targets + reduce_bid_targets
            batch_size = 100
            total = len(bid_targets)
            num_batches = (total + batch_size - 1) // batch_size

            for batch_num in range(num_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total)
                batch = bid_targets[start_idx:end_idx]

                if time.time() - start_time > MAX_RUNTIME_SECONDS:
                    logger.warning(f"Soft timeout reached - stopping bid operations")
                    break

                updates = []
                for target in batch:
                    new_bid = target.get("_new_bid", low_bid)
                    new_state = target.get("_new_state")
                    
                    update = {
                        "targetId": target["targetId"],
                        "adGroupId": target.get("adGroupId"),
                        "campaignId": target.get("campaignId"),
                        "bid": new_bid
                    }
                    if new_state:
                        update["state"] = new_state
                    
                    updates.append(update)
                    updated_target_ids.append(target["targetId"])

                payload = {"targetingClauses": updates}

                try:
                    result = sp.TargetsV3(credentials=credentials).edit_product_targets(body=payload)
                    response_data = result.payload

                    if isinstance(response_data, dict):
                        tc = response_data.get("targetingClauses", {})
                        errors = tc.get("error", [])
                        success_list = tc.get("success", [])

                        if errors:
                            logger.warning(f"  - API returned {len(errors)} error(s):")
                            for err in errors[:3]:
                                idx = err.get("index", "N/A")
                                err_details = err.get("errors", [])
                                for ed in err_details:
                                    reason = ed.get("errorValue", {}).get("entityStateError", {}).get("reason", "UNKNOWN")
                                    logger.warning(f"    - Index {idx}: {reason}")
                            failed_bid += len(errors)
                            success_bid += len(batch) - len(errors)
                        else:
                            success_bid += len(batch)

                    logger.info(f"  - BID batch {batch_num + 1}/{num_batches}: {len(batch)} targets")

                except Exception as e:
                    logger.error(f"  - BID batch failed: {e}")
                    failed_bid += len(batch)

                time.sleep(1)

    if dry_run:
        success_pause = len(pause_targets)
        success_bid = len(low_bid_targets) + len(reduce_bid_targets)

    logger.info("=" * 60)
    logger.info(f"UPDATE COMPLETE [{mode_text}]")
    logger.info(f"  - Targets to PAUSE: {len(pause_targets)}")
    logger.info(f"  - Targets to set LOW_BID: {len(low_bid_targets)}")
    logger.info(f"  - Targets to REDUCE_BID: {len(reduce_bid_targets)}")
    logger.info(f"  - PAUSE success: {success_pause}, failed: {failed_pause}")
    logger.info(f"  - BID success: {success_bid}, failed: {failed_bid}")
    logger.info("=" * 60)

    return {
        "success": success_pause + success_bid,
        "failed": failed_pause + failed_bid,
        "total": total_to_update,
        "paused": success_pause,
        "bid_updated": success_bid,
        "updated_ids": updated_target_ids
    }


def verify_updates(updated_ids: list, profile_id: str, categorized: dict):
    """Post-update verification - re-fetch targets."""
    from ad_api.api import sp

    if not updated_ids:
        return

    credentials = dict(
        refresh_token=os.getenv("REFRESH_TOKEN"),
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        profile_id=profile_id
    )

    logger.info(f"POST-UPDATE VERIFICATION: Re-fetching targets to verify changes...")

    try:
        verify_body = {
            "startIndex": 0,
            "count": min(1000, len(updated_ids) + 100),
            "stateFilter": {"include": ["ENABLED", "PAUSED"]}
        }

        verify_result = sp.TargetsV3(credentials=credentials).list_product_targets(body=verify_body)
        all_verify_targets = verify_result.payload.get("targetingClauses", [])

        pause_targets = {t["targetId"] for t in categorized.get("pause_targets", [])}
        low_bid_targets = {t["targetId"] for t in categorized.get("low_bid_targets", [])}
        reduce_bid_targets = {t["targetId"] for t in categorized.get("reduce_bid_targets", [])}

        verified_count = 0
        for t in all_verify_targets:
            if t.get("targetId") in updated_ids:
                target_id = t.get("targetId", "N/A")
                actual_state = t.get("state", "N/A")
                actual_bid = t.get("bid")

                expected_state = "PAUSED" if target_id in pause_targets else "N/A"
                expected_bid = None

                if target_id in low_bid_targets:
                    expected_bid = LOW_BID
                elif target_id in reduce_bid_targets:
                    for orig in categorized.get("reduce_bid_targets", []):
                        if orig.get("targetId") == target_id:
                            expected_bid = orig.get("_new_bid")
                            break

                logger.info(f"[VERIFY]")
                logger.info(f"TargetId={target_id}")
                logger.info(f"ExpectedState={expected_state}")
                logger.info(f"ActualState={actual_state}")
                if expected_bid is not None:
                    logger.info(f"ExpectedBid={round(expected_bid, 4)}")
                if actual_bid is not None:
                    logger.info(f"ActualBid={round(actual_bid, 4)}")

                verified_count += 1
                if verified_count >= 10:
                    break

        if verified_count == 0:
            logger.warning("VERIFICATION: Could not find any updated targets in re-fetch")

    except Exception as verify_err:
        logger.error(f"VERIFICATION ERROR: {verify_err}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Control auto-target bids/pause in Amazon Ads")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--test", type=int, default=0, help="Test mode: update only N targets (for debugging)")
    parser.add_argument("--max-updates", type=int, default=0, help="Maximum number of targets to update in this run")
    parser.add_argument("--low-bid", type=float, default=LOW_BID, help=f"Low bid value (default: {LOW_BID})")
    parser.add_argument("--force-test-10", action="store_true", help="Process first 10 targets only, always apply (ignores conditions)")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(".env.local")

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
    logger.info(f"Starting Script V2 ({timestamp}, {mode} mode)")
    logger.info(f"Profile ID: {profile_id}")
    logger.info(f"Low bid value: {args.low_bid}")

    logger.info("Getting credentials...")
    credentials = get_access_token()
    logger.info("Credentials loaded successfully")

    active_campaign_ids = get_active_campaign_ids(profile_id)

    logger.info("Fetching ALL targets...")
    all_targets = get_targets(profile_id, "", client_id, campaign_ids=None)
    logger.info(f"Total targets retrieved: {len(all_targets)}")

    if not all_targets:
        logger.info("No targets found in Amazon Ads")
        sys.exit(0)

    expr_types = {}
    for t in all_targets:
        for e in t.get("expression", []):
            etype = e.get("type", "UNKNOWN")
            expr_types[etype] = expr_types.get(etype, 0) + 1

    logger.info("Expression types found:")
    for etype, count in sorted(expr_types.items()):
        logger.info(f"  - {etype}: {count}")

    logger.info("Categorizing targets...")
    categorized = categorize_targets(
        all_targets,
        active_campaign_ids=active_campaign_ids,
        force_test_10=args.force_test_10
    )

    pause_count = len(categorized["pause_targets"])
    low_bid_count = len(categorized["low_bid_targets"])
    reduce_count = len(categorized["reduce_bid_targets"])
    skip_count = len(categorized["skip_targets"])

    total_action = pause_count + low_bid_count + reduce_count

    logger.info(f"Action summary:")
    logger.info(f"  - PAUSE (loose-match): {pause_count}")
    logger.info(f"  - SET LOW_BID (complements): {low_bid_count}")
    logger.info(f"  - REDUCE BID (substitutes): {reduce_count}")
    logger.info(f"  - SKIP (close-match): {skip_count}")
    logger.info(f"  - Total needing action: {total_action}")

    if total_action == 0:
        logger.info("No targets requiring action - exiting early")
        sys.exit(0)

    if args.max_updates > 0 and total_action > args.max_updates:
        logger.info(f"LIMIT: --max-updates={args.max_updates}, truncating targets")

    dry_run = not args.apply

    if args.force_test_10:
        logger.info("FORCE-TEST-10: Applying changes to first 10 targets per category")
        result = update_targets(
            categorized,
            profile_id,
            dry_run=False,
            test_mode=0,
            force_test_10=True,
            low_bid=args.low_bid
        )
    elif dry_run:
        logger.info("=" * 60)
        logger.info("DRY-RUN MODE - Simulating batch processing")
        logger.info("=" * 60)
        result = update_targets(
            categorized,
            profile_id,
            dry_run=True,
            test_mode=args.test,
            force_test_10=False,
            low_bid=args.low_bid
        )
        logger.info(f"Update complete (simulated): {result['success']} success, {result['failed']} failed")
    else:
        logger.info("Applying changes...")
        result = update_targets(
            categorized,
            profile_id,
            dry_run=False,
            test_mode=args.test,
            force_test_10=False,
            low_bid=args.low_bid
        )
        logger.info(f"Update complete: {result['success']} success, {result['failed']} failed")

        if result.get("updated_ids"):
            verify_updates(result["updated_ids"], profile_id, categorized)


if __name__ == "__main__":
    main()