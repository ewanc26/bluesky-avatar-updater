# Bluesky Avatar Updater

## Overview

This repository contains a Python script designed to automatically update your Bluesky avatar based on the current hour. The script uses environment variables for configuration and reads a JSON file of blob CIDs to determine the appropriate avatar. This script was inspired by [@dame.is](https://bsky.app/profile/dame.is)'s blog post ['How I made an automated dynamic avatar for my Bluesky profile'](https://dame.is/blog/how-i-made-an-automated-dynamic-avatar-for-my-bluesky-profile).

The script has been tested and is fully functional. It was developed on macOS but is intended for deployment on Linux.

## Prerequisites

Before running the script, ensure you have the following:

- Python 3.6 or later installed. If using Ubuntu, run `sudo apt update && sudo apt install -y python3 python3-pip python3-dev`
- The required Python packages (automatically installed if missing):
  - `python-dotenv`
  - `atproto`
  - `requests`
  - `python-magic`
  - `python-crontab`
- A valid Bluesky account with the necessary API credentials.

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/ewanc26/bluesky-avatar-updater.git
   cd bluesky-avatar-updater
   ```

2. **Ensure the required package is installed (if necessary):**

   Before creating the virtual environment, make sure that the `python3-venv` package is installed (this is necessary on Debian/Ubuntu systems to create virtual environments).

   ```bash
   sudo apt install python3.10-venv  # Adjust the version if necessary (e.g., python3.9-venv)
   ```

3. **Create a virtual environment and install dependencies:**

   Now, create a new virtual environment and activate it. This isolates the package dependencies for your project.

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

4. **Install dependencies within the virtual environment:**

   With the virtual environment activated, install the required packages listed in the `requirements.txt` file:

   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables:**
   - Place your `.env` file in the `../assets` directory relative to the script.
   - The `.env` file should contain the following entries:

     ```env
     ENDPOINT=your_endpoint
     HANDLE=your_handle
     PASSWORD=your_password (app passwords are recommended)
     DID=your_did
     ```

6. **Prepare the JSON file:**
   - Ensure that a `cids.json` file is located in the `../assets` directory. This file should map each hour (in two-digit format) to a corresponding blob CID. Example:

     ```json
     {
       "00": "cid_for_midnight",
       "01": "cid_for_1am",
       "02": "cid_for_2am"
     }
     ```

## Usage

To run the script, execute:

```bash
python -u ./src/main.py
```

The script will:

- Load the environment configuration from `../assets/.env`.
- Read the blob CIDs from `../assets/cids.json`.
- Determine the current hour and select the appropriate blob CID.
- Authenticate using the AT Protocol.
- Update the Bluesky avatar accordingly.

Execution logs will be displayed directly in the console, and a log file will be created in the `./logs/` directory. The log file will rotate when it reaches 10 MB, keeping up to 5 backup log files, each named with a timestamp for each execution.

## Automating with Cron (Linux)

The script will automatically set up a cron job to run every hour. If you need to manually verify it, run:

```bash
crontab -l
```

If you need to remove or modify the cron job, use:

```bash
crontab -e
```

### Manually Set Up Cron Job

If you wish to manually set up the cron job instead of relying on the script, follow these steps:

1. Open the crontab editor:

   ```bash
   crontab -e
   ```

2. Add the following line to run the script every hour at the top of the hour:

   ```bash
   0 * * * * /path/to/your/.venv/bin/python3 /path/to/bluesky-avatar-updater/src/main.py
   ```

Replace `/path/to/your/.venv/bin/python3` with the path to your virtual environment's Python interpreter and `/path/to/bluesky-avatar-updater/src/main.py` with the full path to the `main.py` script.

## Troubleshooting

- **Environment variables not loading?** Ensure the `.env` file is correctly placed in `../assets/`.
- **Script exits with missing dependencies?** The script will attempt to install missing packages, but you can manually install them using:
  
  ```bash
  pip install -r requirements.txt
  ```

- **Endpoint not responding?** Verify that the Bluesky API endpoint is correct and accessible.
- **Cron job not running?** Verify that the cron job was properly set up using `crontab -l` or set it up manually.

## License

This project is released under the MIT License. See the [LICENSE](./LICENSE) file for full details.
