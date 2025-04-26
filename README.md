# Bluesky Avatar Updater

***This repository is available on [GitHub](https://github.com/ewanc26/bluesky-avatar-updater) and [Tangled](https://tangled.sh/did:plc:ofrbh253gwicbkc5nktqepol/bluesky-avatar-updater). GitHub is the primary version, and the Tangled version is a mirror.***

## Overview

This repository contains a Python script that automatically updates your Bluesky avatar (and, optionally, your banner) based on the current hour. The script utilises environment variables for configuration and reads a JSON file mapping blob CIDs to specific hours. In addition to updating your avatar, the script performs several supportive functions including a health check of the API endpoint, comprehensive logging (both to console and to a rotating file system that deletes logs older than 30 days), and the automatic setup of a cron job to ensure regular updates. This project was inspired by [@dame.is](https://bsky.app/profile/dame.is)'s blog post ['How I made an automated dynamic avatar for my Bluesky profile'](https://dame.is/blog/how-i-made-an-automated-dynamic-avatar-for-my-bluesky-profile).

Developed primarily on macOS and intended for Linux deployment, this tool is designed to run within a virtual environment to isolate dependencies and ensure smooth operation.

## Prerequisites

Before running the script, please ensure you have the following:

- Python 3.6 or later installed. For Ubuntu, run:

  ```bash
  sudo apt update && sudo apt install -y python3 python3-pip python3-dev
  ```

- The following Python packages (automatically installed if missing):
  - `python-dotenv`
  - `atproto`
  - `requests`
  - `python-magic`
  - `python-crontab`
- A valid Bluesky account with the necessary API credentials.
- The script must be executed within a virtual environment.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/ewanc26/bluesky-avatar-updater.git
   cd bluesky-avatar-updater
   ```

2. **Ensure Virtual Environment Support:**
   On Debian/Ubuntu systems, ensure that the `python3-venv` package is installed:

   ```bash
   sudo apt install python3-venv  # Adjust the version if necessary (e.g., python3.10-venv)
   ```

3. **Create and Activate a Virtual Environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

4. **Install Dependencies:**
   With the virtual environment activated, install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

5. **Configure Environment Variables:**
   - Place your `.env` file in the `assets` directory.
   - The `.env` file should contain the following entries:

     ```env
     ENDPOINT=your_endpoint
     HANDLE=your_handle
     PASSWORD=your_password  # App passwords are recommended
     DID=your_did
     UPDATE_BANNER=true      # Set to 'true' to update the banner, or 'false' otherwise
     ```

6. **Prepare the JSON File:**
   Ensure that a `cids.json` file is located in the `assets` directory. This file should map each hour (in two-digit format) to the corresponding blob CIDs for the avatar (and optionally, the banner). For example:

   ```json
   {
     "00": { "avatar": "cid_for_midnight", "banner": "banner_cid_for_midnight" },
     "01": { "avatar": "cid_for_1am", "banner": "banner_cid_for_1am" }
   }
   ```

## Usage

To run the script, execute:

```bash
python -u ./src/main.py
```

Upon execution, the script will:

- Verify that it is running within a virtual environment.
- Load environment variables from the `.env` file located in the `assets` directory.
- Read the blob CIDs from the `cids.json` file.
- Determine the current hour and select the appropriate blob CIDs.
- Perform a health check on the provided API endpoint.
- Authenticate using the AT Protocol and update your Bluesky profile with the new avatar (and banner, if enabled).
- Automatically set up a cron job to run the script every hour.
- Log activity to both the console and a rotating log file in the `logs` directory. The log file rotates every 14 days (with up to 5 backups) and automatically deletes files older than 30 days.

## Automating with Cron (Linux)

The script is designed to automatically configure a cron job to run at the top of every hour. To verify the cron job, use:

```bash
crontab -l
```

If you prefer to manually set up or modify the cron job, follow these steps:

1. Open the crontab editor:

   ```bash
   crontab -e
   ```

2. Add the following line (adjusting paths as necessary):

   ```bash
   0 * * * * /path/to/your/.venv/bin/python3 /path/to/bluesky-avatar-updater/src/main.py
   ```

## Troubleshooting

- **Virtual Environment Issues:** The script will exit if it is not run within a virtual environment. Ensure you activate your virtual environment before running the script.
- **Environment Variables Not Loading:** Verify that the `.env` file is correctly placed in the `assets` directory and contains all required entries.
- **Missing Dependencies:** If the script encounters missing packages, run:

  ```bash
  pip install -r requirements.txt
  ```

  within your virtual environment.
- **Endpoint Issues:** Ensure that the provided API endpoint is correct and accessible. The script performs a health check and will log an error if the endpoint is unresponsive.
- **Cron Job Not Running:** If the cron job is not automatically set up, check with `crontab -l` or set it up manually using `crontab -e`.
- **Log File Management:** The script manages log rotation and deletion automatically. If logs are not being deleted as expected, verify the file permissions in the `logs` directory.

## License

This project is released under the MIT License. Please refer to the [LICENSE](./LICENSE) file for full details.
