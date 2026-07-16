# AGENTS.md

Guidance for agents working on the Rust Bluesky avatar/banner scheduler.

## Architecture

- `src/` handles configuration, hourly CID selection, blob fetching/validation, profile reads/writes, scheduling, cron installation, and rotating logs.
- `assets/cids.json` is operator-provided state and must remain compatible with the documented hour-to-avatar/banner mapping.
- `.env` holds PDS credentials and options; never commit or print it.

## Invariants

- Use UTC/hour semantics consistently and update at most once for a given scheduled interval.
- Read the existing profile and preserve fields not owned by this tool. Avatar-only operation must not erase the banner or other profile data.
- Validate CIDs, MIME types, download bounds, and blob responses before updating the record.
- Use optimistic record revision/swap behavior when available so concurrent profile edits are not overwritten.
- Network and scheduler failures must be logged safely and retried with bounds; never busy-loop.
- Cron installation must be idempotent and must not delete unrelated entries.

## Validation

Run `cargo fmt --check`, `cargo clippy --all-targets --all-features`, and `cargo test`, then `cargo build --release`. Test hour rollover, missing mapping, banner-disabled mode, malformed config, fetch failure, invalid media, concurrent profile change, and graceful shutdown with mocks. Live writes require a dedicated test account and explicit care.
