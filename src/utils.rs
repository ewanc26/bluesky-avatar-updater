use reqwest::Client;
use tracing::{info, warn, error};
use std::env;

pub fn ensure_https(url: &str) -> String {
    if !url.starts_with("http://") && !url.starts_with("https://") {
        return format!("https://{}", url);
    }
    if let Some(stripped) = url.strip_prefix("http://") {
        return format!("https://{}", stripped);
    }
    url.to_string()
}

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

pub struct EnvVars {
    pub endpoint: String,
    pub handle: String,
    pub password: String,
    pub did: String,
    pub update_banner: bool,
}

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
