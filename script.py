import argparse
import logging
import os
import sys

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_credentials():
    return {
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
        "refresh_token": os.getenv("REFRESH_TOKEN"),
        "profile_id": os.getenv("PROFILE_ID"),
    }


def get_targets(credentials: dict) -> list:
    import os
    from ad_api.api import sp
    from ad_api.base import Marketplaces

    profile_id = credentials.get("profile_id")
    os.environ["AD_API_PROFILE_ID"] = profile_id
    
    all_targets = []
    start_index = 0
    count = 100

    while True:
        try:
            response = sp.TargetsV3(
                account="default",
                marketplace=Marketplaces.EU,
                credentials=credentials,
                verify_additional_credentials=False
            ).list_product_targets(body={
                "startIndex": start_index,
                "count": count,
            })

            targets = response.get("targets", [])
            all_targets.extend(targets)

            logger.info(f"Fetched {len(targets)} targets (total so far: {len(all_targets)})")

            if len(targets) < count:
                break

            start_index += count

        except Exception as e:
            logger.error(f"Error fetching targets at startIndex {start_index}: {e}")
            break

    return all_targets


def filter_targets(targets: list) -> list:
    types_to_pause = [
        "queryBroadRelMatches",
        "asinSubstituteRelated",
        "asinAccessoryRelated"
    ]

    types_to_keep = [
        "queryBroadMatches",
        "queryPhraseMatches",
        "queryExactMatches",
        "queryHighRelMatches"
    ]

    targets_to_pause = []

    for target in targets:
        expression_type = target.get("expressionType", "")
        expression = target.get("expression", [])

        if expression_type.lower() != "auto":
            continue

        found_types = []
        should_pause = False

        for expr in expression:
            expr_type = expr.get("type", "")
            if expr_type in types_to_pause:
                should_pause = True
                found_types.append(expr_type)

        if should_pause:
            target["_found_types"] = found_types
            targets_to_pause.append(target)

    return targets_to_pause


def update_targets(targets: list, credentials: dict) -> dict:
    import os
    from ad_api.api import sp
    from ad_api.base import Marketplaces

    if not targets:
        logger.info("No targets to update")
        return {"success": 0, "failed": 0}

    profile_id = credentials.get("profile_id")
    os.environ["AD_API_PROFILE_ID"] = profile_id
    
    batch_size = 100
    success_count = 0
    failed_count = 0

    for i in range(0, len(targets), batch_size):
        batch = targets[i:i + batch_size]

        updates = []
        for target in batch:
            updates.append({
                "targetId": target["targetId"],
                "state": "paused"
            })

        try:
            response = sp.TargetsV3(
                account="default",
                marketplace=Marketplaces.EU,
                credentials=credentials,
                verify_additional_credentials=False
            ).edit_product_targets(updates=updates)

            success_count += len(batch)
            logger.info(f"Updated batch of {len(batch)} targets to paused")

        except Exception as e:
            logger.error(f"Error updating batch: {e}")
            failed_count += len(batch)

    return {"success": success_count, "failed": failed_count}


def main():
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

    credentials = get_credentials()

    logger.info(f"Starting script (dry-run mode: {not args.apply})")

    logger.info("Fetching all targets...")
    all_targets = get_targets(credentials)
    logger.info(f"{len(all_targets)} targets retrieved")

    logger.info("Filtering auto-targets to pause...")
    targets_to_pause = filter_targets(all_targets)
    logger.info(f"{len(targets_to_pause)} targets to pause")

    if not targets_to_pause:
        logger.info("No targets found that need to be paused")
        sys.exit(0)

    logger.info("Targets to pause:")
    for target in targets_to_pause:
        campaign_id = target.get("campaignId", "N/A")
        ad_group_id = target.get("adGroupId", "N/A")
        target_id = target.get("targetId", "N/A")
        found_types = target.get("_found_types", [])
        logger.info(f"  - Target {target_id} (Campaign: {campaign_id}, AdGroup: {ad_group_id}) - Types: {found_types}")

    if args.apply:
        logger.info("Applying changes...")
        result = update_targets(targets_to_pause, credentials)
        logger.info(f"Update complete: {result['success']} success, {result['failed']} failed")
    else:
        logger.info("Dry-run mode: no changes applied. Use --apply to apply changes.")


if __name__ == "__main__":
    main()