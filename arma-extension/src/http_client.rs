use std::time::Duration;

const TIMEOUT_SECS: u64 = 30;

pub fn post_json(url: &str, json: &str) -> Result<String, String> {
    let agent = ureq::AgentBuilder::new()
        .timeout(Duration::from_secs(TIMEOUT_SECS))
        .build();
    agent
        .post(url)
        .set("Content-Type", "application/json")
        .send_string(json)
        .map_err(|e| format!("HTTP POST failed: {}", e))?
        .into_string()
        .map_err(|e| format!("Response read failed: {}", e))
}

pub fn get(url: &str) -> Result<String, String> {
    let agent = ureq::AgentBuilder::new()
        .timeout(Duration::from_secs(TIMEOUT_SECS))
        .build();
    agent
        .get(url)
        .call()
        .map_err(|e| format!("HTTP GET failed: {}", e))?
        .into_string()
        .map_err(|e| format!("Response read failed: {}", e))
}
