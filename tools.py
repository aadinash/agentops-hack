"""
tools.py – Custom function-tools for the CSV-cleaning / validation demo.

Each function is decorated with `@function_tool`, which turns it into a
JSON-schema-aware, LLM-callable tool in the OpenAI Agents SDK
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import List

import pandas as pd  # Optional—useful for many cleaners
from agents import function_tool


# ------------------------------------------------------------------------------
# 1)  Inspect a JSONL file (first N lines)
# ------------------------------------------------------------------------------

@function_tool
def load_data(file_path: str, num_preview_lines: int) -> str:
    """
    Return the first `num_preview_lines` lines of a JSONL file, pretty-printed.

    Args:
        file_path: Absolute or relative path to a `.jsonl` file.
        num_preview_lines: How many lines to show.

    Returns:
        A string containing the requested lines, each formatted as compact JSON.
    """
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"{p} does not exist")
    print(f"Loading data from {p}")

    lines: List[str] = []
    with p.open("r", encoding="utf-8") as f:
        for _ in range(num_preview_lines):
            line = f.readline()
            if not line:
                break
            obj = json.loads(line)
            lines.append(json.dumps(obj, ensure_ascii=False))

    return "\n".join(lines)


# ------------------------------------------------------------------------------
# 2)  Execute arbitrary cleaning code against a JSONL file
# ------------------------------------------------------------------------------

@function_tool
def execute_python_code(code: str, input_file_path: str) -> str:
    """
    Execute arbitrary user-supplied Python code.

    The runtime exposes two helpful variables to the executed script:

        • ``data`` – a ``list[dict]`` loaded from the provided ``input_file_path``
        • ``output_file`` – the path to a writable temporary ``.jsonl`` file

    The script can freely import any standard-library or pre-installed third-party
    packages (e.g. ``pandas``) available in the environment.

    Args:
        code: Source text of the Python module to run.
        input_file_path: Path to the raw JSONL file.

    Returns:
        The ``output_file`` path. Any exceptions raised by the supplied code are
        propagated to the caller so they can be surfaced to the user.
    """
    src_path = Path(input_file_path)
    print(f"src_path: {src_path}")
    if not src_path.is_file():
        raise FileNotFoundError(f"{src_path} does not exist")

    # ------------------------------------------------------------------
    # Load raw JSONL into a Python data structure the script can modify
    # ------------------------------------------------------------------

    # ----------------------------------------------------------
    # Create an isolated namespace and run the provided script
    # ----------------------------------------------------------

    local_ns = {"pd": pd, "input_file": input_file_path}

    # ----------------------------------------------------------
    # Execute the user-provided code, surfacing any exceptions
    # ----------------------------------------------------------
    try:
        exec(code, local_ns)
    except Exception as e:
        # Re-raise with a clearer message while preserving traceback
        raise RuntimeError("Error executing supplied Python code") from e

    # If execution succeeds, return the path to the temporary file so the
    # caller (or their code) can access it.
    return "/Users/aadinashikkar/Desktop/agentops-hack/cleaned_output.jsonl"
