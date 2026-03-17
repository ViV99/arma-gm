use arma_rs::Context;

const MAX_CHUNK_SIZE: usize = 8000;

/// Send response back to Arma via ExtensionCallback with a custom tag.
/// Small responses sent as single `tag` callback.
/// Large responses chunked: {tag}_chunk_begin -> {tag}_chunk_data x N -> {tag}_chunk_end.
pub fn send_response_tagged(ctx: Context, tag: &str, data: String) {
    if data.len() <= MAX_CHUNK_SIZE {
        let _ = ctx.callback_data("ArmaGM", tag, Some(data));
    } else {
        let chunks: Vec<String> = data
            .as_bytes()
            .chunks(MAX_CHUNK_SIZE)
            .map(|c| String::from_utf8_lossy(c).into_owned())
            .collect();
        let total = chunks.len();
        let begin_tag = format!("{}_chunk_begin", tag);
        let data_tag = format!("{}_chunk_data", tag);
        let end_tag = format!("{}_chunk_end", tag);
        let _ = ctx.callback_data("ArmaGM", &begin_tag, Some(total.to_string()));
        for chunk in chunks {
            let _ = ctx.callback_data("ArmaGM", &data_tag, Some(chunk));
        }
        let _ = ctx.callback_data("ArmaGM", &end_tag, Some(String::new()));
    }
}

/// Send response back to Arma via ExtensionCallback.
/// Small responses sent as single "commands" callback.
/// Large responses chunked: chunk_begin -> chunk_data x N -> chunk_end.
///
/// Note: uses original tag names (chunk_begin, not commands_chunk_begin)
/// for backward compatibility with existing SQF handlers.
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
