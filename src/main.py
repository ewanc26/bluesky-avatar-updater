import os
import json
import logging
import requests
import magic
from datetime import datetime
from dotenv import load_dotenv
from atproto import Client, models
from atproto.exceptions import BadRequestError
import sys
from crontab import CronTab

# Ensure the script is run inside a virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("Error: This script must be run inside a virtual environment.")
    sys.exit(1)
else:
    logging.info("Virtual environment detected.")

# Define the paths
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ENV_PATH = os.path.join(ASSETS_DIR, ".env")
JSON_PATH = os.path.join(ASSETS_DIR, "cids.json")
SCRIPT_PATH = os.path.abspath(__file__)

# Configure basic console logging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Show only INFO and higher levels on console
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

# Root logger setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Set the root logger level to INFO

# Remove default handlers (to prevent duplication)
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Add the custom console handler
logger.addHandler(console_handler)

# Suppress httpx logging (this stops httpx internal logs)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Suppress INFO and DEBUG logs from httpx

# Log the start of the script
logger.info("Avatar update script started.")

def ensure_https(url):
    """Ensure the URL starts with https://."""
    if not url.startswith("http://") and not url.startswith("https://"):
        return "https://" + url
    if url.startswith("http://"):
        return "https://" + url[7:]
    return url

def is_endpoint_alive(url):
    """Check if the provided endpoint is alive by making a health check request."""
    health_url = f"{url.rstrip('/')}/xrpc/_health"
    try:
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            logger.info(f"Endpoint {url} is alive and healthy.")
            return True
        else:
            logger.warning(f"Endpoint {url} is not responding correctly: {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"Health check failed for {health_url}: {e}")
        return False

def fetch_blob(did, cid, endpoint):
    """Fetch the blob from the endpoint."""
    url = f"{endpoint}/xrpc/com.atproto.sync.getBlob?did={did}&cid={cid}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logger.info(f"Fetched blob {cid} successfully.")
        return response.content
    except requests.RequestException as e:
        logger.error(f"Failed to fetch blob {cid} for DID {did}: {e}")
        return None

def get_blob_metadata(cid, did, endpoint):
    """Get the metadata for the blob."""
    try:
        logger.info(f"Retrieving metadata for blob {cid}.")
        blob_data = fetch_blob(did, cid, endpoint)
        if blob_data is None:
            return None

        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(blob_data)
        size = len(blob_data)

        logger.debug(f"Blob metadata: MIME Type - {mime_type}, Size - {size}")
        return {
            "$type": "blob",
            "ref": {"$link": cid},
            "mimeType": mime_type,
            "size": size,
        }
    except Exception as e:
        logger.error(f"Error retrieving metadata for blob {cid}: {e}")
        return None

def validate_environment_variables():
    """Validate environment variables and return a dictionary of values."""
    endpoint = os.getenv("ENDPOINT")
    handle = os.getenv("HANDLE")
    password = os.getenv("PASSWORD")
    did = os.getenv("DID")

    if not all([endpoint, handle, password, did]):
        logger.error("Missing environment variables. Ensure ENDPOINT, HANDLE, PASSWORD, and DID are set in .env file.")
        return None
    return {
        "endpoint": endpoint,
        "handle": handle,
        "password": password,
        "did": did
    }

def setup_cron_job():
    """Set up the cron job to run every hour."""
    # Get the path to the virtual environment's Python interpreter
    venv_python = os.path.join(BASE_DIR, ".venv", "bin", "python3")

    # Check if the cron job already exists
    cron = CronTab(user=True)
    job_exists = False
    for job in cron:
        if SCRIPT_PATH in job.command:
            job_exists = True
            break

    if not job_exists:
        # Set up the cron job to run every hour (top of the hour)
        cron_command = f"{venv_python} {SCRIPT_PATH} # Avatar update script"
        job = cron.new(command=cron_command, comment="Avatar update script")
        job.minute.on(0)  # Run at the start of every hour
        cron.write()
        logger.info("Cron job has been set up to run every hour within the virtual environment.")
    else:
        logger.info("Cron job already exists.")

def main():
    """Main function to run the avatar update process."""
    # Set up the cron job (only once)
    setup_cron_job()

    logger.info("Starting avatar update process...")

    # Load environment variables from the .env file
    if os.path.exists(ENV_PATH):
        load_dotenv(ENV_PATH)
        logger.info(f"Loaded environment from {ENV_PATH}")
    else:
        logger.error(f"Missing .env file at {ENV_PATH}")
        return

    env_vars = validate_environment_variables()
    if not env_vars:
        return

    # Ensure endpoint URL is correct and alive
    endpoint = ensure_https(env_vars["endpoint"])
    if not is_endpoint_alive(endpoint):
        logger.error(f"Endpoint {endpoint} is not responding.")
        return

    # Load the CID mapping from the JSON file
    try:
        with open(JSON_PATH, "r") as f:
            blob_dict = json.load(f)
        logger.info(f"Loaded blob CIDs from {JSON_PATH}.")
    except Exception as e:
        logger.error(f"Error loading cids.json from {JSON_PATH}: {e}")
        return

    # Determine the blob CID for the current hour
    current_hour = datetime.now().strftime("%H")
    logger.info(f"Current hour: {current_hour}")
    
    new_blob_cid = blob_dict.get(current_hour)
    if not new_blob_cid:
        logger.warning(f"No blob CID found for hour {current_hour}")
        return

    logger.info(f"Selected blob CID: {new_blob_cid}")

    # Authenticate with the endpoint
    client = Client(endpoint)
    try:
        client.login(env_vars["handle"], env_vars["password"])
        logger.info("Authentication successful.")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return

    # Fetch the current profile and update it with the new avatar
    try:
        current_profile_record = client.app.bsky.actor.profile.get(
            client.me.did, "self"
        )
        current_profile = current_profile_record.value
        swap_record_cid = current_profile_record.cid
        logger.info(f"Current profile record fetched successfully.")
    except BadRequestError:
        current_profile = swap_record_cid = None
        logger.warning(f"Failed to fetch current profile record.")

    old_description = old_display_name = None
    if current_profile:
        old_description = current_profile.description
        old_display_name = current_profile.display_name

    blob_metadata = get_blob_metadata(new_blob_cid, env_vars["did"], endpoint)

    if blob_metadata is None:
        logger.error(f"Could not retrieve metadata for blob CID: {new_blob_cid}")
        return

    # Update the profile with the new avatar
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
        logger.info(f"Avatar updated successfully with CID: {new_blob_cid}")
    except Exception as e:
        logger.error(f"Failed to update profile record: {e}")

if __name__ == "__main__":
    main()