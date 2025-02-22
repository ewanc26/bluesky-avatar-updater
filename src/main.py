#!/usr/bin/env python3
import os
import sys
import subprocess
import logging
import json
import requests
import magic
from datetime import datetime
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from atproto import Client, models
from atproto.exceptions import BadRequestError

# Ensure the script is run inside a virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("Error: This script must be run inside a virtual environment.")
    sys.exit(1)
else:
    print("Virtual environment detected.")

# Define paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # /src/
REQ_PATH = os.path.abspath(os.path.join(BASE_DIR, "../requirements.txt"))  # /requirements.txt
ASSETS_DIR = os.path.join(BASE_DIR, "../assets")
ENV_PATH = os.path.join(ASSETS_DIR, ".env")
JSON_PATH = os.path.join(ASSETS_DIR, "cids.json")
LOG_PATH = os.path.join(BASE_DIR, "logs", "avatar_update.log")

# Ensure necessary directories exist
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Configure logging with log rotation (5MB per file, keeps last 5 logs)
log_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5)
log_handler.setLevel(logging.DEBUG)
log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
log_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_formatter)

logging.basicConfig(level=logging.DEBUG, handlers=[log_handler, console_handler])
logging.info("Starting script with log rotation enabled.")

def install_and_rerun():
    """Install missing packages from requirements.txt and re-run the script."""
    if os.path.exists(REQ_PATH):
        logging.info(f"Installing missing packages from {REQ_PATH}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQ_PATH])
            logging.info("Packages installed successfully. Restarting script...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to install packages: {e}")
            sys.exit(1)
    else:
        logging.error(f"requirements.txt not found at {REQ_PATH}, cannot install missing packages.")
        sys.exit(1)

# Check for required packages and install if missing
try:
    import requests
    import magic
    from atproto import Client, models
    from atproto.exceptions import BadRequestError
    from dotenv import load_dotenv
except ImportError as e:
    logging.error(f"Missing package(s): {e}")
    install_and_rerun()

def ensure_https(url):
    """Ensure the URL starts with https://"""
    if not url.startswith("http://") and not url.startswith("https://"):
        return "https://" + url
    if url.startswith("http://"):
        return "https://" + url[7:]
    return url

def is_endpoint_alive(url):
    """Check if the endpoint is alive by making a health check request."""
    health_url = f"{url.rstrip('/')}/xrpc/_health"
    logging.info(f"Checking endpoint health: {health_url}")
    try:
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            logging.info("Endpoint is alive.")
            return True
        else:
            logging.warning(f"Endpoint returned status code {response.status_code}")
            return False
    except requests.RequestException as e:
        logging.error(f"Health check failed for {health_url}: {e}")
        return False

def fetch_blob(did, cid, endpoint):
    """Fetch blob data from the given endpoint."""
    url = f"{endpoint}/xrpc/com.atproto.sync.getBlob?did={did}&cid={cid}"
    logging.info(f"Fetching blob: {url}")
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        logging.info(f"Successfully fetched blob {cid} for DID {did}.")
        return response.content
    except requests.RequestException as e:
        logging.error(f"Failed to fetch blob {cid} for DID {did}: {e}")
        return None

def get_blob_metadata(cid, did, endpoint):
    """Retrieve metadata for a given blob CID."""
    blob_data = fetch_blob(did, cid, endpoint)
    if blob_data is None:
        logging.error("Blob data is empty.")
        return None

    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(blob_data)
    size = len(blob_data)
    
    logging.info(f"Retrieved metadata - MIME Type: {mime_type}, Size: {size} bytes")
    
    return {
        "$type": "blob",
        "ref": {"$link": cid},
        "mimeType": mime_type,
        "size": size,
    }

def setup_cron_job():
    """Set up a cron job to run the script hourly."""
    cron_job_command = f"0 * * * * {sys.executable} {os.path.abspath(__file__)} >> {LOG_PATH} 2>&1"
    logging.info("Setting up cron job...")

    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        cron_jobs = result.stdout.strip() if result.returncode == 0 else ""

        if cron_job_command in cron_jobs:
            logging.info("Cron job is already set.")
            return

        new_cron_jobs = cron_jobs + "\n" + cron_job_command if cron_jobs else cron_job_command
        subprocess.run(["crontab"], input=new_cron_jobs, text=True, check=True)
        logging.info("Cron job added successfully.")
    except Exception as e:
        logging.error(f"Failed to set up cron job: {e}")

def main():
    logging.info("Starting avatar update script...")

    if not os.path.exists(ENV_PATH):
        logging.error(f"Missing .env file at {ENV_PATH}")
        return
    load_dotenv(ENV_PATH)
    logging.info("Loaded .env file successfully.")

    endpoint = os.getenv("ENDPOINT")
    handle = os.getenv("HANDLE")
    password = os.getenv("PASSWORD")
    did = os.getenv("DID")

    if not (endpoint and handle and password and did):
        logging.error("Missing environment variables. Check .env file.")
        return

    endpoint = ensure_https(endpoint)
    if not is_endpoint_alive(endpoint):
        logging.error(f"Endpoint {endpoint} is not responding.")
        return

    if not os.path.exists(JSON_PATH) or os.path.getsize(JSON_PATH) == 0:
        logging.error(f"Error: {JSON_PATH} is missing or empty.")
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

    blob_metadata = get_blob_metadata(new_blob_cid, did, endpoint)
    if blob_metadata is None:
        logging.error("Blob metadata retrieval failed.")
        return

    try:
        client.com.atproto.repo.put_record(
            models.ComAtprotoRepoPutRecord.Data(
                collection=models.ids.AppBskyActorProfile,
                repo=client.me.did,
                rkey="self",
                record=models.AppBskyActorProfile.Record(
                    avatar=blob_metadata,
                ),
            )
        )
        logging.info("Avatar updated successfully!")
    except Exception as e:
        logging.error(f"Failed to update profile record: {e}")

if __name__ == "__main__":
    setup_cron_job()
    main()