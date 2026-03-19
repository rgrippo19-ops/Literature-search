from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..schemas import RunOutput


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_run_outputs(output_dir: str | Path, payload: RunOutput) -> tuple[Path, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = timestamp_slug()
    json_path = out_dir / f"{slug}_run.json"
    md_path = out_dir / f"{slug}_run.md"
    json_path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    return json_path, md_path


def _to_markdown(payload: RunOutput) -> str:
    lines = [
        f"# Question\n\n{payload.question}",
        f"## Normalized Question\n\n{payload.normalized_question}",
        f"## Final Answer\n\n{payload.final_answer}",
        "## Citations",
    ]
    for c in payload.citations:
        label = c.pmid or c.pmcid or c.paper_id
        lines.append(f"- {label} ({c.year}) {c.title} — {c.source_url}")
    lines.append("\n## Reasoning Chain")
    for step in payload.reasoning_chain:
        lines.append(f"- {step}")
    return "\n".join(lines) + "\n"
