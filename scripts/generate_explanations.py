#!/usr/bin/env python3
"""Offline generator for vocabulary word explanations.

Reads src/vocabulary/*.csv, calls the Claude API in batches to write a short
learner-facing explanation for each (word, translation) pair, and writes the
`explanation` column back into the CSV. Run this manually when adding new
vocabulary or improving explanations — the running app never calls an LLM.

Usage:
    uv sync --extra scripts
    ANTHROPIC_API_KEY=... uv run python scripts/generate_explanations.py \
        [--topic NAME] [--force] [--dry-run]
"""

import argparse
import glob
import json
import os
import sys

import anthropic
import pandas as pd

VOCAB_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "vocabulary")
MODEL = "claude-opus-4-8"
DEFAULT_BATCH_SIZE = 30

EXPLANATION_SCHEMA = {
    "type": "object",
    "properties": {
        "explanations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["word", "explanation"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["explanations"],
    "additionalProperties": False,
}


def build_prompt(pairs: list[tuple[str, str]]) -> str:
    lines = "\n".join(f"- {word!r} -> {translation!r}" for word, translation in pairs)
    return (
        "You are writing short study notes for a vocabulary quiz app. For each "
        "word/translation pair below, write a one-to-two sentence, learner-facing "
        "explanation: a usage nuance, a common point of confusion, or a memory aid "
        "that would help someone who just answered incorrectly understand the word "
        "better. Do not just restate the translation. Keep each explanation under "
        "240 characters.\n\n"
        f"{lines}\n\n"
        "Return one explanation per pair, in the same order as given."
    )


def generate_batch(
    client: anthropic.Anthropic, pairs: list[tuple[str, str]]
) -> list[str]:
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        output_config={"format": {"type": "json_schema", "schema": EXPLANATION_SCHEMA}},
        messages=[{"role": "user", "content": build_prompt(pairs)}],
    )
    text = next(block.text for block in response.content if block.type == "text")
    explanations = json.loads(text)["explanations"]
    if len(explanations) != len(pairs):
        raise ValueError(f"expected {len(pairs)} explanations, got {len(explanations)}")
    return [item["explanation"] for item in explanations]


def process_csv(
    client: anthropic.Anthropic,
    path: str,
    force: bool,
    dry_run: bool,
    batch_size: int,
) -> None:
    df = pd.read_csv(path, encoding="utf-8")
    if "word" not in df.columns or "translation" not in df.columns:
        print(f"Skipping {path}: missing word/translation columns")
        return

    if "explanation" not in df.columns:
        df["explanation"] = ""
    df["explanation"] = df["explanation"].fillna("")

    if force:
        pending_idx = df.index.tolist()
    else:
        pending_idx = df.index[df["explanation"].str.strip() == ""].tolist()

    name = os.path.basename(path)
    if not pending_idx:
        print(f"{name}: nothing to do ({len(df)} words already explained)")
        return

    print(f"{name}: generating {len(pending_idx)}/{len(df)} explanations")

    for start in range(0, len(pending_idx), batch_size):
        batch_idx = pending_idx[start : start + batch_size]
        pairs = [(df.at[i, "word"], df.at[i, "translation"]) for i in batch_idx]
        try:
            explanations = generate_batch(client, pairs)
        except Exception as exc:
            end = start + len(batch_idx)
            print(f"  batch {start}-{end} failed: {exc}", file=sys.stderr)
            continue

        for i, explanation in zip(batch_idx, explanations, strict=True):
            if dry_run:
                print(f"  {df.at[i, 'word']!r}: {explanation}")
            else:
                df.at[i, "explanation"] = explanation

    if not dry_run:
        df.to_csv(path, index=False, encoding="utf-8")
        print(f"  wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", help="Only process src/vocabulary/<topic>.csv")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate explanations that already exist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print explanations without writing the CSV",
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()

    try:
        client = anthropic.Anthropic()
    except anthropic.AnthropicError as exc:
        print(f"Failed to create Anthropic client: {exc}", file=sys.stderr)
        print("Set ANTHROPIC_API_KEY, or run `ant auth login`.", file=sys.stderr)
        sys.exit(1)

    if args.topic:
        paths = [os.path.join(VOCAB_DIR, f"{args.topic}.csv")]
        if not os.path.exists(paths[0]):
            print(f"No such vocab file: {paths[0]}", file=sys.stderr)
            sys.exit(1)
    else:
        paths = sorted(glob.glob(os.path.join(VOCAB_DIR, "*.csv")))
        if not paths:
            print(f"No CSV files found in {VOCAB_DIR}", file=sys.stderr)
            sys.exit(1)

    for path in paths:
        process_csv(client, path, args.force, args.dry_run, args.batch_size)


if __name__ == "__main__":
    main()
