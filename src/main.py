#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from atproto import Client, models

# Define the paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "../assets")
ENV_PATH = os.path.join(ASSETS_DIR, ".env")
JSON_PATH = os.path.join(ASSETS_DIR, "cids.json")

# Configure logging
logging.basicConfig(
    filename="avatar_update.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

def main():
    logging.info("Starting avatar update script...")

    if os.path.exists(ENV_PATH):
        load_dotenv(ENV_PATH)
    else:
        logging.error(f"Missing .env file at {ENV_PATH}")
        return

    endpoint = os.getenv("ENDPOINT")
    handle = os.getenv("HANDLE")
    password = os.getenv("PASSWORD")

    if not (endpoint and handle and password):
        logging.error("Missing environment variables. Ensure ENDPOINT, HANDLE, and PASSWORD are set in .env file.")
        return

    try:
        with open(JSON_PATH, "r") as f:
            blob_dict = json.load(f)
        logging.debug(f"Loaded blob CIDs from {JSON_PATH}: {blob_dict}")
    except Exception as e:
        logging.error(f"Error loading cids.json from {JSON_PATH}: {e}")
        return

    current_hour = datetime.now().strftime("%H")
    logging.info(f"Current hour: {current_hour}")
    new_blob_cid = blob_dict.get(current_hour)
    if not new_blob_cid:
        logging.warning(f"No blob CID found for hour {current_hour}")
        return
    logging.info(f"Selected blob CID: {new_blob_cid}")

    client = Client(endpoint)

    try:
        profile = client.login(handle, password)
        logging.info(f"Authentication successful. Welcome, {profile.display_name}")
        did = profile.did
        logging.info(f"User DID: {did}")
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        return

    updated_profile_data = {
        "$type": "app.bsky.actor.profile",
        "avatar": {
            "cid": new_blob_cid
        }
    }

    logging.debug(f"Updated profile data: {updated_profile_data}")

    try:
        client.com.atproto.repo.put_record(
            repo=did,
            collection="app.bsky.actor.profile",
            rkey="self",
            record=updated_profile_data
        )
        logging.info("Avatar updated successfully!")
    except Exception as e:
        logging.error(f"Failed to update profile record: {e}")

if __name__ == "__main__":
    main()
