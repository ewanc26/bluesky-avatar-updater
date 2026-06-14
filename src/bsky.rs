use atrium_api::types::{Blob, CidLink};
use anyhow::{Result, anyhow};
use reqwest::Client;
use tracing::{info, debug};
use bytes::Bytes;
use std::str::FromStr;

pub async fn fetch_blob(did: &str, cid: &str, endpoint: &str) -> Result<Bytes> {
    let url = format!("{}/xrpc/com.atproto.sync.getBlob?did={}&cid={}", endpoint.trim_end_matches('/'), did, cid);
    let client = Client::new();
    let response = client.get(&url).timeout(std::time::Duration::from_secs(5)).send().await?;
    response.error_for_status_ref()?;
    let content = response.bytes().await?;
    info!("Fetched blob {} successfully.", cid);
    Ok(content)
}

pub async fn get_blob_metadata(cid: &str, did: &str, endpoint: &str) -> Result<Blob> {
    info!("Retrieving metadata for blob {}.", cid);
    let blob_data = fetch_blob(did, cid, endpoint).await?;
    
    let kind = infer::get(&blob_data).ok_or_else(|| anyhow!("Could not infer mime type for blob {}", cid))?;
    let mime_type = kind.mime_type().to_string();
    let size = blob_data.len();

    debug!("Blob metadata: MIME Type - {}, Size - {}", mime_type, size);

    Ok(Blob {
        r#ref: CidLink(cid::Cid::from_str(cid).map_err(|e| anyhow!("{:?}", e))?),
        mime_type,
        size,
    })
}
