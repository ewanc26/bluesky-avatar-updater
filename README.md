# Bluesky Avatar Updater

## Overview

This repository contains a Python script intended to update your Bluesky avatar automatically based on the current hour. The script utilises environment variables for configuration and reads a JSON file of blob CIDs to determine the appropriate avatar for each hour. Please note that the implementation is not yet fully operational, as several issues remain to be resolved.

## Prerequisites

Before running the script, ensure you have the following:

- Python 3.6 or later installed.

- The required Python packages:
  - `python-dotenv`
  - `atproto`
  - Standard libraries such as `os`, `json`, `logging`, and `datetime`
- A valid Bluesky account with the necessary API credentials.

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/ewanc26/bluesky-avatar-updater.git
   cd bluesky-avatar-updater
   ```

2. **Create a virtual environment and install dependencies:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Place your `.env` file in the `../assets` directory relative to the script.
   - The `.env` file should contain the following entries:

     ```env
     ENDPOINT=your_endpoint
     HANDLE=your_handle
     PASSWORD=your_password
     ```

4. **Prepare the JSON file:**
   - Ensure that a `cids.json` file is located in the `../assets` directory. This file should map each hour (in two-digit format) to a corresponding blob CID.

## Usage

To run the script, execute:

```bash
python -u ./src/main.py
```

The script will:

- Load the environment configuration from `./assets/.env`.
- Read the blob CIDs from `./assets/cids.json`.
- Determine the current hour and select the appropriate blob CID.
- Attempt to authenticate and update the avatar using the AT Protocol.

Execution logs will be recorded in `avatar_update.log` for your review.

## Known Issues

At present, the script isn’t fully working. We’ve noticed an error when updating the profile—specifically, the `put_record()` method is missing a required parameter. There have also been occasional authentication hiccoughs, which might be due to configuration issues or [API](https://atproto.blue) quirks.

If you’re keen to help sort these out or have ideas for improvements, please open a Pull Request. Your contributions are very welcome!

---

## Licence

This project is released under the MIT Licence. See the [LICENSE](./LICENSE) file for full details.
