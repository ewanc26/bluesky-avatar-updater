# AGENTS.md

Guidance for agents working on the unmaintained Rust Bluesky avatar/banner updater.

## Current implementation

- `main.rs` resolves `assets/`, `logs/`, and config from the process current directory, installs cron before validating config, uses the host's local hour (`chrono::Local`) to select a zero-padded `cids.json` key, performs one update, and exits.
- `bsky.rs` downloads the full existing blob through `com.atproto.sync.getBlob` to infer MIME type and size; it does not upload image bytes.
- `cron.rs` preserves the current crontab and appends `0 * * * * <current executable>` when that path is absent. Daily tracing files are created, but code does not implement the README's claimed 14-day retention.
- Root `.env` loads first and `assets/.env` may supplement it. `ENDPOINT`, `HANDLE`, `PASSWORD`, and `DID` are required; `UPDATE_BANNER` is true only for case-insensitive `true`.

## Invariants

- Preserve local-time semantics unless a UTC migration updates deployed mappings and docs.
- Bound blob downloads and validate CID/MIME/status before writing.
- A successful profile read preserves all decoded fields and supplies its CID as `swap_record`. Any read error currently falls back to a blank profile and can erase metadata; distinguish not-found from transient/auth/parse failures before retaining that behavior.
- Cron setup must preserve unrelated jobs, quote paths safely, and avoid installing a broken job before config validation.
- Never commit `.env`, `assets/cids.json` with private deployment data, or logs.

## Validation

Run `cargo fmt --check`, `cargo clippy --all-targets --all-features`, `cargo test`, and `cargo build --release`. Use controlled working directories with mocked HTTP/agent/crontab behavior to cover env precedence, local-hour lookup, missing/malformed maps, endpoint health, blob timeout/status/type/size, banner modes, profile-read failure classes, swap conflicts, crontab preservation, and executable paths with spaces. Live writes require a dedicated account.
