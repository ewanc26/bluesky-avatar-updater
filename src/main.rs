//! Hourly Bluesky avatar and banner rotator.
//!
//! Reads a CID-per-hour mapping from `assets/cids.json`, picks the current hour's
//! entry, and writes it to the user's Bluesky profile.  Designed to be run once
//! and self-install as a cron job so subsequent rotations happen unattended.

mod bsky;
mod cron;
mod utils;

use anyhow::{Result, Context, anyhow};
use bsky_sdk::BskyAgent;
use bsky_sdk::agent::config::Config;
use chrono::Local;
use dotenvy::dotenv;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs;
use tracing::{info, error, warn};
use tracing_subscriber::{fmt, prelude::*, EnvFilter};
use atrium_api::app::bsky::actor::profile::{Record, RecordData};
use atrium_api::types::{BlobRef, TypedBlobRef, Unknown};

// ─── Data Structures ─────────────────────────────────

#[derive(Serialize, Deserialize, Debug)]
struct HourEntry {
    avatar: String,
    banner: Option<String>,
}

// ─── Entry Point ─────────────────────────────────────

#[tokio::main]
async fn main() -> Result<()> {
    // ── Setup ────────────────────────────────────────

    let base_dir = env::current_dir()?;
    let assets_dir = base_dir.join("assets");
    let json_path = assets_dir.join("cids.json");
    let log_dir = base_dir.join("logs");

    if !log_dir.exists() {
        fs::create_dir_all(&log_dir)?;
    }

    // ── Tracing ──────────────────────────────────────
    // File logs roll daily; stdout keeps a live view for terminal runs.
    let file_appender = tracing_appender::rolling::daily(&log_dir, "update.log");
    let (non_blocking, _guard) = tracing_appender::non_blocking(file_appender);

    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info"));

    tracing_subscriber::registry()
        .with(filter)
        .with(fmt::layer().with_writer(std::io::stdout))
        .with(fmt::layer().with_writer(non_blocking).with_ansi(false))
        .init();

    info!("Script started.");

    // ── Environment & Health ─────────────────────────
    // Self-install the cron entry so the binary only needs one manual launch.
    cron::setup_cron_job();

    dotenv().ok();
    // The original Python script checked assets/.env separately — preserve that
    // path for backwards-compatibility with existing deployments.
    let env_path = assets_dir.join(".env");
    if env_path.exists() {
        dotenvy::from_path(&env_path).ok();
        info!("Loaded environment from {:?}", env_path);
    }

    let env_vars = match utils::validate_environment_variables() {
        Some(v) => v,
        None => return Ok(()),
    };

    let endpoint = utils::ensure_https(&env_vars.endpoint);
    if !utils::is_endpoint_alive(&endpoint).await {
        error!("Endpoint {} is not responding.", endpoint);
        return Ok(());
    }

    // ── CID Lookup ──────────────────────────────────

    let blob_dict: HashMap<String, HourEntry> = if json_path.exists() {
        let content = fs::read_to_string(&json_path)?;
        serde_json::from_str(&content).context("Failed to parse cids.json")?
    } else {
        error!("Missing cids.json at {:?}", json_path);
        return Ok(());
    };

    // Pick the CID whose key matches the current hour (00-23).
    let current_hour = Local::now().format("%H").to_string();
    info!("Current hour: {}", current_hour);

    let current_entry = match blob_dict.get(&current_hour) {
        Some(entry) => entry,
        None => {
            warn!("No entry found for hour {} in cids.json", current_hour);
            return Ok(());
        }
    };

    let new_avatar_cid = &current_entry.avatar;
    let new_banner_cid = current_entry.banner.as_ref();

    info!("Selected avatar CID: {}", new_avatar_cid);
    if env_vars.update_banner {
        if let Some(bcid) = new_banner_cid {
            info!("Selected banner CID: {}", bcid);
        }
    }

    // ── Auth ─────────────────────────────────────────

    let agent = BskyAgent::builder()
        .config(Config {
            endpoint: endpoint.clone(),
            ..Default::default()
        })
        .build()
        .await?;

    agent.login(env_vars.handle.clone(), env_vars.password.clone()).await?;
    info!("Authentication successful.");

    // ── Read Current Profile ─────────────────────────

    let me = agent.api.com.atproto.repo.get_record(
        atrium_api::com::atproto::repo::get_record::ParametersData {
            collection: "app.bsky.actor.profile".parse().map_err(|e| anyhow!("{:?}", e))?,
            repo: env_vars.did.clone().parse().map_err(|e| anyhow!("{:?}", e))?,
            rkey: "self".parse().map_err(|e| anyhow!("{:?}", e))?,
            cid: None,
        }.into()
    ).await;

    // Keep the returned CID for an optimistic-concurrency swap on put_record,
    // so we don't silently clobber another writer's changes.
    let (mut current_record_data, swap_record_cid) = match me {
        Ok(output) => {
            let record = serde_json::from_value::<Record>(serde_json::to_value(&output.data.value)?)?;
            (record.data, output.data.cid)
        }
        Err(e) => {
            warn!("Failed to fetch current profile record: {:?}", e);
            // No existing record — start from scratch.  The SDK still lets us
            // put a record with all-None fields.
            (RecordData {
                avatar: None,
                banner: None,
                created_at: None,
                description: None,
                display_name: None,
                joined_via_starter_pack: None,
                labels: None,
                pinned_post: None,
                pronouns: None,
                website: None,
            }, None)
        }
    };

    // ── Update Avatar ────────────────────────────────

    match bsky::get_blob_metadata(new_avatar_cid, &env_vars.did, &endpoint).await {
        Ok(blob) => {
            current_record_data.avatar = Some(BlobRef::Typed(TypedBlobRef::Blob(blob)));
        }
        Err(e) => {
            error!("Could not retrieve metadata for avatar blob CID: {}. Error: {:?}", new_avatar_cid, e);
            return Ok(());
        }
    }

    // ── Update Banner ────────────────────────────────
    // Banner is optional per-hour; only attempt the swap when the env flag is
    // on AND the current hour maps to a banner CID.

    if env_vars.update_banner {
        if let Some(bcid) = new_banner_cid {
            match bsky::get_blob_metadata(bcid, &env_vars.did, &endpoint).await {
                Ok(blob) => {
                    current_record_data.banner = Some(BlobRef::Typed(TypedBlobRef::Blob(blob)));
                }
                Err(e) => {
                    warn!("Could not retrieve metadata for banner blob CID: {}. Error: {:?}", bcid, e);
                }
            }
        }
    }

    // ── Write Profile ────────────────────────────────

    agent.api.com.atproto.repo.put_record(
        atrium_api::com::atproto::repo::put_record::InputData {
            collection: "app.bsky.actor.profile".parse().map_err(|e| anyhow!("{:?}", e))?,
            repo: env_vars.did.parse().map_err(|e| anyhow!("{:?}", e))?,
            rkey: "self".parse().map_err(|e| anyhow!("{:?}", e))?,
            record: serde_json::from_value::<Unknown>(serde_json::to_value(current_record_data)?)?,
            swap_record: swap_record_cid,
            validate: None,
            swap_commit: None,
        }.into()
    ).await?;

    info!("Profile updated successfully.");

    Ok(())
}
