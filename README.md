# Bluesky Avatar Updater

**_This repository is available on [GitHub](https://github.com/ewanc26/bluesky-avatar-updater) and [Tangled](https://tangled.sh/did:plc:ofrbh253gwicbkc5nktqepol/bluesky-avatar-updater). GitHub is the primary version, and the Tangled version is a mirror._**

## Overview

This repository contains a Python script that updates a Bluesky profile avatar, and optionally a banner, based on the current hour. It looks up blob CIDs in `assets/cids.json`, fetches the blobs from the configured endpoint, and updates the profile record through the AT Protocol.

The script also performs a health check against the endpoint, writes logs to `logs/update.log`, rotates logs every 14 days with up to 5 backups, removes old logs older than 30 days at startup, and installs an hourly cron job so the update runs automatically.

This project was inspired by [@dame.is](https://bsky.app/profile/dame.is)'s blog post ['How I made an automated dynamic avatar for my Bluesky profile'](https://dame.is/blog/how-i-made-an-automated-dynamic-avatar-for-my-bluesky-profile).

> 🧶 Also available on [Tangled](https://tangled.org/ewancroft.uk/bluesky-avatar-updater)

## Requirements

- Python 3.6 or later
- A virtual environment
- Python packages from `requirements.txt`
- A valid Bluesky account with app password access
- A working AT Protocol endpoint that serves the blobs referenced in `cids.json`

Install the Python dependencies with:

```bash
pip install -r requirements.txt
```

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/ewanc26/bluesky-avatar-updater.git
   cd bluesky-avatar-updater
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Create `assets/.env` with:

   ```env
   ENDPOINT=your_endpoint
   HANDLE=your_handle
   PASSWORD=your_app_password
   DID=your_did
   UPDATE_BANNER=false
   ```

4. Create `assets/cids.json` with hourly blob mappings:

   ```json
   {
     "00": {
       "avatar": "cid_for_midnight",
       "banner": "banner_cid_for_midnight"
     },
     "01": { "avatar": "cid_for_1am", "banner": "banner_cid_for_1am" }
   }
   ```

## Usage

Run the updater from the repository root while the virtual environment is active:

```bash
python -u ./src/main.py
```

On start-up, the script will:

1. Verify that it is running inside a virtual environment
2. Load `assets/.env`
3. Confirm the endpoint is healthy
4. Read the CID mapping from `assets/cids.json`
5. Select the avatar CID for the current hour
6. Log in to Bluesky and update the profile record
7. Ensure an hourly cron job exists for future runs

## Notes

- `UPDATE_BANNER=true` enables banner updates when a banner CID is present for the current hour.
- The endpoint value is normalised to HTTPS if necessary.
- The script expects the endpoint to support `/_health` and `com.atproto.sync.getBlob`.

## Troubleshooting

- If the script exits immediately, double-check that the virtual environment is active.
- If authentication fails, confirm the handle and app password are correct.
- If blob fetching fails, make sure the endpoint can access the DID/CID pair in `cids.json`.
- If cron does not install, verify that `python-crontab` is available in the virtual environment.

## License

This project is released under the MIT License. Please refer to the [LICENSE](./LICENSE) file for full details.

## ☕ Support

If you found this useful, consider [buying me a ko-fi](https://ko-fi.com/ewancroft)!
