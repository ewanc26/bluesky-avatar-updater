import os
import json
import logging
import requests
import magic
from datetime import datetime
from dotenv import load_dotenv
from atproto import Client, models
from atproto.exceptions import BadRequestError

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


def ensure_https(url):
    if not url.startswith("http://") and not url.startswith("https://"):
        return "https://" + url
    if url.startswith("http://"):
        return "https://" + url[7:]
    return url


def is_endpoint_alive(url):
    health_url = f"{url.rstrip('/')}/xrpc/_health"
    try:
        response = requests.get(health_url, timeout=5)
        return response.status_code == 200
    except requests.RequestException as e:
        logging.error(f"Health check failed for {health_url}: {e}")
        return False


def fetch_blob(did, cid, endpoint):
    url = f"{endpoint}/xrpc/com.atproto.sync.getBlob?did={did}&cid={cid}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        logging.error(f"Failed to fetch blob {cid} for DID {did}: {e}")
        return None


def get_blob_metadata(cid, did, endpoint):
    blob_data = fetch_blob(did, cid, endpoint)
    if blob_data is None:
        return None

    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(blob_data)
    size = len(blob_data)
    
    return {
        "$type": "blob",
        "ref": {"$link": cid},
        "mimeType": mime_type,
        "size": size,
    }

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
    did = os.getenv("DID")

    if not (endpoint and handle and password and did):
        logging.error(
            "Missing environment variables. Ensure ENDPOINT, HANDLE, PASSWORD, and DID are set in .env file."
        )
        return

    endpoint = ensure_https(endpoint)
    if not is_endpoint_alive(endpoint):
        logging.error(f"Endpoint {endpoint} is not responding.")
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
        client.login(handle, password)
        logging.info("Authentication successful.")
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        return

    try:
        current_profile_record = client.app.bsky.actor.profile.get(
            client.me.did, "self"
        )
        current_profile = current_profile_record.value
        swap_record_cid = current_profile_record.cid
    except BadRequestError:
        current_profile = swap_record_cid = None

    old_description = old_display_name = None
    if current_profile:
        old_description = current_profile.description
        old_display_name = current_profile.display_name

    blob_metadata = get_blob_metadata(new_blob_cid, did, endpoint)

    if blob_metadata is None:
        logging.error(f"Could not retrieve metadata for blob CID: {new_blob_cid}")
        return

    try:
        client.com.atproto.repo.put_record(
            models.ComAtprotoRepoPutRecord.Data(
                collection=models.ids.AppBskyActorProfile,
                repo=client.me.did,
                rkey="self",
                swap_record=swap_record_cid,
                record=models.AppBskyActorProfile.Record(
                    avatar=blob_metadata,
                    banner=current_profile.banner if current_profile else None,
                    description=old_description,
                    display_name=old_display_name,
                ),
            )
        )
        logging.info("Avatar updated successfully!")
    except Exception as e:
        logging.error(f"Failed to update profile record: {e}")


if __name__ == "__main__":
    main()
