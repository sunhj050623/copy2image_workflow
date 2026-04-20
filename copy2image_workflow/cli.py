from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import MODE_TO_SKILL, Copy2ImageWorkflowEngine, Copy2ImageRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Copy2Image Workflow orchestrator based on agentorch template.")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_cmd = sub.add_parser("inspect", help="Inspect integrated skills and backend locations.")
    inspect_cmd.add_argument("--project-root", default=".", help="Project root path.")

    run_cmd = sub.add_parser("run", help="Run one end-to-end mode workflow.")
    run_cmd.add_argument("--project-root", default=".", help="Project root path.")
    run_cmd.add_argument("--mode", choices=sorted(MODE_TO_SKILL.keys()), required=True)
    run_cmd.add_argument("--topic", required=True)
    run_cmd.add_argument("--content", default="")
    run_cmd.add_argument("--content-file")
    run_cmd.add_argument("--style")
    run_cmd.add_argument("--layout")
    run_cmd.add_argument("--palette")
    run_cmd.add_argument("--image-count", type=int, default=4)
    run_cmd.add_argument("--aspect-ratio", default="3:4")
    run_cmd.add_argument("--quality", choices=["normal", "2k"], default="2k")
    run_cmd.add_argument("--provider")
    run_cmd.add_argument("--model")
    run_cmd.add_argument("--image-api-dialect")
    run_cmd.add_argument("--output-root", default="runs")
    run_cmd.add_argument("--thread-id", default="copy2image-thread")
    run_cmd.add_argument("--dry-run", action="store_true")
    run_cmd.add_argument("--no-generate", action="store_true")
    run_cmd.add_argument("--no-anchor-chain", action="store_true")
    run_cmd.add_argument("--fail-fast", action="store_true")
    run_cmd.add_argument("--skip-analysis-llm", action="store_true", help="Skip LLM content analysis step.")
    run_cmd.add_argument("--skip-outline-llm", action="store_true", help="Build outline from source sections without LLM outline refinement.")
    return parser


def cmd_inspect(project_root: Path) -> dict[str, object]:
    skills_root = project_root / "skills"
    backend = skills_root / "t2i-imagine" / "scripts" / "main.ts"
    return {
        "project_root": str(project_root.resolve()),
        "skills_root": str(skills_root.resolve()),
        "modes": {mode: str((skills_root / skill).resolve()) for mode, skill in MODE_TO_SKILL.items()},
        "backend_script": str(backend.resolve()),
        "backend_exists": backend.exists(),
    }


def cmd_run(args: argparse.Namespace) -> dict[str, object]:
    project_root = Path(args.project_root).resolve()
    engine = Copy2ImageWorkflowEngine(project_root=project_root)
    request = Copy2ImageRequest(
        mode=args.mode,
        topic=args.topic,
        content=args.content,
        content_file=args.content_file,
        style=args.style,
        layout=args.layout,
        palette=args.palette,
        image_count=args.image_count,
        aspect_ratio=args.aspect_ratio,
        quality=args.quality,
        provider=args.provider,
        model=args.model,
        image_api_dialect=args.image_api_dialect,
        generate=not args.no_generate,
        dry_run=args.dry_run,
        anchor_chain=not args.no_anchor_chain,
        fail_fast=args.fail_fast,
        skip_analysis_llm=args.skip_analysis_llm,
        skip_outline_llm=args.skip_outline_llm,
        output_root=str((project_root / args.output_root).resolve()),
        thread_id=args.thread_id,
    )
    return engine.run_sync(request)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "inspect":
        result = cmd_inspect(Path(args.project_root))
    else:
        result = cmd_run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

