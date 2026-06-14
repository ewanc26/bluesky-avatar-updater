# Bluesky Avatar Updater

[![No Maintenance Intended](http://unmaintained.tech/badge.svg)](http://unmaintained.tech/)

A Rust tool to automatically rotate your Bluesky profile avatar and banner every hour.

## Features

- **Automated Rotation**: Automatically updates your profile assets every hour.
- **Environment Support**: Loads configuration from `.env` files.
- **Logging**: Robust file logging with 14-day rotation.
- **Cron Integration**: Self-installs as an hourly cron job for persistent updates.
- **Asset Mapping**: Supports detailed hourly CID mapping for both avatar and banner.

## Requirements

To run this project, you will need the following:

- Rust 1.85+ (Cargo)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/ewanc26/bluesky-avatar-updater.git
   cd bluesky-avatar-updater
   ```

2. Build the project:

   ```bash
   cargo build --release
   ```

3. Create a `.env` file in the `assets/` directory (or the root) and add your environment variables:

   ```plaintext
   ENDPOINT=https://bsky.social
   HANDLE=your_handle.bsky.social
   PASSWORD=your_app_password
   DID=did:plc:your_did
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

Run the updater from the repository root:

```bash
cargo run --release
```

On start-up, the script will:

1. Load configuration and environment variables.
2. Confirm the endpoint is healthy.
3. Read the CID mapping from `assets/cids.json`.
4. Select the avatar/banner CID for the current hour.
5. Log in to Bluesky and update the profile record.
6. Ensure an hourly cron job exists for future runs.

## File Structure

- `src/main.rs`: Main orchestration.
- `src/bsky.rs`: Bluesky API and blob handling.
- `src/cron.rs`: Cron job management.
- `src/utils.rs`: Utility functions and environment validation.
- `assets/cids.json`: Mapping of hours to avatar and banner CIDs.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## ☕ Support

If you found this useful, consider [buying me a ko-fi](https://ko-fi.com/ewancroft)!
