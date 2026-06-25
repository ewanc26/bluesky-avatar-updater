//! URL normalisation, endpoint health checks, and environment variable
//! validation.

use reqwest::Client;
use tracing::{info, warn, error};
use std::env;

/// Upgrade a URL to HTTPS if it isn't already.
///
/// Strips an explicit `http://` prefix to avoid mixed-content issues with the
/// AT Protocol, and prepends `https://` to bare hostnames.
pub fn ensure_https(url: &str) -> String {
    if !url.starts_with("http://") && !url.starts_with("https://") {
        return format!("https://{}", url);
    }
    if let Some(stripped) = url.strip_prefix("http://") {
        return format!("https://{}", stripped);
    }
    url.to_string()
}

/// Check whether a PDS endpoint is reachable via its health endpoint.
///
/// Hitting `/xrpc/_health` is lighter than attempting a full login — we bail
/// early when the server is down rather than burning time on retry logic.
pub async fn is_endpoint_alive(url: &str) -> bool {
    let health_url = format!("{}/xrpc/_health", url.trim_end_matches('/'));
    let client = Client::new();
    match client.get(&health_url).timeout(std::time::Duration::from_secs(5)).send().await {
        Ok(response) => {
            if response.status().is_success() {
                info!("Endpoint {} is alive and healthy.", url);
                true
            } else {
                warn!("Endpoint {} is not responding correctly: {}", url, response.status());
                false
            }
        }
        Err(e) => {
            error!("Health check failed for {}: {}", health_url, e);
            false
        }
    }
}

/// Runtime environment variables the binary needs to operate.
pub struct EnvVars {
    pub endpoint: String,
    pub handle: String,
    pub password: String,
    pub did: String,
    pub update_banner: bool,
}

/// Read and validate required environment variables.
///
/// Returns `None` (and logs an error) when `ENDPOINT`, `HANDLE`, `PASSWORD`,
/// or `DID` is missing.  `UPDATE_BANNER` defaults to `false` and is optional.
pub fn validate_environment_variables() -> Option<EnvVars> {
    let endpoint = env::var("ENDPOINT").ok();
    let handle = env::var("HANDLE").ok();
    let password = env::var("PASSWORD").ok();
    let did = env::var("DID").ok();
    let update_banner = env::var("UPDATE_BANNER").unwrap_or_else(|_| "false".to_string()).to_lowercase() == "true";

    if let (Some(endpoint), Some(handle), Some(password), Some(did)) = (endpoint, handle, password, did) {
        Some(EnvVars {
            endpoint,
            handle,
            password,
            did,
            update_banner,
        })
    } else {
        error!("Missing environment variables. Ensure ENDPOINT, HANDLE, PASSWORD, and DID are set.");
        None
    }
}
