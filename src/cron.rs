use std::process::Command;
use std::env;
use std::io::Write;
use tracing::{info, error};

pub fn setup_cron_job() {
    let current_exe = match env::current_exe() {
        Ok(path) => path,
        Err(e) => {
            error!("Failed to get current exe path: {}", e);
            return;
        }
    };
    let current_exe_str = current_exe.to_str().expect("Failed to convert path to string");
    
    // Command to check if cron job exists
    let output = Command::new("crontab")
        .arg("-l")
        .output();
    
    let cron_list = match output {
        Ok(out) if out.status.success() => String::from_utf8_lossy(&out.stdout).to_string(),
        _ => String::new(),
    };

    if cron_list.contains(current_exe_str) {
        info!("Cron job already exists.");
        return;
    }

    let new_job = format!("0 * * * * {}", current_exe_str);
    let mut new_cron = cron_list;
    if !new_cron.is_empty() && !new_cron.ends_with('\n') {
        new_cron.push('\n');
    }
    new_cron.push_str(&new_job);
    new_cron.push('\n');

    let child = Command::new("crontab")
        .arg("-")
        .stdin(std::process::Stdio::piped())
        .spawn();

    match child {
        Ok(mut child) => {
            let mut stdin = child.stdin.take().expect("Failed to open stdin");
            if let Err(e) = stdin.write_all(new_cron.as_bytes()) {
                error!("Failed to write to crontab stdin: {}", e);
                return;
            }
            drop(stdin);

            match child.wait() {
                Ok(status) => {
                    if status.success() {
                        info!("Cron job has been set up to run every hour.");
                    } else {
                        error!("Failed to set up cron job (crontab exited with error).");
                    }
                }
                Err(e) => error!("Failed to wait on crontab process: {}", e),
            }
        }
        Err(e) => error!("Failed to spawn crontab process: {}", e),
    }
}
