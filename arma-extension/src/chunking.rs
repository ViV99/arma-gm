use arma_rs::Context;

const MAX_CHUNK_SIZE: usize = 8000;

/// Send response back to Arma via ExtensionCallback.
/// Small responses sent as single "commands" callback.
/// Large responses chunked: chunk_begin -> chunk_data x N -> chunk_end.
pub fn send_response(ctx: Context, data: String) {
    if data.len() <= MAX_CHUNK_SIZE {
        let _ = ctx.callback_data("ArmaGM", "commands", Some(data));
    } else {
        let chunks: Vec<String> = data
            .as_bytes()
            .chunks(MAX_CHUNK_SIZE)
            .map(|c| String::from_utf8_lossy(c).into_owned())
            .collect();
        let total = chunks.len();
        let _ = ctx.callback_data("ArmaGM", "chunk_begin", Some(total.to_string()));
        for chunk in chunks {
            let _ = ctx.callback_data("ArmaGM", "chunk_data", Some(chunk));
        }
        let _ = ctx.callback_data("ArmaGM", "chunk_end", Some(String::new()));
    }
}
