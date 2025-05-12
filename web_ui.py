"""Simple FastAPI web interface for running clean_until_valid and streaming logs."""

import asyncio
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Import objects from main.py
from main import Runner, Validator, ItemHelpers

app = FastAPI()

# Serve static assets (index.html, JS, CSS)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root() -> HTMLResponse:
    """Return main HTML page."""
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/files")
async def list_input_files() -> List[str]:
    """Return a list of available JSONL files under ./input_jsonl."""
    data_dir = Path(__file__).parent / "input_jsonl"
    files = sorted(str(p.relative_to(Path(__file__).parent)) for p in data_dir.glob("*.jsonl"))
    return files


async def _stream_clean(path: str, preview_lines: int):
    """Yield log lines produced by clean_until_valid for websocket streaming."""

    prompt = f"file_path = {path}\nnum_preview_lines = {preview_lines}"
    result = Runner.run_streamed(Validator, input=prompt, max_turns=24)

    yield "=== Run starting ===\n"
    async for event in result.stream_events():
        if event.type == "agent_updated_stream_event":
            yield f"\n--- switched to: {event.new_agent.name} ---\n"
        elif event.type == "run_item_stream_event":
            item = event.item
            if item.type == "message_output_item":
                yield ItemHelpers.text_message_output(item)
            elif item.type == "tool_call_item":
                yield f"[calling tool → {item.raw_item.name}]"
            elif item.type == "tool_call_output_item":
                yield f"[tool output] {item.output}"

    yield "\n=== Run complete ===\n"
    yield f"\nFinal output:\n{result.final_output}\n"


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Handle websocket connection, run cleaning pipeline and stream logs."""
    await ws.accept()
    try:
        params = await ws.receive_json()
        file_path = params.get("file_path")
        lines = int(params.get("lines", 3))

        abs_path = Path(file_path)
        if not abs_path.is_file():
            await ws.send_text(f"Error: File not found — {file_path}")
            await ws.close()
            return

        # Stream log lines
        async for log_line in _stream_clean(str(abs_path), lines):
            await ws.send_text(log_line)

        await ws.close()

    except WebSocketDisconnect:
        # Client disconnected; nothing to do
        pass
    except Exception as exc:
        # Propagate any other errors to the client before closing
        await ws.send_text(f"Error: {exc}")
        await ws.close()
