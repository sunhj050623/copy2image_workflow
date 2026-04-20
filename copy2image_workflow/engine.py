from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, Field


def _load_workflow_base_symbols() -> tuple[type, type, type, type]:
    """
    Load `agentorch/workflow/base.py` directly to avoid importing `agentorch/__init__.py`
    and unrelated optional dependencies.
    """
    workflow_root = Path(__file__).resolve().parents[1]
    repo_root = workflow_root.parent
    candidate_roots = [repo_root, workflow_root]
    base_file: Path | None = None
    for root in candidate_roots:
        candidate = root / "agentorch" / "workflow" / "base.py"
        if candidate.exists():
            base_file = candidate
            break
    if base_file is None:
        base_file = repo_root / "agentorch" / "workflow" / "base.py"
    spec = importlib.util.spec_from_file_location("copy2image_agentorch_workflow_base", base_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load workflow base module: {base_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[assignment]
    # Pydantic forward refs from postponed annotations need explicit rebuild
    for model_name in ("Context", "Node", "Edge", "Workflow"):
        model = getattr(module, model_name, None)
        if model is not None and hasattr(model, "model_rebuild"):
            model.model_rebuild()
    return module.Context, module.Node, module.Workflow, module.WorkflowBuilder


Context, Node, Workflow, WorkflowBuilder = _load_workflow_base_symbols()


class WorkflowRunner:
    """
    Local copy of `agentorch.workflow.runner.WorkflowRunner` logic.
    """

    def __init__(self, handlers: dict[str, Any] | None = None) -> None:
        self.handlers = handlers or {}

    async def run(self, workflow: Workflow, context: Context) -> dict[str, Any]:
        current = context.resume_from or workflow.entry_node
        steps = 0
        last_result: dict[str, Any] = {}
        completed_nodes: set[str] = set()
        while current and steps < workflow.max_steps:
            node = workflow.get_node(current)
            handler = self.handlers.get(node.kind)
            if handler is None:
                raise ValueError(f"No handler registered for node kind '{node.kind}'.")
            last_result = await handler(node, context)
            context.variables[node.id] = last_result
            completed_nodes.add(node.id)
            if last_result.get("status") == "waiting_human":
                return last_result
            current = self._next_node(workflow, node.id, last_result)
            if current is None:
                current = self._find_join_target(workflow, completed_nodes)
            steps += 1
        if steps >= workflow.max_steps:
            raise RuntimeError("Workflow exceeded maximum allowed steps.")
        return last_result

    @staticmethod
    def _next_node(workflow: Workflow, node_id: str, result: dict[str, Any]) -> str | None:
        edges = workflow.get_edges(node_id)
        for edge in edges:
            if edge.kind == "success":
                return edge.target
            if edge.kind == "failure" and result.get("status") == "failed":
                return edge.target
            if edge.kind == "condition" and edge.condition == result.get("route"):
                return edge.target
        return None

    @staticmethod
    def _find_join_target(workflow: Workflow, completed_nodes: set[str]) -> str | None:
        for node in workflow.nodes:
            incoming = [edge for edge in workflow.edges if edge.target == node.id and edge.kind == "join"]
            if incoming and all(edge.source in completed_nodes for edge in incoming) and node.id not in completed_nodes:
                return node.id
        return None

WorkflowMode = Literal["image-cards", "infographic", "comic", "article-illustrator", "diagram", "cover-image"]

MODE_TO_SKILL = {
    "image-cards": "t2i-image-cards",
    "infographic": "t2i-infographic",
    "comic": "t2i-comic",
    "article-illustrator": "t2i-article-illustrator",
    "diagram": "t2i-diagram",
    "cover-image": "t2i-cover-image",
}


def slugify(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "untitled"


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


class Copy2ImageRequest(BaseModel):
    mode: WorkflowMode
    topic: str
    content: str = ""
    content_file: str | None = None

    type: str | None = None
    preset: str | None = None
    density: str | None = None
    style: str | None = None
    layout: str | None = None
    palette: str | None = None
    tone: str | None = None
    lang: str | None = None
    cover_type: str | None = None
    rendering: str | None = None
    text_level: str | None = None
    mood: str | None = None
    font: str | None = None
    ref_images: list[str] = Field(default_factory=list)
    image_count: int = 4

    aspect_ratio: str = "3:4"
    quality: Literal["normal", "2k"] = "2k"
    provider: str | None = None
    model: str | None = None
    image_api_dialect: str | None = None

    generate: bool = True
    dry_run: bool = False
    anchor_chain: bool = True
    fail_fast: bool = False
    skip_analysis_llm: bool = False
    skip_outline_llm: bool = False

    output_root: str | None = None
    thread_id: str = "copy2image-thread"

    @property
    def resolved_content(self) -> str:
        if self.content.strip():
            return self.content.strip()
        if self.content_file:
            content = Path(self.content_file).read_text(encoding="utf-8")
            return content.strip()
        return self.topic


@dataclass
class RenderResult:
    image: str
    prompt: str
    ok: bool
    command: list[str]
    stdout: str
    stderr: str
    code: int


@dataclass
class CommandExecResult:
    code: int
    stdout: str
    stderr: str
    cancelled: bool = False


class LLMAnalysis(BaseModel):
    analysis_markdown: str
    language: str | None = None
    recommended_count: int | None = None


class OutlineEntry(BaseModel):
    index: int
    kind: str
    slug: str
    title: str
    points: list[str] = Field(default_factory=list)
    visual_concept: str | None = None


class LLMOutline(BaseModel):
    outline_markdown: str
    entries: list[OutlineEntry]


class LLMPromptItem(BaseModel):
    index: int
    kind: str
    slug: str
    filename: str | None = None
    prompt: str


class LLMPrompts(BaseModel):
    prompts: list[LLMPromptItem]


class Copy2ImageWorkflowEngine:
    def __init__(self, project_root: Path | str) -> None:
        self.project_root = Path(project_root).resolve()
        self.skills_root = self.project_root / "skills"
        self.backend_root = self.skills_root / "t2i-imagine"
        self.backend_script = self.backend_root / "scripts" / "main.ts"
        self._bootstrap_text_env()
        self._text_api_key: str | None = None
        self._text_base_url: str | None = None
        self._text_model = "gpt-4o-mini"
        self._text_client: OpenAI | None = None
        self.configure_text_client()
        self._tool_handlers = {
            "prepare_workspace": self._tool_prepare_workspace,
            "analyze_content": self._tool_analyze_content,
            "build_outline": self._tool_build_outline,
            "build_prompts": self._tool_build_prompts,
            "render_images": self._tool_render_images,
        }

    def configure_text_client(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        resolved_api_key = (api_key or "").strip() or (
            os.environ.get("COPY2IMAGE_WORKFLOW_TEXT_API_KEY")
            or os.environ.get("T2I_AGENT_TEXT_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or None
        )
        resolved_base_url = (base_url or "").strip() or (
            os.environ.get("COPY2IMAGE_WORKFLOW_TEXT_BASE_URL")
            or os.environ.get("T2I_AGENT_TEXT_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or None
        )
        resolved_model = (model or "").strip() or (
            os.environ.get("COPY2IMAGE_WORKFLOW_TEXT_MODEL")
            or os.environ.get("T2I_AGENT_TEXT_MODEL")
            or os.environ.get("OPENAI_TEXT_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or os.environ.get("OPENAI_IMAGE_MODEL")
            or "gpt-4o-mini"
        )
        self._text_api_key = resolved_api_key
        self._text_base_url = resolved_base_url
        self._text_model = resolved_model
        if resolved_api_key:
            self._text_client = OpenAI(
                api_key=resolved_api_key,
                base_url=resolved_base_url if resolved_base_url else None,
            )
        else:
            self._text_client = None

    def _bootstrap_text_env(self) -> None:
        env_paths = [
            self.project_root.parent / "agent" / ".env",
        ]
        for env_path in env_paths:
            self._load_env_file(env_path)

    @staticmethod
    def _load_env_file(path: Path) -> None:
        if not path.exists():
            return
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            return
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            key = k.strip()
            val = v.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val

    @staticmethod
    def _extract_json_blob(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped
        fenced = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, flags=re.IGNORECASE)
        if fenced:
            return fenced.group(1)
        generic = re.search(r"(\{[\s\S]*\})", text)
        if generic:
            return generic.group(1)
        raise ValueError("LLM did not return a JSON object.")

    def _llm_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self._text_api_key:
            raise RuntimeError(
                "COPY2IMAGE_WORKFLOW_TEXT_API_KEY (or T2I_AGENT_TEXT_API_KEY / OPENAI_API_KEY) is required for LLM-driven skill execution."
            )
        last_error: Exception | None = None
        for _ in range(3):
            try:
                if self._text_client is None:
                    raise RuntimeError("Text client is not initialized.")
                resp = self._text_client.chat.completions.create(
                    model=self._text_model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                content = resp.choices[0].message.content or ""
                blob = self._extract_json_blob(content)
                return json.loads(blob)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"LLM JSON generation failed: {last_error}") from last_error

    async def _llm_json_async(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._llm_json, system_prompt=system_prompt, user_prompt=user_prompt)

    @staticmethod
    def _read_text_limit(path: Path, max_chars: int = 120_000) -> str:
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            return text[:max_chars] + "\n\n[TRUNCATED]"
        return text

    def _skill_context_text(self, skill_root: Path) -> str:
        skill_md = self._read_text_limit(skill_root / "SKILL.md", max_chars=30_000)
        refs: list[str] = []
        total_chars = len(skill_md)
        for rel in (
            Path("references/workflow.md"),
            Path("references/workflows/analysis-framework.md"),
            Path("references/workflows/outline-template.md"),
            Path("references/workflows/prompt-assembly.md"),
            Path("references/confirmation.md"),
        ):
            p = skill_root / rel
            if p.exists():
                ref_text = self._read_text_limit(p, max_chars=12_000)
                refs.append(f"## {rel.as_posix()}\n\n{ref_text}")
                total_chars += len(ref_text)
                if total_chars >= 55_000:
                    break
        return f"# SKILL.md\n\n{skill_md}\n\n" + "\n\n".join(refs)

    def build_workflow(self) -> Workflow:
        builder = WorkflowBuilder(max_steps=16)
        builder.add(Node(id="route", kind="router"), entry=True)
        builder.then(Node.tool("prepare_workspace", "prepare_workspace"))
        builder.then(Node.tool("analyze_content", "analyze_content"))
        builder.then(Node.tool("build_outline", "build_outline"))
        builder.then(Node.tool("build_prompts", "build_prompts"))
        builder.then(Node.tool("render_images", "render_images"))
        builder.then(Node(id="finalize", kind="artifact"))
        return builder.build()

    async def _handle_router(self, node: Node, context: Context) -> dict[str, Any]:
        request = Copy2ImageRequest.model_validate(context.state["request"])
        if request.mode not in MODE_TO_SKILL:
            return {"status": "failed", "error": f"Unsupported mode: {request.mode}"}
        context.state["selected_mode"] = request.mode
        context.state["selected_skill"] = MODE_TO_SKILL[request.mode]
        return {
            "status": "ok",
            "route": request.mode,
            "mode": request.mode,
            "skill": MODE_TO_SKILL[request.mode],
        }

    async def _handle_tool(self, node: Node, context: Context) -> dict[str, Any]:
        if self._is_cancelled(context):
            context.state["cancelled"] = True
            return {"status": "failed", "error": "Run cancelled by user."}
        tool_name = str(node.config.get("tool_name", "")).strip()
        handler = self._tool_handlers.get(tool_name)
        if handler is None:
            return {"status": "failed", "error": f"Unknown tool handler: {tool_name}"}
        return await handler(context)

    async def _handle_artifact(self, node: Node, context: Context) -> dict[str, Any]:
        request = Copy2ImageRequest.model_validate(context.state["request"])
        run_dir = Path(context.state["run_dir"])
        render_rows = context.state.get("render_results", [])
        status = "cancelled" if bool(context.state.get("cancelled")) else "ok"
        ok_count = 0
        total_count = 0
        if isinstance(render_rows, list) and render_rows:
            rows = [r for r in render_rows if isinstance(r, dict)]
            total_count = len(rows)
            ok_count = len([r for r in rows if bool(r.get("ok"))])
            dry_run_only = bool(rows) and all(int(r.get("code", 0)) == -1 for r in rows)
            if not dry_run_only and status != "cancelled":
                if ok_count == total_count:
                    status = "ok"
                elif ok_count > 0:
                    status = "partial_failed"
                else:
                    status = "failed"
        report = {
            "status": status,
            "mode": context.state["selected_mode"],
            "topic": request.topic,
            "skill": context.state["selected_skill"],
            "backend": "t2i-imagine",
            "project_root": str(self.project_root),
            "run_dir": str(run_dir),
            "analysis_file": str(run_dir / "analysis.md"),
            "outline_file": str(run_dir / "outline.md"),
            "prompts_dir": str(run_dir / "prompts"),
            "images": context.state.get("images", []),
            "render_results": context.state.get("render_results", []),
            "ok_count": ok_count,
            "total_count": total_count,
            "cancelled": bool(context.state.get("cancelled")),
        }
        report_path = run_dir / "report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    async def _tool_prepare_workspace(self, context: Context) -> dict[str, Any]:
        request = Copy2ImageRequest.model_validate(context.state["request"])
        topic_slug = slugify(request.topic)
        output_root = Path(request.output_root).resolve() if request.output_root else (self.project_root / "runs")
        run_dir = output_root / request.mode / f"{topic_slug}-{now_stamp()}"
        prompts_dir = run_dir / "prompts"
        refs_dir = run_dir / "refs"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        refs_dir.mkdir(parents=True, exist_ok=True)

        source_text = request.resolved_content
        source_name = f"source-{topic_slug}.md"
        (run_dir / source_name).write_text(source_text + "\n", encoding="utf-8")

        skill_root = self.skills_root / MODE_TO_SKILL[request.mode]
        context.state["run_dir"] = str(run_dir)
        context.state["prompts_dir"] = str(prompts_dir)
        context.state["refs_dir"] = str(refs_dir)
        context.state["topic_slug"] = topic_slug
        context.state["source_text"] = source_text
        context.state["source_file"] = str(run_dir / source_name)
        context.state["skill_root"] = str(skill_root)
        context.state["images"] = []
        context.state["render_results"] = []
        return {
            "status": "ok",
            "run_dir": str(run_dir),
            "source_file": str(run_dir / source_name),
            "skill_root": str(skill_root),
        }

    async def _tool_analyze_content(self, context: Context) -> dict[str, Any]:
        request = Copy2ImageRequest.model_validate(context.state["request"])
        run_dir = Path(context.state["run_dir"])
        skill_root = Path(context.state["skill_root"])
        source_text = context.state["source_text"]
        skill_context = self._skill_context_text(skill_root)
        if self._is_cancelled(context):
            context.state["cancelled"] = True
            return {"status": "failed", "error": "Run cancelled by user."}

        if request.skip_analysis_llm:
            sections = self._extract_sections(source_text)
            key_points: list[str] = []
            for sec in sections[:6]:
                title = str(sec.get("title", "")).strip()
                if title:
                    key_points.append(f"- {title}")
            fallback_markdown = "\n".join(
                [
                    "# Analysis (LLM skipped)",
                    "",
                    f"- Mode: {request.mode}",
                    f"- Topic: {request.topic}",
                    f"- Source length: {len(source_text)} chars",
                    "",
                    "## Source Sections",
                    *(key_points or ["- (no explicit sections found)"]),
                    "",
                    "## Note",
                    "- This run skips LLM analysis and relies on source-text-driven planning.",
                ]
            ).strip() + "\n"
            analysis_path = run_dir / "analysis.md"
            analysis_path.write_text(fallback_markdown, encoding="utf-8")
            context.state["analysis_markdown"] = fallback_markdown
            return {"status": "ok", "analysis_file": str(analysis_path), "analysis_mode": "source_only"}

        payload = {
            "request": request.model_dump(),
            "mode": request.mode,
            "topic": request.topic,
            "source_text": source_text,
            "required_output_schema": {
                "analysis_markdown": "string",
                "language": "string or null",
                "recommended_count": "integer or null",
            },
            "requirements": [
                "Follow the selected skill strategy, not generic templates.",
                "Write practical analysis that will drive outline and prompt generation.",
                "analysis_markdown must be markdown in user language.",
            ],
        }
        system_prompt = (
            "You are a senior visual-content planner. "
            "You must execute based on the provided skill documents and return strict JSON only."
        )
        user_prompt = f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n# Skill Context\n\n{skill_context}"
        analysis_obj = LLMAnalysis.model_validate(
            await self._llm_json_async(system_prompt=system_prompt, user_prompt=user_prompt)
        )
        analysis_path = run_dir / "analysis.md"
        analysis_path.write_text(analysis_obj.analysis_markdown.strip() + "\n", encoding="utf-8")
        context.state["analysis_markdown"] = analysis_obj.analysis_markdown
        if analysis_obj.recommended_count and analysis_obj.recommended_count > 0:
            context.state["recommended_count"] = analysis_obj.recommended_count
        return {"status": "ok", "analysis_file": str(analysis_path)}

    async def _tool_build_outline(self, context: Context) -> dict[str, Any]:
        request = Copy2ImageRequest.model_validate(context.state["request"])
        skill_root = Path(context.state["skill_root"])
        run_dir = Path(context.state["run_dir"])
        skill_context = self._skill_context_text(skill_root)
        source_text = context.state["source_text"]
        analysis_markdown = context.state.get("analysis_markdown", "")
        if self._is_cancelled(context):
            context.state["cancelled"] = True
            return {"status": "failed", "error": "Run cancelled by user."}
        # Hard constraint: user-selected image_count controls both planning and final rendering count.
        target_count = max(1, int(request.image_count))
        context.state["target_image_count"] = target_count

        if request.skip_outline_llm:
            source_sections = self._extract_sections(source_text)
            draft_entries: list[OutlineEntry] = []
            for idx, section in enumerate(source_sections, start=1):
                title = str(section.get("title", "")).strip() or f"Part {idx}"
                points_raw = section.get("points", [])
                points = [str(p).strip() for p in points_raw if str(p).strip()]
                draft_entries.append(
                    OutlineEntry(
                        index=idx,
                        kind="content",
                        slug=slugify(f"{request.topic}-{idx}"),
                        title=title[:100],
                        points=points[:8] or [title],
                        visual_concept=None,
                    )
                )
            entries = self._normalize_outline_entries(
                entries=draft_entries,
                target_count=target_count,
                topic=request.topic,
                source_text=source_text,
            )
            context.state["outline_entries"] = [entry.model_dump() for entry in entries]
            outline_path = run_dir / "outline.md"
            outline_path.write_text(self._render_outline_markdown(entries), encoding="utf-8")
            return {"status": "ok", "outline_file": str(outline_path), "count": len(entries), "outline_mode": "source_sections"}

        payload = {
            "request": request.model_dump(),
            "analysis_markdown": analysis_markdown,
            "source_text": source_text,
            "target_entry_count": target_count,
            "required_output_schema": {
                "outline_markdown": "string",
                "entries": [
                    {
                        "index": "integer, starts at 1",
                        "kind": "string",
                        "slug": "kebab-case string",
                        "title": "string",
                        "points": ["string", "string"],
                        "visual_concept": "string or null",
                    }
                ],
            },
            "requirements": [
                "Follow the selected skill's structure and conventions.",
                "entries length must equal target_entry_count exactly.",
                "Each entry should be generation-ready for image prompts.",
                "Respect user-selected image_count as a hard constraint.",
                "Return strict JSON only.",
            ],
        }
        if request.mode == "comic":
            payload["requirements"].extend(
                [
                    "Each entry is one comic page (not one single full-frame scene).",
                    "Each page should include multiple beats suitable for panel splitting.",
                ]
            )
        system_prompt = (
            "You are an expert storyboard and outline planner for multimodal content workflows. "
            "Follow skill docs exactly and output strict JSON."
        )
        user_prompt = f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n# Skill Context\n\n{skill_context}"
        outline_obj = LLMOutline.model_validate(
            await self._llm_json_async(system_prompt=system_prompt, user_prompt=user_prompt)
        )
        raw_entries = sorted(outline_obj.entries, key=lambda e: e.index)
        entries = self._normalize_outline_entries(
            entries=raw_entries,
            target_count=target_count,
            topic=request.topic,
            source_text=source_text,
        )

        context.state["outline_entries"] = [entry.model_dump() for entry in entries]
        outline_path = run_dir / "outline.md"
        if len(raw_entries) == target_count and outline_obj.outline_markdown.strip():
            outline_path.write_text(outline_obj.outline_markdown.strip() + "\n", encoding="utf-8")
        else:
            outline_path.write_text(self._render_outline_markdown(entries), encoding="utf-8")
        return {"status": "ok", "outline_file": str(outline_path), "count": len(entries)}

    async def _tool_build_prompts(self, context: Context) -> dict[str, Any]:
        request = Copy2ImageRequest.model_validate(context.state["request"])
        skill_root = Path(context.state["skill_root"])
        skill_context = self._skill_context_text(skill_root)
        run_dir = Path(context.state["run_dir"])
        prompts_dir = Path(context.state["prompts_dir"])
        entries: list[dict[str, Any]] = context.state["outline_entries"]
        if self._is_cancelled(context):
            context.state["cancelled"] = True
            return {"status": "failed", "error": "Run cancelled by user."}
        target_count = max(1, int(context.state.get("target_image_count", request.image_count)))
        if len(entries) != target_count:
            entries = entries[:target_count]
            context.state["outline_entries"] = entries
        payload = {
            "request": request.model_dump(),
            "outline_entries": entries,
            "source_text": context.state["source_text"],
            "required_output_schema": {
                "prompts": [
                    {
                        "index": "integer",
                        "kind": "string",
                        "slug": "kebab-case string",
                        "filename": "optional prompt filename ending with .md",
                        "prompt": "final generation prompt text",
                    }
                ]
            },
            "requirements": [
                "One prompt per outline entry.",
                f"Return exactly {len(entries)} prompts.",
                "Prompt must be production-ready and aligned with skill style/layout logic.",
                "Include explicit text rendering requirements when source language is Chinese.",
                "Do not include any watermark, logo, publisher mark, brand mark, app UI badge, or signature in the generated image.",
                "Avoid adding unrelated corner text such as platform/source labels (for example: 鑵捐鍔ㄦ极).",
                "Hard rule: the bottom-right corner must be clean. Never place any watermark, logo, publisher text, source label, or signature in the bottom-right area.",
                "Any visible text must appear only inside intended dialogue bubbles or narration boxes, not in free corners.",
                "Return strict JSON only.",
            ],
        }
        if request.style:
            payload["requirements"].append(f"Apply selected style strictly: {request.style}.")
        if request.type:
            payload["requirements"].append(f"Apply selected type strictly: {request.type}.")
        if request.preset:
            payload["requirements"].append(
                f"Apply selected preset strictly: {request.preset}. Resolve implied style/layout/palette/type rules from the skill docs."
            )
        if request.density:
            payload["requirements"].append(f"Target content density level: {request.density}.")
        if request.layout:
            payload["requirements"].append(f"Apply selected layout strictly: {request.layout}.")
        if request.palette:
            payload["requirements"].append(f"Apply selected palette strictly: {request.palette}.")
        if request.tone:
            payload["requirements"].append(f"Apply selected tone strictly: {request.tone}.")
        if request.lang and request.lang != "auto":
            payload["requirements"].append(f"All visible text must be rendered in language: {request.lang}.")
        if request.cover_type:
            payload["requirements"].append(f"Cover type must be: {request.cover_type}.")
        if request.rendering:
            payload["requirements"].append(f"Cover rendering style must be: {request.rendering}.")
        if request.text_level:
            payload["requirements"].append(f"Cover text density level must be: {request.text_level}.")
        if request.mood:
            payload["requirements"].append(f"Cover mood intensity must be: {request.mood}.")
        if request.font:
            payload["requirements"].append(f"Cover typography style must be: {request.font}.")

        source_text = str(context.state.get("source_text", ""))
        prefers_zh = request.lang == "zh" or (request.lang in (None, "", "auto") and bool(re.search(r"[\u4e00-\u9fff]", source_text)))
        if prefers_zh:
            payload["requirements"].extend(
                [
                    "Chinese text quality hard rules: no garbled characters, no repeated/stacked characters, and no broken glyphs.",
                    "Chinese text must be fluent and natural, with correct wording and punctuation.",
                    "No overlapping text; keep safe spacing from panel borders and key visual subjects.",
                    "Keep each Chinese text block concise (prefer <=12 Chinese characters per bubble/label).",
                ]
            )
        else:
            payload["requirements"].append("Text quality hard rule: no overlapping text, repeated glyphs, or broken characters.")

        if request.mode == "comic":
            payload["requirements"].extend(
                [
                    "Each prompt must describe a multi-panel comic page, not a single full-frame illustration.",
                    "Specify panel zoning explicitly (panel count, panel arrangement, and narrative flow).",
                    "Keep character appearance consistent across all panels in the same page.",
                    "Keep core character identity consistent across all pages in this run (face shape, hairstyle, costume colors, age impression, body proportion, and key accessories).",
                    "Panel borders/gutters must be clearly visible and clean.",
                ]
            )
            payload["comic_panel_guidance"] = self._comic_panel_guidance(request.layout, request.image_count)
            if request.style:
                payload["requirements"].append(f"Use comic art style: {request.style}.")
            if request.tone:
                payload["requirements"].append(f"Use comic tone: {request.tone}.")
        system_prompt = (
            "You are a prompt engineer for multimodal generation pipelines. "
            "Follow the provided skill docs precisely and output strict JSON."
        )
        user_prompt = f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n# Skill Context\n\n{skill_context}"
        prompts_obj = LLMPrompts.model_validate(
            await self._llm_json_async(system_prompt=system_prompt, user_prompt=user_prompt)
        )

        prompt_files: list[str] = []
        image_targets: list[str] = []
        prompts_by_index: dict[int, LLMPromptItem] = {}
        for item in sorted(prompts_obj.prompts, key=lambda p: p.index):
            if item.prompt.strip():
                prompts_by_index[int(item.index)] = item

        normalized_entries = sorted(entries, key=lambda e: int(e.get("index", 0) or 0))
        for seq_idx, entry in enumerate(normalized_entries, start=1):
            entry_index = int(entry.get("index", seq_idx) or seq_idx)
            chosen_item = prompts_by_index.get(entry_index) or prompts_by_index.get(seq_idx)
            idx = seq_idx
            kind = str((chosen_item.kind if chosen_item else entry.get("kind")) or "content")
            slug = str((chosen_item.slug if chosen_item else entry.get("slug")) or slugify(f"{request.topic}-{idx}"))
            prompt_text = (
                chosen_item.prompt.strip()
                if chosen_item and chosen_item.prompt.strip()
                else self._fallback_prompt(entry=entry, request=request)
            )
            default_name = f"{idx:02d}-{kind}-{slug}.md"
            chosen_name = Path(chosen_item.filename).name if chosen_item and chosen_item.filename else default_name
            if not chosen_name.endswith(".md"):
                chosen_name = chosen_name + ".md"
            prompt_file = prompts_dir / chosen_name
            image_file = run_dir / (prompt_file.stem + ".png")
            prompt_file.write_text(prompt_text + "\n", encoding="utf-8")
            prompt_files.append(str(prompt_file))
            image_targets.append(str(image_file))

        context.state["prompt_files"] = prompt_files
        context.state["image_targets"] = image_targets
        return {"status": "ok", "prompt_count": len(prompt_files), "prompts_dir": str(prompts_dir)}

    async def _tool_render_images(self, context: Context) -> dict[str, Any]:
        request = Copy2ImageRequest.model_validate(context.state["request"])
        prompt_files: list[str] = context.state["prompt_files"]
        image_targets: list[str] = context.state["image_targets"]
        cancel_event = context.state.get("_cancel_event")
        target_count = max(1, int(context.state.get("target_image_count", request.image_count)))
        pair_count = min(len(prompt_files), len(image_targets), target_count)
        if pair_count <= 0:
            return {"status": "failed", "error": "No prompt/image pairs available for rendering."}
        prompt_files = prompt_files[:pair_count]
        image_targets = image_targets[:pair_count]

        if request.dry_run or not request.generate:
            preview = [{"prompt": p, "image": i} for p, i in zip(prompt_files, image_targets, strict=True)]
            context.state["images"] = image_targets
            context.state["render_results"] = [
                {"image": i, "prompt": p, "ok": False, "code": -1, "stdout": "", "stderr": "dry-run"} for p, i in zip(prompt_files, image_targets, strict=True)
            ]
            return {"status": "ok", "dry_run": True, "planned": preview}

        if not self.backend_script.exists():
            return {"status": "failed", "error": f"Backend script not found: {self.backend_script}"}

        npx_bin = self._resolve_npx_binary()
        first_image: str | None = None
        latest_success_image: str | None = None
        render_results: list[RenderResult] = []
        generated_images: list[str] = []
        requested_user_refs = [str(p).strip() for p in request.ref_images if str(p).strip()]
        user_refs = [p for p in requested_user_refs if Path(p).exists()]
        # image-cards uses user refs for image 1 anchor; other modes keep refs on each image.
        apply_user_refs_every_image = request.mode in {"infographic", "comic", "article-illustrator", "diagram", "cover-image"}

        for idx, (prompt_file, image_file) in enumerate(zip(prompt_files, image_targets, strict=True), start=1):
            if cancel_event and hasattr(cancel_event, "is_set") and cancel_event.is_set():
                context.state["cancelled"] = True
                break
            # `ratio-metadata` is valid for text-to-image, but OpenAI-compatible
            # reference-image edits require `openai-native`.
            requested_dialect = (request.image_api_dialect or "").strip() or None
            env_dialect = (os.environ.get("OPENAI_IMAGE_API_DIALECT") or "").strip() or None
            attach_user_refs = bool(user_refs) and (apply_user_refs_every_image or idx == 1)
            using_reference = attach_user_refs or bool(request.anchor_chain and first_image and idx > 1)
            effective_dialect = requested_dialect
            if using_reference:
                active_dialect = (requested_dialect or env_dialect or "").lower()
                if active_dialect == "ratio-metadata":
                    effective_dialect = "openai-native"

            cmd = [
                npx_bin,
                "-y",
                "bun",
                str(self.backend_script),
                "--promptfiles",
                prompt_file,
                "--image",
                image_file,
                "--ar",
                request.aspect_ratio,
                "--quality",
                request.quality,
            ]
            if request.provider:
                cmd.extend(["--provider", request.provider])
            if request.model:
                cmd.extend(["--model", request.model])
            if effective_dialect:
                cmd.extend(["--imageApiDialect", effective_dialect])
            ref_images: list[str] = []
            if attach_user_refs:
                ref_images.extend(user_refs)
            if request.anchor_chain and first_image and idx > 1:
                ref_images.append(first_image)
                if latest_success_image and latest_success_image != first_image:
                    ref_images.append(latest_success_image)
            if ref_images:
                deduped_refs: list[str] = []
                seen_refs: set[str] = set()
                for ref in ref_images:
                    if ref not in seen_refs:
                        seen_refs.add(ref)
                        deduped_refs.append(ref)
                cmd.extend(["--ref", *deduped_refs])

            proc_result = self._run_subprocess_with_cancel(
                cmd,
                cwd=str(self.project_root),
                env=os.environ.copy(),
                cancel_event=cancel_event if isinstance(cancel_event, threading.Event) else None,
            )
            if proc_result.cancelled:
                context.state["cancelled"] = True

            # Graceful fallback: when quota is tight, retry the same page with `normal` quality.
            if (not context.state.get("cancelled")) and proc_result.code != 0 and request.quality == "2k":
                low_quota = "insufficient_user_quota" in (proc_result.stderr or "")
                if low_quota and "--quality" in cmd:
                    retry_cmd = cmd.copy()
                    q_index = retry_cmd.index("--quality")
                    if q_index + 1 < len(retry_cmd):
                        retry_cmd[q_index + 1] = "normal"
                        retry_result = self._run_subprocess_with_cancel(
                            retry_cmd,
                            cwd=str(self.project_root),
                            env=os.environ.copy(),
                            cancel_event=cancel_event if isinstance(cancel_event, threading.Event) else None,
                        )
                        if retry_result.cancelled:
                            context.state["cancelled"] = True
                            proc_result = retry_result
                        elif retry_result.code == 0:
                            cmd = retry_cmd
                            proc_result = retry_result

            ok = proc_result.code == 0
            if ok:
                generated_images.append(image_file)
                if first_image is None:
                    first_image = image_file
                latest_success_image = image_file
            result = RenderResult(
                image=image_file,
                prompt=prompt_file,
                ok=ok,
                command=cmd,
                stdout=proc_result.stdout,
                stderr=proc_result.stderr,
                code=proc_result.code,
            )
            render_results.append(result)

            if context.state.get("cancelled"):
                break

            if not ok and request.fail_fast:
                break

        context.state["images"] = generated_images
        context.state["render_results"] = [
            {
                "image": r.image,
                "prompt": r.prompt,
                "ok": r.ok,
                "command": r.command,
                "code": r.code,
                "stdout": r.stdout,
                "stderr": r.stderr,
            }
            for r in render_results
        ]

        all_ok = all(r.ok for r in render_results) if render_results else False
        cancelled = bool(context.state.get("cancelled"))
        return {
            "status": "cancelled" if cancelled else ("ok" if all_ok else "failed"),
            "generated": generated_images,
            "total": len(render_results),
            "ok_count": len([r for r in render_results if r.ok]),
            "cancelled": cancelled,
        }

    @staticmethod
    def _normalize_outline_entries(
        entries: list[OutlineEntry],
        target_count: int,
        topic: str,
        source_text: str,
    ) -> list[OutlineEntry]:
        cleaned = sorted(entries, key=lambda e: e.index)
        cleaned = cleaned[:target_count]
        fallback_sections = Copy2ImageWorkflowEngine._extract_sections(source_text)

        while len(cleaned) < target_count:
            idx = len(cleaned) + 1
            section = fallback_sections[(idx - 1) % len(fallback_sections)] if fallback_sections else {"title": f"Part {idx}", "points": [f"Key point {idx}"]}
            title = str(section.get("title", "")).strip() or f"Part {idx}"
            points_raw = section.get("points", [])
            points = [str(p).strip() for p in points_raw if str(p).strip()][:4]
            if not points:
                points = [title]
            cleaned.append(
                OutlineEntry(
                    index=idx,
                    kind="content",
                    slug=slugify(f"{topic}-{idx}"),
                    title=title[:100],
                    points=points,
                    visual_concept=None,
                )
            )

        normalized: list[OutlineEntry] = []
        for idx, entry in enumerate(cleaned, start=1):
            title = (entry.title or f"Part {idx}").strip()
            points = [p.strip() for p in entry.points if p and p.strip()] or [title]
            kind = (entry.kind or "content").strip() or "content"
            slug = (entry.slug or slugify(f"{topic}-{idx}")).strip() or slugify(f"{topic}-{idx}")
            normalized.append(
                OutlineEntry(
                    index=idx,
                    kind=kind,
                    slug=slug,
                    title=title[:100],
                    points=points[:8],
                    visual_concept=entry.visual_concept,
                )
            )
        return normalized

    @staticmethod
    def _render_outline_markdown(entries: list[OutlineEntry]) -> str:
        lines: list[str] = [f"# Outline ({len(entries)} images)", ""]
        for entry in entries:
            lines.append(f"## {entry.index}. {entry.title}")
            lines.append(f"- kind: {entry.kind}")
            lines.append(f"- slug: {entry.slug}")
            if entry.visual_concept:
                lines.append(f"- visual: {entry.visual_concept}")
            for point in entry.points:
                lines.append(f"- {point}")
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _fallback_prompt(entry: dict[str, Any], request: Copy2ImageRequest) -> str:
        title = str(entry.get("title", "")).strip() or "Untitled scene"
        points = [str(p).strip() for p in (entry.get("points", []) or []) if str(p).strip()]
        lines = [
            f"Create one {request.mode} image.",
            f"Main scene: {title}",
            f"Aspect ratio: {request.aspect_ratio}",
            "Requirements:",
        ]
        if request.style:
            lines.append(f"- Style: {request.style}")
        if request.type:
            lines.append(f"- Type: {request.type}")
        if request.preset:
            lines.append(f"- Preset: {request.preset}")
        if request.density:
            lines.append(f"- Density: {request.density}")
        if request.layout:
            lines.append(f"- Layout: {request.layout}")
        if request.palette:
            lines.append(f"- Palette: {request.palette}")
        if request.tone:
            lines.append(f"- Tone: {request.tone}")
        if request.lang and request.lang != "auto":
            lines.append(f"- Output language for all visible text: {request.lang}")
        if request.cover_type:
            lines.append(f"- Cover type: {request.cover_type}")
        if request.rendering:
            lines.append(f"- Cover rendering: {request.rendering}")
        if request.text_level:
            lines.append(f"- Cover text density: {request.text_level}")
        if request.mood:
            lines.append(f"- Cover mood: {request.mood}")
        if request.font:
            lines.append(f"- Cover font style: {request.font}")
        if points:
            lines.append("- Include these key points as readable text:")
            for point in points[:6]:
                lines.append(f"  - {point}")
        if request.mode == "comic":
            lines.append("- This image must be a comic page with clear multi-panel zoning, not a single full-frame illustration.")
            for rule in Copy2ImageWorkflowEngine._comic_panel_guidance(request.layout, request.image_count):
                lines.append(f"- {rule}")
            lines.append("- Keep characters visually consistent with previous pages in hairstyle, outfit, and facial traits.")
        lines.append("- Do not include any watermark, logo, publisher stamp, or signature text.")
        lines.append("- Hard rule: keep the bottom-right corner clean; no watermark/logo/label/signature text in that area.")
        lines.append("- Any visible text must be inside dialogue bubbles or narration boxes, not in free corners.")
        lines.append("- Text quality hard rule: no garbled characters, no repeated/stacked characters, and no broken glyphs.")
        lines.append("- Keep text blocks concise and avoid overlap with images or panel borders.")
        if request.lang == "zh":
            lines.append("- Chinese text must be fluent and natural; prefer <=12 Chinese characters per bubble/label.")
        lines.append("- Keep composition clear and not overcrowded.")
        lines.append("- Ensure text is legible and language-accurate.")
        return "\n".join(lines)

    @staticmethod
    def _comic_panel_guidance(layout: str | None, image_count: int) -> list[str]:
        selected_layout = (layout or "standard").strip().lower()
        low_page_count = max(1, int(image_count)) <= 3
        dense_hint = "Use slightly denser storytelling per page because total page count is low." if low_page_count else "Keep pacing balanced across pages."
        layout_rules: dict[str, list[str]] = {
            "four-panel": [
                "Use a strict 2x2 four-panel grid.",
                "One key beat per panel with clear setup-development-turn-conclusion flow.",
            ],
            "webtoon": [
                "Use a vertical strip with 4-7 stacked panels.",
                "Control rhythm through varying panel heights and white space.",
            ],
            "dense": [
                "Use 6-9 smaller panels with clear hierarchy.",
                "Group related actions in compact panel clusters.",
            ],
            "cinematic": [
                "Use 3-5 wide cinematic panels.",
                "Combine one establishing panel with close-up reaction panels.",
            ],
            "mixed": [
                "Use 4-6 panels with mixed sizes.",
                "Place one dominant panel and several supporting panels.",
            ],
            "splash": [
                "Use one dominant splash panel plus 2-3 supporting panels.",
                "Keep supporting panels as narrative transitions.",
            ],
            "standard": [
                "Use a balanced 4-6 panel page.",
                "Maintain clear reading order and panel gutters.",
            ],
        }
        base_rules = layout_rules.get(selected_layout, layout_rules["standard"])
        return [*base_rules, dense_hint]

    def run_sync(self, request: Copy2ImageRequest, cancel_event: threading.Event | None = None) -> dict[str, Any]:
        return asyncio.run(self.run(request, cancel_event=cancel_event))

    async def run(self, request: Copy2ImageRequest, cancel_event: threading.Event | None = None) -> dict[str, Any]:
        workflow = self.build_workflow()
        context = Context(
            thread_id=request.thread_id,
            user_input=request.topic,
            state={"request": request.model_dump(), "_cancel_event": cancel_event, "cancelled": False},
        )
        runner = WorkflowRunner(
            handlers={
                "router": self._handle_router,
                "tool": self._handle_tool,
                "artifact": self._handle_artifact,
            }
        )
        return await runner.run(workflow, context)

    @staticmethod
    def _extract_sections(text: str) -> list[dict[str, Any]]:
        heading_blocks = re.findall(r"(?m)^#{1,3}\s+(.+)$", text)
        if heading_blocks:
            return [{"title": heading.strip(), "points": [heading.strip()]} for heading in heading_blocks]
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            return [{"title": "Section", "points": ["Key idea"]}]
        sections: list[dict[str, Any]] = []
        for idx, para in enumerate(paragraphs[:8], start=1):
            excerpt = para.splitlines()[0][:80]
            bullets = [sentence.strip() for sentence in re.split(r"[.!?;]\s+|\n", para) if sentence.strip()][:3]
            sections.append({"title": f"Section {idx}: {excerpt}", "points": bullets or [excerpt]})
        return sections

    @staticmethod
    def _resolve_npx_binary() -> str:
        if os.name == "nt":
            return shutil.which("npx.cmd") or shutil.which("npx") or "npx.cmd"
        return shutil.which("npx") or "npx"

    @staticmethod
    def _is_cancelled(context: Context) -> bool:
        cancel_event = context.state.get("_cancel_event")
        return bool(cancel_event and hasattr(cancel_event, "is_set") and cancel_event.is_set())

    @staticmethod
    def _run_subprocess_with_cancel(
        cmd: list[str],
        *,
        cwd: str,
        env: dict[str, str],
        cancel_event: threading.Event | None,
    ) -> CommandExecResult:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        while True:
            if cancel_event and cancel_event.is_set():
                try:
                    proc.terminate()
                except Exception:
                    pass
                try:
                    out, err = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    out, err = proc.communicate()
                message = (err or "").rstrip()
                if message:
                    message += "\n"
                message += "[run cancelled by user]\n"
                return CommandExecResult(code=130, stdout=out or "", stderr=message, cancelled=True)
            try:
                out, err = proc.communicate(timeout=0.35)
                return CommandExecResult(code=proc.returncode or 0, stdout=out or "", stderr=err or "", cancelled=False)
            except subprocess.TimeoutExpired:
                continue

