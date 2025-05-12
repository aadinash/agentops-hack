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

Inputs (always provided via arguments, never hard-code paths):
  • `code`           – source for a Python module
  • `input_file_path` – path to the raw JSONL

Expectations:
 1. Read the issue report you receive from Validator.
 2. Write a Python script that defines:

        def clean(data: jsonl file) -> jsonl file

    where the input jsonl file is the original data. It is named "/Users/aadinashikkar/Desktop/agentops-hack/input_jsonl/html_example.jsonl"
    The function should fix *all* reported issues.
    The end of the script should call clean() on the provided input file. You can save the output to a new file 'cleaned_output.jsonl'
    Do **not** output additional commentary.
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
1. Use `load_data(<file_path>, num_preview_lines)` to inspect the JSONL
   (path provided in conversation).
2. Detect problems under **all** of these rules:
     • No null values
     • All keys are lowercase snake_case
     • No duplicate records (exact dict equality)
3. If problems exist:
   • Print a short bullet list of issues.
   • Then call rewrite_cleaning_code(
       input = "Issues:\\n- …\\n\\n")
4. Once you have received the cleaning code, call execute_python_code(
       input = "code = …\\n\\nfile_path = …")
5. If the cleaning code is successful, use load_data to inspect the cleaned JSONL.
6. Repeat until the JSONL is valid.
""",
    tools=[load_data, rewrite_cleaning_code, execute_python_code],
)

async def clean_until_valid(path: str, preview_lines: int = 3, max_turns: int = 12):
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
