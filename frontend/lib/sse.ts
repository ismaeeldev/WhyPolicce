/**
 * Native SSE parser — AgentGuide/02_ApplicationFlow.md §5: fetch +
 * response.body.getReader(), no external SSE library, per the original scope
 * wording ("native web streams").
 */
export type SseEvent =
  | { type: "token"; data: string }
  | { type: "done"; sessionId: string; memorySnippets?: string[] }
  | { type: "error"; message: string };

function* parseSseBlocks(blocks: string[]): Generator<SseEvent> {
  for (const block of blocks) {
    const dataLine = block.split("\n").find((l) => l.startsWith("data: "));
    if (!dataLine) continue;
    try {
      yield JSON.parse(dataLine.slice(6)) as SseEvent;
    } catch {
      // Malformed chunk — skip rather than crash the stream.
    }
  }
}

export async function* parseSseStream(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<SseEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) {
        await reader.cancel();
        return;
      }
      const { done, value } = await reader.read();
      if (value) {
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";
        yield* parseSseBlocks(blocks);
      }
      if (done) {
        buffer += decoder.decode();
        if (buffer.trim()) {
          yield* parseSseBlocks([buffer]);
        }
        return;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
