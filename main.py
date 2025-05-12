from agents import Agent, Runner, ItemHelpers
import os
from dotenv import load_dotenv
from tools import load_data, execute_python_code
import agentops
import asyncio
import sys
from pathlib import Path

load_dotenv()

agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

Cleaner = Agent(
    name="Cleaner",
    instructions="""
You are *Cleaner*, a senior data engineer.

Inputs (always provided **in the prompt text**):
  • An *issue report* describing all remaining problems.
  • The *current cleaning script* (enclosed in a ```python block). Treat this as the starting point. If no prior script is supplied, start from an empty file.
  • The variable `input_file_path` giving the absolute path to the raw JSONL file.

Tasks
  1. Read the issue report silently (do NOT output commentary).
  2. **Modify** the existing cleaning script – do NOT rewrite from scratch. Preserve working code and append / edit only the parts needed to fix the newly reported issues.
  3. Output a single Markdown ```python block that contains the *complete, updated script*.
  4. The script must define

        def clean(data_file: str) -> str

      and at the end call `clean("input_jsonl/mixed_example.jsonl")` and write the cleaned records to a file called `cleaned_output.jsonl` in the project root.
  5. Return nothing but the ```python block – no prose, no explanations.
""",
    tools=[execute_python_code],
)

# Expose Cleaner as a callable tool so Validator can summon it
rewrite_cleaning_code = Cleaner.as_tool(
    tool_name="rewrite_cleaning_code",
    tool_description=(
        "Given an issue report, emit *only* a Markdown ```python block "
    ),
)

Validator = Agent(
    name="Validator",
    instructions="""
You are *Validator*, a strict data QA specialist.

Workflow for each turn
----------------------
1. Use `load_data(<file_path>, num_preview_lines)` to inspect the JSONL (path provided in conversation).
2. Detect problems under **all** of these rules:
     • No null values
     • All keys are lowercase snake_case
     • No duplicate records (exact dict equality)
     • A field contains HTML tags, entities, or inconsistent spacing/markdown
     • A field contains boilerplate phrases like "As an AI..." or "I hope this helps!"
3. If problems exist **or** the previous cleaning script raised an exception:
     • Compose a short bullet list of issues and/or the Python traceback.
     • Then call `rewrite_cleaning_code` with **one argument**:
           The prompt should include:
             - "Issues:\n- …" (the bullet list)
             - "\nCurrent script:\n```python\n...\n```" (the latest cleaning script, if any)
             - A line `input_file_path = <path>` so Cleaner can call the script.
4. When you receive the updated script from Cleaner, immediately call `execute_python_code(code=<script>, input_file_path=<path>)`.
5. If execution succeeds, use `load_data` to inspect the cleaned JSONL; otherwise capture the exception text for step 3 on the next turn.
6. Repeat until the JSONL passes all checks or `max_turns` is reached.
""",
    tools=[load_data, rewrite_cleaning_code, execute_python_code],
)

async def clean_until_valid(path: str, preview_lines: int = 3, max_turns: int = 24):
    prompt = f"file_path = {path}\nnum_preview_lines = {preview_lines}"

    result = Runner.run_streamed(Validator, input=prompt, max_turns=max_turns)

    print("=== Run starting ===\n")
    async for event in result.stream_events():        
        if event.type == "agent_updated_stream_event":
            print(f"\n--- switched to: {event.new_agent.name} ---\n")

        elif event.type == "run_item_stream_event":
            item = event.item
            if item.type == "message_output_item":
                print(ItemHelpers.text_message_output(item))
            elif item.type == "tool_call_item":
                print(f"[calling tool → {item.raw_item.name}]")
            elif item.type == "tool_call_output_item":
                print(f"[tool output] {item.output}")

    print("\n=== Run complete ===")
    print("\nFinal output:\n", result.final_output)

# ---------- 4) CLI ----------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python app.py raw.jsonl [preview_lines]")
        sys.exit(1)

    file_path = sys.argv[1]
    if not Path(file_path).is_file():
        sys.exit(f"File not found: {file_path}")

    lines = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    asyncio.run(clean_until_valid(file_path, preview_lines=lines))
