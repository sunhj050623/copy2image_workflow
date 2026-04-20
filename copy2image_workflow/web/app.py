from __future__ import annotations

import json
import os
import re
import shutil
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from copy2image_workflow.engine import MODE_TO_SKILL, Copy2ImageWorkflowEngine, Copy2ImageRequest

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]
RUNS_ROOT = PROJECT_ROOT / "runs"
UPLOADS_ROOT = RUNS_ROOT / "uploads"
SETTINGS_FILE = RUNS_ROOT / "web_settings.json"
RUNS_ROOT.mkdir(parents=True, exist_ok=True)

IMAGE_CARD_LAYOUTS = [
    "sparse",
    "balanced",
    "dense",
    "list",
    "comparison",
    "flow",
    "mindmap",
    "quadrant",
]
IMAGE_CARD_PALETTES = ["macaron", "warm", "neon"]
COMMON_LANGS = ["auto", "zh", "en", "ja"]
DIAGRAM_TYPES = [
    "architecture",
    "flowchart",
    "sequence",
    "structural",
    "mind-map",
    "timeline",
    "illustrative",
    "state-machine",
    "data-flow",
]
COVER_TYPES = ["hero", "conceptual", "typography", "metaphor", "scene", "minimal"]
COVER_TEXT_LEVELS = ["none", "title-only", "title-subtitle", "text-rich"]
COVER_MOODS = ["subtle", "balanced", "bold"]
COVER_FONTS = ["clean", "handwritten", "serif", "display"]
ARTICLE_TYPES = ["infographic", "scene", "flowchart", "comparison", "framework", "timeline", "mixed"]
ARTICLE_DENSITIES = ["minimal", "balanced", "per-section", "rich"]
ALLOWED_UPLOAD_EXTS = {".txt", ".md", ".markdown", ".docx"}
ALLOWED_REF_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


def _md_stems(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted(p.stem for p in path.glob("*.md") if p.is_file())


def _md_table_first_col_values(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    values: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|\s*:?-{2,}", line):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if not cols:
            continue
        first = cols[0].strip("` ").strip()
        if not first or first.startswith("--"):
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", first):
            continue
        if first not in seen:
            seen.add(first)
            values.append(first)
    return values


def _token_cell(cell: str) -> str | None:
    token = cell.strip().strip("`").strip()
    if not token:
        return None
    if re.fullmatch(r"[a-z0-9][a-z0-9-]*", token):
        return token
    return None


def _md_table_combo_map(path: Path, value_columns: int) -> dict[str, list[str | None]]:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    mapping: dict[str, list[str | None]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|\s*:?-{2,}", line):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < value_columns + 1:
            continue
        key = _token_cell(cols[0])
        if not key or key.startswith("--"):
            continue
        values: list[str | None] = []
        for idx in range(1, value_columns + 1):
            values.append(_token_cell(cols[idx]))
        if key not in mapping:
            mapping[key] = values
    return mapping


def _build_mode_options() -> dict[str, dict[str, Any]]:
    skills_root = PROJECT_ROOT / "skills"
    return {
        "image-cards": {
            "styles": _md_stems(skills_root / "t2i-image-cards" / "references" / "presets"),
            "layouts": IMAGE_CARD_LAYOUTS,
            "palettes": IMAGE_CARD_PALETTES,
            "tones": [],
            "langs": COMMON_LANGS,
            "supports_palette": True,
            "types": [],
            "presets": _md_table_first_col_values(skills_root / "t2i-image-cards" / "references" / "style-presets.md"),
            "densities": [],
            "supports_ref": True,
        },
        "infographic": {
            "styles": _md_stems(skills_root / "t2i-infographic" / "references" / "styles"),
            "layouts": _md_stems(skills_root / "t2i-infographic" / "references" / "layouts"),
            "palettes": [],
            "tones": [],
            "langs": COMMON_LANGS,
            "supports_palette": False,
            "types": [],
            "presets": [],
            "densities": [],
            "supports_ref": True,
        },
        "comic": {
            "styles": _md_stems(skills_root / "t2i-comic" / "references" / "art-styles"),
            "layouts": _md_stems(skills_root / "t2i-comic" / "references" / "layouts"),
            "palettes": [],
            "tones": _md_stems(skills_root / "t2i-comic" / "references" / "tones"),
            "langs": COMMON_LANGS,
            "supports_palette": False,
            "types": [],
            "presets": [],
            "densities": [],
            "supports_ref": True,
        },
        "article-illustrator": {
            "styles": _md_stems(skills_root / "t2i-article-illustrator" / "references" / "styles"),
            "layouts": [],
            "palettes": _md_stems(skills_root / "t2i-article-illustrator" / "references" / "palettes"),
            "tones": [],
            "langs": COMMON_LANGS,
            "supports_palette": True,
            "types": ARTICLE_TYPES,
            "presets": _md_table_first_col_values(skills_root / "t2i-article-illustrator" / "references" / "style-presets.md"),
            "densities": ARTICLE_DENSITIES,
            "supports_ref": True,
        },
        "diagram": {
            "styles": _md_stems(skills_root / "t2i-diagram" / "references" / "styles"),
            "layouts": DIAGRAM_TYPES,
            "palettes": [],
            "tones": [],
            "langs": COMMON_LANGS,
            "supports_palette": False,
            "diagram_types": DIAGRAM_TYPES,
            "types": [],
            "presets": [],
            "densities": [],
            "supports_ref": False,
        },
        "cover-image": {
            "styles": _md_table_first_col_values(skills_root / "t2i-cover-image" / "references" / "style-presets.md"),
            "layouts": [],
            "palettes": _md_stems(skills_root / "t2i-cover-image" / "references" / "palettes"),
            "tones": [],
            "langs": COMMON_LANGS,
            "supports_palette": True,
            "cover_types": COVER_TYPES,
            "renderings": _md_stems(skills_root / "t2i-cover-image" / "references" / "renderings"),
            "text_levels": COVER_TEXT_LEVELS,
            "moods": COVER_MOODS,
            "fonts": COVER_FONTS,
            "types": [],
            "presets": [],
            "densities": [],
            "supports_ref": True,
        },
    }


MODE_OPTIONS = _build_mode_options()
_SKILLS_ROOT = PROJECT_ROOT / "skills"
IMAGE_CARD_PRESET_MAP = _md_table_combo_map(_SKILLS_ROOT / "t2i-image-cards" / "references" / "style-presets.md", 3)
ARTICLE_PRESET_MAP = _md_table_combo_map(_SKILLS_ROOT / "t2i-article-illustrator" / "references" / "style-presets.md", 3)
COVER_STYLE_MAP = _md_table_combo_map(_SKILLS_ROOT / "t2i-cover-image" / "references" / "style-presets.md", 2)

app = FastAPI(title="Copy2Image Workflow Web", version="1.2.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/runs", StaticFiles(directory=str(RUNS_ROOT)), name="runs")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
engine = Copy2ImageWorkflowEngine(project_root=PROJECT_ROOT)
_RUN_LOCK = threading.Lock()
_SETTINGS_LOCK = threading.Lock()
_ACTIVE_CANCEL_EVENT: threading.Event | None = None
_ACTIVE_THREAD_ID: str | None = None


class RunPayload(BaseModel):
    mode: str
    topic: str | None = None
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
    ref_images: list[str] | None = None
    image_count: int = 4
    aspect_ratio: str = "3:4"
    quality: str = "2k"
    provider: str | None = None
    model: str | None = None
    image_api_dialect: str | None = None
    dry_run: bool = False
    generate: bool = True
    anchor_chain: bool = True
    fail_fast: bool = False
    skip_analysis_llm: bool = False
    skip_outline_llm: bool = False
    output_root: str = "runs"
    thread_id: str = "copy2image-web"


class LangPayload(BaseModel):
    lang: str


class TextModelSettings(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class ImageModelSettings(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    provider: str | None = None
    image_api_dialect: str | None = None


class WebSettingsPayload(BaseModel):
    text: TextModelSettings = Field(default_factory=TextModelSettings)
    image: ImageModelSettings = Field(default_factory=ImageModelSettings)


I18N: dict[str, dict[str, Any]] = {
    "zh": {
        "title": "Copy2Image Workflow 控制台",
        "subtitle": "六种模式统一编排，白底蓝色简洁界面",
        "run_title": "运行任务",
        "result_title": "输出结果",
        "recent_title": "最近任务",
        "labels": {
            "mode": "模式",
            "topic": "主题（可选）",
            "content": "内容",
            "input_source": "内容来源",
            "input_text": "直接输入",
            "input_upload": "上传文档",
            "upload_file": "选择文档（txt / md / docx）",
            "type": "类型（可选）",
            "preset": "预设（可选）",
            "density": "密度（可选）",
            "style": "风格（可选）",
            "tone": "语气/氛围（可选）",
            "lang": "语言（可选）",
            "cover_type": "封面类型（可选）",
            "rendering": "渲染风格（可选）",
            "text_level": "文字密度（可选）",
            "mood": "情绪强度（可选）",
            "font": "字体风格（可选）",
            "ref_images": "参考图（可选）",
            "upload_ref_file": "选择参考图（png / jpg / webp / gif）",
            "layout": "布局（可选）",
            "palette": "配色（可选）",
            "image_count": "图片数量",
            "aspect_ratio": "比例",
            "quality": "质量",
            "provider": "后端 provider（可选）",
            "model": "模型（可选）",
            "image_api_dialect": "API 方言（可选）",
            "dry_run": "仅演练（dry-run）",
            "generate": "执行生成",
            "anchor_chain": "启用首图风格锚定",
            "fail_fast": "失败即停",
            "skip_analysis_llm": "跳过 LLM 内容分析",
            "skip_outline_llm": "跳过 LLM 大纲提炼",
        },
        "placeholders": {
            "topic": "留空将自动从文案或文件名推断",
            "content": "输入文案内容，或切换到“上传文档”",
            "auto": "自动（推荐）",
            "upload_status_empty": "未上传文件",
            "ref_status_empty": "未上传参考图",
            "result_empty": "运行后将在这里显示输出图片",
        },
        "buttons": {
            "run": "开始运行",
            "stop": "停止当前任务",
            "refresh": "刷新最近任务",
            "upload": "上传并使用",
            "upload_ref": "上传参考图",
            "settings": "模型设置",
        },
        "modes": {
            "image-cards": "图片卡片",
            "infographic": "信息图",
            "comic": "漫画",
            "article-illustrator": "文章配图",
            "diagram": "图表",
            "cover-image": "封面图",
        },
        "lang_switch": "English",
    },
    "en": {
        "title": "Copy2Image Workflow Console",
        "subtitle": "Unified orchestration for six modes with a clean white + blue UI",
        "run_title": "Run Task",
        "result_title": "Output",
        "recent_title": "Recent Runs",
        "labels": {
            "mode": "Mode",
            "topic": "Topic (optional)",
            "content": "Content",
            "input_source": "Content Source",
            "input_text": "Direct Input",
            "input_upload": "Upload Document",
            "upload_file": "Select file (txt / md / docx)",
            "type": "Type (optional)",
            "preset": "Preset (optional)",
            "density": "Density (optional)",
            "style": "Style (optional)",
            "tone": "Tone (optional)",
            "lang": "Language (optional)",
            "cover_type": "Cover Type (optional)",
            "rendering": "Rendering (optional)",
            "text_level": "Text Density (optional)",
            "mood": "Mood (optional)",
            "font": "Font (optional)",
            "ref_images": "Reference Images (optional)",
            "upload_ref_file": "Select reference images (png / jpg / webp / gif)",
            "layout": "Layout (optional)",
            "palette": "Palette (optional)",
            "image_count": "Image count",
            "aspect_ratio": "Aspect ratio",
            "quality": "Quality",
            "provider": "Backend provider (optional)",
            "model": "Model (optional)",
            "image_api_dialect": "API dialect (optional)",
            "dry_run": "Dry-run only",
            "generate": "Generate",
            "anchor_chain": "Use first-image anchor chain",
            "fail_fast": "Fail fast",
            "skip_analysis_llm": "Skip LLM content analysis",
            "skip_outline_llm": "Skip LLM outline refinement",
        },
        "placeholders": {
            "topic": "Leave empty to infer from content or filename",
            "content": "Paste your copy, or switch to upload mode",
            "auto": "Auto (recommended)",
            "upload_status_empty": "No file uploaded",
            "ref_status_empty": "No reference image uploaded",
            "result_empty": "Generated images will appear here",
        },
        "buttons": {
            "run": "Run",
            "stop": "Stop Current Task",
            "refresh": "Refresh Recent Runs",
            "upload": "Upload and Use",
            "upload_ref": "Upload Refs",
            "settings": "Model Settings",
        },
        "modes": {
            "image-cards": "Image Cards",
            "infographic": "Infographic",
            "comic": "Comic",
            "article-illustrator": "Article Illustrator",
            "diagram": "Diagram",
            "cover-image": "Cover Image",
        },
        "lang_switch": "中文",
    },
}


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        normalized = _normalize_text(value)
        if normalized:
            return normalized
    return None


def _default_settings() -> WebSettingsPayload:
    return WebSettingsPayload(
        text=TextModelSettings(
            api_key=_first_non_empty(
                os.environ.get("COPY2IMAGE_WORKFLOW_TEXT_API_KEY"),
                os.environ.get("T2I_AGENT_TEXT_API_KEY"),
                os.environ.get("OPENAI_API_KEY"),
            ),
            base_url=_first_non_empty(
                os.environ.get("COPY2IMAGE_WORKFLOW_TEXT_BASE_URL"),
                os.environ.get("T2I_AGENT_TEXT_BASE_URL"),
                os.environ.get("OPENAI_BASE_URL"),
            ),
            model=_first_non_empty(
                os.environ.get("COPY2IMAGE_WORKFLOW_TEXT_MODEL"),
                os.environ.get("T2I_AGENT_TEXT_MODEL"),
                os.environ.get("OPENAI_TEXT_MODEL"),
                os.environ.get("OPENAI_MODEL"),
                os.environ.get("OPENAI_IMAGE_MODEL"),
            ),
        ),
        image=ImageModelSettings(
            api_key=_first_non_empty(os.environ.get("OPENAI_API_KEY")),
            base_url=_first_non_empty(os.environ.get("OPENAI_BASE_URL")),
            model=_first_non_empty(os.environ.get("OPENAI_IMAGE_MODEL"), os.environ.get("OPENAI_MODEL")),
            provider=None,
            image_api_dialect=_first_non_empty(os.environ.get("OPENAI_IMAGE_API_DIALECT")),
        ),
    )


def _normalized_settings(payload: WebSettingsPayload) -> WebSettingsPayload:
    return WebSettingsPayload(
        text=TextModelSettings(
            api_key=_normalize_text(payload.text.api_key),
            base_url=_normalize_text(payload.text.base_url),
            model=_normalize_text(payload.text.model),
        ),
        image=ImageModelSettings(
            api_key=_normalize_text(payload.image.api_key),
            base_url=_normalize_text(payload.image.base_url),
            model=_normalize_text(payload.image.model),
            provider=_normalize_text(payload.image.provider),
            image_api_dialect=_normalize_text(payload.image.image_api_dialect),
        ),
    )


def _load_settings() -> WebSettingsPayload:
    defaults = _default_settings()
    if not SETTINGS_FILE.exists():
        return defaults
    try:
        with _SETTINGS_LOCK:
            raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        loaded = WebSettingsPayload.model_validate(raw)
        return _normalized_settings(loaded)
    except Exception:
        return defaults


def _save_settings(payload: WebSettingsPayload) -> WebSettingsPayload:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalized_settings(payload)
    with _SETTINGS_LOCK:
        SETTINGS_FILE.write_text(
            json.dumps(normalized.model_dump(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return normalized


@contextmanager
def _temporary_env(overrides: dict[str, str | None]):
    touched: dict[str, str | None] = {}
    for key, value in overrides.items():
        if value is None:
            continue
        touched[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, old_value in touched.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def _safe_filename(raw_name: str) -> str:
    stem = Path(raw_name).stem
    stem = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff._-]+", "-", stem).strip("-._")
    if not stem:
        stem = "upload"
    return stem[:80]


def _extract_docx_text(path: Path) -> str:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(path, "r") as zip_file:
        xml_bytes = zip_file.read("word/document.xml")
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_bytes)
    chunks: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        line_parts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        line = "".join(line_parts).strip()
        if line:
            chunks.append(line)
    return "\n".join(chunks).strip()


def _read_upload_as_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".markdown"}:
        return path.read_text(encoding="utf-8").strip()
    if ext == ".docx":
        return _extract_docx_text(path)
    raise ValueError(f"Unsupported upload type: {ext}")


def _infer_topic(mode: str, topic: str | None, content: str, content_file: str | None) -> str:
    max_len = 24
    if topic and topic.strip():
        return topic.strip()[:max_len]
    if content.strip():
        for line in content.splitlines():
            candidate = line.strip().lstrip("#").strip()
            if candidate:
                return candidate[:max_len]
    if content_file:
        candidate = Path(content_file).stem.replace("_", " ").replace("-", " ").strip()
        if candidate:
            return candidate[:max_len]
    return f"{mode}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def _recent_title_from_topic(topic: str | None, run_id: str) -> str:
    if topic and topic.strip():
        return topic.strip()[:24]
    fallback = re.sub(r"-\d{8}-\d{6}$", "", run_id).replace("-", " ").strip()
    if fallback:
        return fallback[:24]
    return run_id[:24]


def _path_to_runs_url(path: str) -> str | None:
    normalized = path.replace("\\", "/")
    marker = "/runs/"
    idx = normalized.find(marker)
    if idx >= 0:
        return normalized[idx:]
    try:
        rel = Path(path).resolve().relative_to(RUNS_ROOT.resolve())
        return f"/runs/{rel.as_posix()}"
    except Exception:
        return None


def _enrich_result_with_urls(result: dict[str, Any]) -> dict[str, Any]:
    data = dict(result)
    image_paths = [str(p) for p in (data.get("images", []) or [])]
    image_urls = [u for p in image_paths if (u := _path_to_runs_url(p))]
    data["image_urls"] = image_urls

    render_results = data.get("render_results")
    if isinstance(render_results, list):
        enriched_rows: list[dict[str, Any]] = []
        for row in render_results:
            if isinstance(row, dict):
                row_copy = dict(row)
                if "image_url" not in row_copy and isinstance(row_copy.get("image"), str):
                    row_copy["image_url"] = _path_to_runs_url(row_copy["image"])
                enriched_rows.append(row_copy)
            else:
                enriched_rows.append({"raw": row})
        data["render_results"] = enriched_rows
    return data


def _list_recent_runs(limit: int = 12) -> list[dict[str, Any]]:
    if not RUNS_ROOT.exists():
        return []
    rows: list[dict[str, Any]] = []
    for mode_dir in RUNS_ROOT.iterdir():
        if not mode_dir.is_dir() or mode_dir.name == "uploads":
            continue
        for run_dir in mode_dir.iterdir():
            if not run_dir.is_dir():
                continue
            report = run_dir / "report.json"
            row = {
                "mode": mode_dir.name,
                "run_id": run_dir.name,
                "title": _recent_title_from_topic(None, run_dir.name),
                "path": str(run_dir),
                "updated_at": run_dir.stat().st_mtime,
                "status": "unknown",
            }
            if report.exists():
                try:
                    data = _enrich_result_with_urls(json.loads(report.read_text(encoding="utf-8")))
                    row["status"] = data.get("status", "unknown")
                    row["title"] = _recent_title_from_topic(str(data.get("topic") or ""), run_dir.name)
                    row["image_count"] = len(data.get("images", []))
                    first_urls = data.get("image_urls", [])
                    if first_urls:
                        row["cover_url"] = first_urls[0]
                except Exception:
                    row["status"] = "invalid-report"
            rows.append(row)
    rows.sort(key=lambda item: item["updated_at"], reverse=True)
    return rows[:limit]


def _template_context(lang: str) -> dict[str, Any]:
    alt_lang = "en" if lang == "zh" else "zh"
    return {
        "lang": lang,
        "alt_lang": alt_lang,
        "i18n": I18N[lang],
        "modes": list(MODE_TO_SKILL.keys()),
        "recent_runs": _list_recent_runs(),
    }


def _resolve_lang(request: Request) -> str:
    cookie_lang = request.cookies.get("copy2image_lang") or request.cookies.get("t2i_lang")
    if cookie_lang in I18N:
        return str(cookie_lang)
    return "zh"


@app.get("/", include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    lang = _resolve_lang(request)
    return templates.TemplateResponse(request=request, name="index.html", context=_template_context(lang))


@app.get("/settings", include_in_schema=False)
async def settings_page(request: Request) -> HTMLResponse:
    lang = _resolve_lang(request)
    return templates.TemplateResponse(request=request, name="settings.html", context=_template_context(lang))


@app.get("/zh", response_class=HTMLResponse, include_in_schema=False)
async def page_zh() -> RedirectResponse:
    response = RedirectResponse(url="/")
    response.set_cookie("copy2image_lang", "zh", max_age=31536000, samesite="lax")
    return response


@app.get("/en", response_class=HTMLResponse, include_in_schema=False)
async def page_en() -> RedirectResponse:
    response = RedirectResponse(url="/")
    response.set_cookie("copy2image_lang", "en", max_age=31536000, samesite="lax")
    return response


@app.post("/api/lang")
async def api_lang(payload: LangPayload) -> JSONResponse:
    lang = str(payload.lang).strip().lower()
    if lang not in I18N:
        raise HTTPException(status_code=400, detail=f"Invalid lang: {payload.lang}")
    response = JSONResponse({"status": "ok", "lang": lang})
    response.set_cookie("copy2image_lang", lang, max_age=31536000, samesite="lax")
    return response


@app.get("/api/inspect")
async def api_inspect() -> dict[str, Any]:
    skills_root = PROJECT_ROOT / "skills"
    backend = skills_root / "t2i-imagine" / "scripts" / "main.ts"
    return {
        "project_root": str(PROJECT_ROOT),
        "skills_root": str(skills_root),
        "modes": {mode: str((skills_root / skill)) for mode, skill in MODE_TO_SKILL.items()},
        "backend_script": str(backend),
        "backend_exists": backend.exists(),
    }


@app.get("/api/options")
async def api_options() -> dict[str, Any]:
    return {"modes": MODE_OPTIONS}


@app.get("/api/settings")
async def api_settings_get() -> dict[str, Any]:
    settings = _load_settings()
    return settings.model_dump()


@app.post("/api/settings")
async def api_settings_save(payload: WebSettingsPayload) -> dict[str, Any]:
    saved = _save_settings(payload)
    return {"status": "ok", "settings": saved.model_dump()}


@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext or '(none)'}. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXTS))}",
        )

    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    day_dir = UPLOADS_ROOT / datetime.now().strftime("%Y%m%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%H%M%S")
    safe_name = _safe_filename(filename)
    target_path = day_dir / f"{stamp}-{safe_name}{ext}"

    with target_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    await file.close()

    try:
        text = _read_upload_as_text(target_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse uploaded document: {exc}") from exc
    if not text:
        raise HTTPException(status_code=400, detail="Uploaded document is empty after text extraction.")

    extracted_path = target_path.with_suffix(".extracted.md")
    extracted_path.write_text(text + "\n", encoding="utf-8")
    preview = text[:220]
    return {
        "status": "ok",
        "original_file": str(target_path),
        "content_file": str(extracted_path),
        "preview": preview,
    }


@app.post("/api/upload_ref")
async def api_upload_ref(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="No reference files uploaded.")
    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    day_dir = UPLOADS_ROOT / "refs" / datetime.now().strftime("%Y%m%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    uploaded_items: list[dict[str, str]] = []
    for idx, file in enumerate(files, start=1):
        filename = file.filename or ""
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_REF_EXTS:
            await file.close()
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported reference file type: {ext or '(none)'}. Allowed: {', '.join(sorted(ALLOWED_REF_EXTS))}",
            )
        stamp = datetime.now().strftime("%H%M%S")
        safe_name = _safe_filename(filename)
        target_path = day_dir / f"{stamp}-{idx:02d}-{safe_name}{ext}"
        with target_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        await file.close()
        uploaded_items.append(
            {
                "original_file": filename,
                "ref_file": str(target_path.resolve()),
            }
        )
    return {
        "status": "ok",
        "items": uploaded_items,
        "ref_images": [item["ref_file"] for item in uploaded_items],
    }


@app.get("/api/runs")
async def api_runs(limit: int = 20) -> dict[str, Any]:
    return {"items": _list_recent_runs(limit=limit)}


@app.get("/api/runs/{mode}/{run_id}")
async def api_run_detail(mode: str, run_id: str) -> dict[str, Any]:
    report_path = RUNS_ROOT / mode / run_id / "report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Run not found")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return _enrich_result_with_urls(report)


@app.post("/api/run")
async def api_run(payload: RunPayload) -> dict[str, Any]:
    global _ACTIVE_CANCEL_EVENT, _ACTIVE_THREAD_ID
    mode = _normalize_text(payload.mode)
    if not mode or mode not in MODE_TO_SKILL:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {payload.mode}")

    options = MODE_OPTIONS.get(mode, {})
    styles = set(options.get("styles", []))
    layouts = set(options.get("layouts", []))
    palettes = set(options.get("palettes", []))
    tones = set(options.get("tones", []))
    langs = set(options.get("langs", []))
    types = set(options.get("types", []))
    presets = set(options.get("presets", []))
    densities = set(options.get("densities", []))
    supports_palette = bool(options.get("supports_palette", False))
    supports_ref = bool(options.get("supports_ref", False))
    cover_types = set(options.get("cover_types", []))
    renderings = set(options.get("renderings", []))
    text_levels = set(options.get("text_levels", []))
    moods = set(options.get("moods", []))
    fonts = set(options.get("fonts", []))

    illustration_type = _normalize_text(payload.type)
    preset = _normalize_text(payload.preset)
    density = _normalize_text(payload.density)
    style = _normalize_text(payload.style)
    layout = _normalize_text(payload.layout)
    palette = _normalize_text(payload.palette)
    tone = _normalize_text(payload.tone)
    lang = _normalize_text(payload.lang)
    cover_type = _normalize_text(payload.cover_type)
    rendering = _normalize_text(payload.rendering)
    text_level = _normalize_text(payload.text_level)
    mood = _normalize_text(payload.mood)
    font = _normalize_text(payload.font)
    ref_images = [_normalize_text(x) for x in (payload.ref_images or [])]
    ref_images = [x for x in ref_images if x]
    content = payload.content or ""
    content_file = _normalize_text(payload.content_file)

    if preset:
        if not presets:
            raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support preset.")
        if preset not in presets:
            raise HTTPException(status_code=400, detail=f"Invalid preset '{preset}' for mode '{mode}'.")
    if density:
        if not densities:
            raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support density.")
        if density not in densities:
            raise HTTPException(status_code=400, detail=f"Invalid density '{density}' for mode '{mode}'.")

    if mode == "image-cards" and preset:
        preset_vals = IMAGE_CARD_PRESET_MAP.get(preset)
        if preset_vals:
            mapped_style, mapped_layout, mapped_palette = preset_vals
            style = style or mapped_style
            layout = layout or mapped_layout
            palette = palette or mapped_palette
    if mode == "article-illustrator" and preset:
        preset_vals = ARTICLE_PRESET_MAP.get(preset)
        if preset_vals:
            mapped_type, mapped_style, mapped_palette = preset_vals
            illustration_type = illustration_type or mapped_type
            style = style or mapped_style
            palette = palette or mapped_palette
    if mode == "cover-image" and style:
        style_vals = COVER_STYLE_MAP.get(style)
        if style_vals:
            mapped_palette, mapped_rendering = style_vals
            palette = palette or mapped_palette
            rendering = rendering or mapped_rendering

    if illustration_type:
        if not types:
            raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support type.")
        if illustration_type not in types:
            raise HTTPException(status_code=400, detail=f"Invalid type '{illustration_type}' for mode '{mode}'.")
    if style and styles and style not in styles:
        raise HTTPException(status_code=400, detail=f"Invalid style '{style}' for mode '{mode}'.")
    if layout and layouts and layout not in layouts:
        raise HTTPException(status_code=400, detail=f"Invalid layout '{layout}' for mode '{mode}'.")
    if palette:
        if not supports_palette:
            raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support palette.")
        if palettes and palette not in palettes:
            raise HTTPException(status_code=400, detail=f"Invalid palette '{palette}' for mode '{mode}'.")
    else:
        palette = None

    if not supports_palette:
        palette = None
    if tone:
        if not tones:
            raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support tone.")
        if tone not in tones:
            raise HTTPException(status_code=400, detail=f"Invalid tone '{tone}' for mode '{mode}'.")
    if lang:
        if not langs:
            raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support lang.")
        if lang not in langs:
            raise HTTPException(status_code=400, detail=f"Invalid lang '{lang}' for mode '{mode}'.")
    if cover_type:
        if not cover_types:
            raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support cover_type.")
        if cover_type not in cover_types:
            raise HTTPException(status_code=400, detail=f"Invalid cover_type '{cover_type}' for mode '{mode}'.")
    if rendering:
        if not renderings:
            raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support rendering.")
        if rendering not in renderings:
            raise HTTPException(status_code=400, detail=f"Invalid rendering '{rendering}' for mode '{mode}'.")
    if text_level:
        if not text_levels:
            raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support text_level.")
        if text_level not in text_levels:
            raise HTTPException(status_code=400, detail=f"Invalid text_level '{text_level}' for mode '{mode}'.")
    if mood:
        if not moods:
            raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support mood.")
        if mood not in moods:
            raise HTTPException(status_code=400, detail=f"Invalid mood '{mood}' for mode '{mode}'.")
    if font:
        if not fonts:
            raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support font.")
        if font not in fonts:
            raise HTTPException(status_code=400, detail=f"Invalid font '{font}' for mode '{mode}'.")
    if ref_images and not supports_ref:
        raise HTTPException(status_code=400, detail=f"Mode '{mode}' does not support reference images.")
    validated_refs: list[str] = []
    for raw_ref in ref_images:
        try:
            ref_path = Path(raw_ref).resolve()
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid reference path: {raw_ref}") from None
        if not ref_path.exists():
            raise HTTPException(status_code=400, detail=f"Reference image does not exist: {raw_ref}")
        if ref_path.suffix.lower() not in ALLOWED_REF_EXTS:
            raise HTTPException(status_code=400, detail=f"Unsupported reference image type: {ref_path.suffix}")
        validated_refs.append(str(ref_path))

    topic = _infer_topic(mode, payload.topic, content, content_file)
    output_root = str((PROJECT_ROOT / payload.output_root).resolve())
    settings = _load_settings()

    effective_provider = _first_non_empty(_normalize_text(payload.provider), settings.image.provider)
    effective_model = _first_non_empty(_normalize_text(payload.model), settings.image.model)
    effective_dialect = _first_non_empty(_normalize_text(payload.image_api_dialect), settings.image.image_api_dialect)

    text_api_key = _first_non_empty(
        settings.text.api_key,
        os.environ.get("COPY2IMAGE_WORKFLOW_TEXT_API_KEY"),
        os.environ.get("T2I_AGENT_TEXT_API_KEY"),
        os.environ.get("OPENAI_API_KEY"),
    )
    text_base_url = _first_non_empty(
        settings.text.base_url,
        os.environ.get("COPY2IMAGE_WORKFLOW_TEXT_BASE_URL"),
        os.environ.get("T2I_AGENT_TEXT_BASE_URL"),
        os.environ.get("OPENAI_BASE_URL"),
    )
    text_model = _first_non_empty(
        settings.text.model,
        os.environ.get("COPY2IMAGE_WORKFLOW_TEXT_MODEL"),
        os.environ.get("T2I_AGENT_TEXT_MODEL"),
        os.environ.get("OPENAI_TEXT_MODEL"),
        os.environ.get("OPENAI_MODEL"),
        os.environ.get("OPENAI_IMAGE_MODEL"),
    )

    image_api_key = _first_non_empty(settings.image.api_key, os.environ.get("OPENAI_API_KEY"))
    image_base_url = _first_non_empty(settings.image.base_url, os.environ.get("OPENAI_BASE_URL"))
    image_model_for_env = _first_non_empty(
        effective_model,
        settings.image.model,
        os.environ.get("OPENAI_IMAGE_MODEL"),
        os.environ.get("OPENAI_MODEL"),
    )
    image_dialect_for_env = _first_non_empty(
        effective_dialect,
        settings.image.image_api_dialect,
        os.environ.get("OPENAI_IMAGE_API_DIALECT"),
    )

    try:
        request_obj = Copy2ImageRequest(
            mode=mode,
            topic=topic,
            content=content,
            content_file=content_file,
            type=illustration_type,
            preset=preset,
            density=density,
            style=style,
            layout=layout,
            palette=palette,
            tone=tone,
            lang=lang,
            cover_type=cover_type,
            rendering=rendering,
            text_level=text_level,
            mood=mood,
            font=font,
            ref_images=validated_refs,
            image_count=payload.image_count,
            aspect_ratio=payload.aspect_ratio,
            quality=payload.quality,  # type: ignore[arg-type]
            provider=effective_provider,
            model=effective_model,
            image_api_dialect=effective_dialect,
            dry_run=payload.dry_run,
            generate=payload.generate,
            anchor_chain=payload.anchor_chain,
            fail_fast=payload.fail_fast,
            skip_analysis_llm=payload.skip_analysis_llm,
            skip_outline_llm=payload.skip_outline_llm,
            output_root=output_root,
            thread_id=payload.thread_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cancel_event = threading.Event()
    with _RUN_LOCK:
        if _ACTIVE_CANCEL_EVENT is not None:
            raise HTTPException(status_code=409, detail="Another run is currently in progress. Please stop it first.")
        engine.configure_text_client(api_key=text_api_key, base_url=text_base_url, model=text_model)
        _ACTIVE_CANCEL_EVENT = cancel_event
        _ACTIVE_THREAD_ID = request_obj.thread_id

    image_env_overrides = {
        "OPENAI_API_KEY": image_api_key,
        "OPENAI_BASE_URL": image_base_url,
        "OPENAI_IMAGE_MODEL": image_model_for_env,
        "OPENAI_IMAGE_API_DIALECT": image_dialect_for_env,
    }

    try:
        with _temporary_env(image_env_overrides):
            result = await run_in_threadpool(engine.run_sync, request_obj, cancel_event)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        with _RUN_LOCK:
            if _ACTIVE_CANCEL_EVENT is cancel_event:
                _ACTIVE_CANCEL_EVENT = None
                _ACTIVE_THREAD_ID = None
    return _enrich_result_with_urls(result)


@app.post("/api/run/stop")
async def api_run_stop() -> dict[str, Any]:
    with _RUN_LOCK:
        event = _ACTIVE_CANCEL_EVENT
        thread_id = _ACTIVE_THREAD_ID
        if event is None:
            return {"status": "idle", "stopped": False}
        event.set()
    return {"status": "stopping", "stopped": True, "thread_id": thread_id}


