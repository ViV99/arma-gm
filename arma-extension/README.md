# Arma Extension (Rust DLL)

A thin Rust bridge between Arma 3's `callExtension` API and the GM server HTTP API. Handles async HTTP communication without blocking the game thread.

## What It Does

- Receives `callExtension` calls from SQF
- Posts game state JSON to `POST /api/v1/tick` asynchronously (in a worker thread)
- Sends responses back to Arma via `ExtensionCallback` event handler
- Splits large responses into 8 KB chunks to work around Arma's callback data limit

## Extension Commands (SQF API)

```sqf
// Set GM server URL (call once during init)
"ArmaGM" callExtension ["config", ["http://127.0.0.1:8080"]]

// Send game state JSON — returns "" immediately, response via ExtensionCallback
"ArmaGM" callExtension ["send_state", [_jsonString]]

// Send generated graph JSON — response via ExtensionCallback "graph_result"
"ArmaGM" callExtension ["send_graph", [_jsonString]]

// Check if server has cached graphs — response via ExtensionCallback "cache_result"
"ArmaGM" callExtension ["check_cache", [_mapName]]

// Ping server — response via ExtensionCallback "pong" function
"ArmaGM" callExtension ["ping", []]
```

## ExtensionCallback Protocol

Arma receives responses through the `ExtensionCallback` mission event handler. The `_name` parameter is always `"ArmaGM"`. The `_function` parameter indicates message type:

| `_function` | `_data` | Meaning |
|-------------|---------|---------|
| `"commands"` | JSON string | Complete tick response (≤8 KB) |
| `"chunk_begin"` | total chunk count (string) | Start of chunked tick response |
| `"chunk_data"` | chunk content | One chunk of tick response data |
| `"chunk_end"` | `""` | All tick response chunks received |
| `"graph_result"` | JSON string | Complete graph submission response (≤8 KB) |
| `"graph_result_chunk_begin"` | total chunk count | Start of chunked graph response |
| `"graph_result_chunk_data"` | chunk content | One chunk of graph response |
| `"graph_result_chunk_end"` | `""` | All graph response chunks received |
| `"cache_result"` | JSON string | Complete cache check response (≤8 KB) |
| `"cache_result_chunk_begin"` | total chunk count | Start of chunked cache response |
| `"cache_result_chunk_data"` | chunk content | One chunk of cache response |
| `"cache_result_chunk_end"` | `""` | All cache response chunks received |
| `"pong"` | `"ok"` or `"error:..."` | Ping response |
| `"error"` | error message | HTTP failure |

SQF response handling is in `arma-mod/addons/main/functions/fnc_receiveCommands.sqf`.

## Building

### Syntax check (any platform)

```bash
cd arma-extension
cargo check
```

### Build for Windows (from macOS)

```bash
# Prerequisites (one-time setup)
rustup target add x86_64-pc-windows-gnu
rustup target add i686-pc-windows-gnu
brew install mingw-w64

# 64-bit DLL (Arma 3 64-bit)
cargo build --release --target x86_64-pc-windows-gnu

# 32-bit DLL (Arma 3 32-bit, legacy)
cargo build --release --target i686-pc-windows-gnu
```

Output files:
- `target/x86_64-pc-windows-gnu/release/arma_gm_ext.dll` → copy as `arma_gm_ext_x64.dll`
- `target/i686-pc-windows-gnu/release/arma_gm_ext.dll` → copy as `arma_gm_ext.dll`

### Build on Windows

```cmd
cargo build --release
```

Output: `target/release/arma_gm_ext.dll`

## Installation

Copy both DLL files to the **Arma 3 root directory** (same folder as `arma3.exe`):

```
<Arma 3 root>/
├── arma3.exe
├── arma_gm_ext.dll       ← 32-bit
└── arma_gm_ext_x64.dll   ← 64-bit (used by modern Arma 3)
```

Arma 3 automatically loads `_x64.dll` when running in 64-bit mode.

## Source Layout

```
src/
├── lib.rs          # Extension entry point: #[arma] init, five commands
├── http_client.rs  # Blocking HTTP (ureq): post_json(), get()
└── chunking.rs     # Response chunker: send_response() + send_response_tagged()
```

## Design Notes

**Blocking HTTP in a worker thread**: The SQF `callExtension` call returns `""` immediately. The actual HTTP POST runs in a `std::thread::spawn` closure. This prevents the GM tick from blocking the Arma game loop.

**ureq over reqwest**: ureq is a blocking HTTP client with no async runtime dependency. It keeps the DLL small and avoids linking issues on Windows.

**8 KB chunk limit**: Arma's `ExtensionCallback` data parameter is limited to approximately 10 KB. The chunker splits at 8000 bytes to stay safely under the limit with JSON overhead.

**OnceLock for server URL**: The server URL is stored in a `OnceLock<RwLock<String>>` global. This avoids the arma-rs state system while still allowing runtime URL configuration via the `config` command.
