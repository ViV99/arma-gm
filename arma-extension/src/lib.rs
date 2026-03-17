use std::sync::{OnceLock, RwLock};

use arma_rs::{arma, Context, Extension};

mod chunking;
mod http_client;

static SERVER_URL: OnceLock<RwLock<String>> = OnceLock::new();

fn get_server_url() -> String {
    SERVER_URL
        .get_or_init(|| RwLock::new("http://127.0.0.1:8080".to_string()))
        .read()
        .unwrap()
        .clone()
}

fn set_server_url(url: String) {
    SERVER_URL
        .get_or_init(|| RwLock::new(String::new()))
        .write()
        .unwrap()
        .clone_from(&url);
}

#[arma]
fn init() -> Extension {
    Extension::build()
        .command("config", command_config)
        .command("send_state", command_send_state)
        .command("send_graph", command_send_graph)
        .command("check_cache", command_check_cache)
        .command("ping", command_ping)
        .finish()
}

/// Set GM server URL.
/// SQF: "ArmaGM" callExtension ["config", ["http://127.0.0.1:8080"]]
fn command_config(url: String) -> &'static str {
    set_server_url(url);
    "ok"
}

/// Send game state JSON to GM server (non-blocking).
/// SQF: "ArmaGM" callExtension ["send_state", [_jsonString]]
/// Returns "" immediately; response comes via ExtensionCallback.
fn command_send_state(ctx: Context, json: String) -> &'static str {
    let url = format!("{}/api/v1/tick", get_server_url());
    std::thread::spawn(move || match http_client::post_json(&url, &json) {
        Ok(response) => chunking::send_response(ctx, response),
        Err(err) => {
            let _ = ctx.callback_data("ArmaGM", "error", Some(err));
        }
    });
    ""
}

/// Send graph JSON to GM server for processing (non-blocking).
/// SQF: "ArmaGM" callExtension ["send_graph", [_jsonString]]
/// Returns "" immediately; response comes via ExtensionCallback "graph_result".
fn command_send_graph(ctx: Context, json: String) -> &'static str {
    let url = format!("{}/api/v1/graph", get_server_url());
    std::thread::spawn(move || match http_client::post_json(&url, &json) {
        Ok(response) => chunking::send_response_tagged(ctx, "graph_result", response),
        Err(err) => {
            let _ = ctx.callback_data("ArmaGM", "error", Some(err));
        }
    });
    ""
}

/// Check if the GM server has a cached graph for the given map (non-blocking).
/// SQF: "ArmaGM" callExtension ["check_cache", [_mapName]]
/// Returns "" immediately; response comes via ExtensionCallback "cache_result".
fn command_check_cache(ctx: Context, map_name: String) -> &'static str {
    let url = format!("{}/api/v1/graph/cache/{}", get_server_url(), map_name);
    std::thread::spawn(move || match http_client::get(&url) {
        Ok(response) => chunking::send_response_tagged(ctx, "cache_result", response),
        Err(err) => {
            let _ = ctx.callback_data("ArmaGM", "error", Some(err));
        }
    });
    ""
}

/// Ping the GM server to check connectivity.
/// SQF: "ArmaGM" callExtension ["ping", []]
fn command_ping(ctx: Context) -> &'static str {
    let url = format!("{}/api/v1/status", get_server_url());
    std::thread::spawn(move || match http_client::get(&url) {
        Ok(_) => {
            let _ = ctx.callback_data("ArmaGM", "pong", Some("ok".to_string()));
        }
        Err(e) => {
            let _ = ctx.callback_data("ArmaGM", "pong", Some(format!("error:{}", e)));
        }
    });
    ""
}
