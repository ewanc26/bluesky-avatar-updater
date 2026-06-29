# Bluesky Avatar Updater

[![No Maintenance Intended](http://unmaintained.tech/badge.svg)](http://unmaintained.tech/)

Rotates your Bluesky avatar and banner every hour. Written in Rust.

## Features

- Updates avatar and banner on an hourly schedule
- Loads config from `.env`
- Logs to file with 14-day rotation
- Self-installs as a cron job

## Requirements

- Rust 1.85+

## Install

```bash
git clone https://github.com/ewanc26/bluesky-avatar-updater.git
cd bluesky-avatar-updater
cargo build --release
```

Create `.env` in `assets/` (or root):

```plaintext
ENDPOINT=https://bsky.social
HANDLE=your_handle.bsky.social
PASSWORD=your_app_password
DID=did:plc:your_did
UPDATE_BANNER=false
```

Create `assets/cids.json` with hourly blob mappings:

```json
{
  "00": { "avatar": "cid_for_midnight", "banner": "banner_cid_for_midnight" },
  "01": { "avatar": "cid_for_1am", "banner": "banner_cid_for_1am" }
}
```

## Usage

```bash
cargo run --release
```

On startup it:

1. Loads config
2. Checks the endpoint is healthy
3. Reads CID mappings from `assets/cids.json`
4. Picks the avatar/banner for the current hour
5. Logs into Bluesky, updates the profile
6. Makes sure an hourly cron job exists

## Files

- `src/main.rs` — Orchestration
- `src/bsky.rs` — Bluesky API + blob handling
- `src/cron.rs` — Cron job management
- `src/utils.rs` — Utilities and env validation
- `assets/cids.json` — Hour-to-CID mappings

## Licence

MIT
