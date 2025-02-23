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
from logging.handlers import TimedRotatingFileHandler
import glob
import time

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

# Define the log file directory and log file path
log_dir = os.path.join(BASE_DIR, "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

def cleanup_old_logs(log_directory, days=30):
    """Deletes log files older than the specified number of days."""
    cutoff = time.time() - (days * 86400)  # Convert days to seconds
    for log_file in glob.glob(os.path.join(log_directory, "update.log")):
        if os.path.isfile(log_file) and os.path.getmtime(log_file) < cutoff:
            os.remove(log_file)
            print(f"Deleted old log: {log_file}")

# Cleanup logs older than 30 days before setting up new logging
cleanup_old_logs(log_dir, days=30)

# Use a fixed log file name for the current log; TimedRotatingFileHandler will manage rotations.
log_file_path = os.path.join(log_dir, "update.log")

# Configure logging to both console and file with bi-weekly rotation
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Show only INFO and higher levels on console

# Create a timed rotating file handler (rotate every 14 days, keep up to 5 backups)
file_handler = TimedRotatingFileHandler(
    log_file_path,
    when="D",        # 'D' stands for days
    interval=14,     # Rotate every 14 days
    backupCount=5
)
file_handler.setLevel(logging.INFO)  # Save all logs to file

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Root logger setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Set the root logger level to INFO

# Remove default handlers (to prevent duplication)
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Add the custom handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Suppress httpx logging (this stops httpx internal logs)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Suppress INFO and DEBUG logs from httpx

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
    update_banner = os.getenv("UPDATE_BANNER", "false").lower() == "true"

    if not all([endpoint, handle, password, did]):
        logger.error("Missing environment variables. Ensure ENDPOINT, HANDLE, PASSWORD, and DID are set in .env file.")
        return None
    return {
        "endpoint": endpoint,
        "handle": handle,
        "password": password,
        "did": did,
        "update_banner": update_banner
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
        cron_command = f"{venv_python} {SCRIPT_PATH}"
        job = cron.new(command=cron_command, comment="Avatar update script")
        job.minute.on(0)  # Run at the start of every hour
        cron.write()
        logger.info("Cron job has been set up to run every hour within the virtual environment.")
    else:
        logger.info("Cron job already exists.")

def main():
    """Main function to run the avatar and banner update process."""
    # Set up the cron job (only once)
    try:
        setup_cron_job()
    except Exception as e:
        logger.error(f"Error setting cron job: {e}")
        pass

    logger.info("Script started.")
    logger.info("Starting update process...")

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

    # Determine the blob CIDs for the current hour from the modified structure
    current_hour = datetime.now().strftime("%H")
    logger.info(f"Current hour: {current_hour}")

    current_entry = blob_dict.get(current_hour)
    if not current_entry:
        logger.warning(f"No entry found for hour {current_hour} in cids.json")
        return

    new_avatar_cid = current_entry.get("avatar")
    new_banner_cid = current_entry.get("banner") if env_vars["update_banner"] else None

    if not new_avatar_cid:
        logger.warning(f"No avatar CID found for hour {current_hour}")
        return

    logger.info(f"Selected avatar CID: {new_avatar_cid}")
    if env_vars["update_banner"]:
        if new_banner_cid:
            logger.info(f"Selected banner CID: {new_banner_cid}")
        else:
            logger.warning(f"UPDATE_BANNER is enabled, but no banner CID found for hour {current_hour}")

    # Authenticate with the endpoint
    client = Client(endpoint)
    try:
        client.login(env_vars["handle"], env_vars["password"])
        logger.info("Authentication successful.")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return

    # Fetch the current profile and update it with the new avatar (and optionally banner)
    try:
        current_profile_record = client.app.bsky.actor.profile.get(
            client.me.did, "self"
        )
        current_profile = current_profile_record.value
        swap_record_cid = current_profile_record.cid
        logger.info("Current profile record fetched successfully.")
    except BadRequestError:
        current_profile = swap_record_cid = None
        logger.warning("Failed to fetch current profile record.")

    old_description = current_profile.description if current_profile else None
    old_display_name = current_profile.display_name if current_profile else None
    old_banner = current_profile.banner if current_profile else None

    avatar_metadata = get_blob_metadata(new_avatar_cid, env_vars["did"], endpoint)
    if avatar_metadata is None:
        logger.error(f"Could not retrieve metadata for avatar blob CID: {new_avatar_cid}")
        return

    banner_metadata = None
    if env_vars["update_banner"] and new_banner_cid:
        banner_metadata = get_blob_metadata(new_banner_cid, env_vars["did"], endpoint)
        if banner_metadata is None:
            logger.warning(f"Could not retrieve metadata for banner blob CID: {new_banner_cid}")
            banner_metadata = old_banner
    else:
        banner_metadata = old_banner

    # Update the profile with the new avatar and optionally the new banner
    try:
        client.com.atproto.repo.put_record(
            models.ComAtprotoRepoPutRecord.Data(
                collection=models.ids.AppBskyActorProfile,
                repo=client.me.did,
                rkey="self",
                swap_record=swap_record_cid,
                record=models.AppBskyActorProfile.Record(
                    avatar=avatar_metadata,
                    banner=banner_metadata,
                    description=old_description,
                    display_name=old_display_name,
                ),
            )
        )
        if env_vars["update_banner"] and new_banner_cid:
            logger.info(f"Profile updated successfully with avatar CID {new_avatar_cid} and banner CID {new_banner_cid}")
        else:
            logger.info(f"Profile updated successfully with avatar CID: {new_avatar_cid}")
    except Exception as e:
        logger.error(f"Failed to update profile record: {e}")

if __name__ == "__main__":
    main()