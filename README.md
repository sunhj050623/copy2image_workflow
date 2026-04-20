<div align="center">

# ✨ 文案成图工作流 · Copy2Image Workflow

<p>
  <strong>把文案自动变成图片产出流水线：</strong><br/>
  分析内容 → 生成大纲 → 组装提示词 → 批量出图 → 产出报告
</p>

<p>
  <a href="#-快速开始"><img src="https://img.shields.io/badge/QuickStart-5分钟上手-2ea44f?style=for-the-badge" /></a>
  <a href="#-工作模式"><img src="https://img.shields.io/badge/Modes-6种模式-0969da?style=for-the-badge" /></a>
  <a href="#-分模式参数说明"><img src="https://img.shields.io/badge/Params-分模式参数-f57c00?style=for-the-badge" /></a>
  <a href="#-模型配置web--env"><img src="https://img.shields.io/badge/Config-Web%20%2B%20.env-8250df?style=for-the-badge" /></a>
</p>

<p>
  <a href="#-项目简介">简介</a> •
  <a href="#-快速开始">快速开始</a> •
  <a href="#-工作模式">工作模式</a> •
  <a href="#-分模式参数说明">分模式参数</a> •
  <a href="#-模型配置web--env">模型配置</a> •
  <a href="#-输出结构">输出结构</a>
</p>

</div>

---

## 📌 项目简介

`Copy2Image Workflow` 是一个“从文案到图片”的自动化工作流，适合内容创作、知识传播、运营配图和教学材料生成。

你提供文本，它负责把流程拆解为可执行步骤：

1. 内容分析（`analysis.md`）
2. 结构化大纲（`outline.md`）
3. 分图提示词（`prompts/*.md`）
4. 调用绘图后端生成图片（`*.png`）
5. 汇总运行报告（`report.json`）

---

## 🎯 适用场景

- 📚 知识卡片：教程、清单、框架拆解
- 🧠 信息图：结构化主题的“一图读懂”
- 🎬 漫画化表达：角色对话、故事化讲解
- 📝 文章配图：长文按章节自动配图
- 🧭 图表图示：架构图、流程图、时序图
- 🖼️ 封面图：文章、视频、活动主视觉

---

## 🚀 快速开始

### 1) 安装依赖

```bash
pip install -r requirements.txt
```

### 2) 准备根目录 `.env`

```bash
# Windows PowerShell
Copy-Item .env.example .env
```

把 API Key 和模型填进项目根目录 `.env`。

### 3) 查看可用模式与后端

```bash
python -m copy2image_workflow.cli inspect --project-root .
```

### 4) 先跑一次 dry-run（不消耗出图额度）

```bash
python -m copy2image_workflow.cli run \
  --project-root . \
  --mode image-cards \
  --topic "AI 学习路线图" \
  --content "从基础到实战，分阶段学习并持续复盘" \
  --image-count 4 \
  --style sketch-notes \
  --layout balanced \
  --dry-run
```

### 5) 正式出图

```bash
python -m copy2image_workflow.cli run \
  --project-root . \
  --mode infographic \
  --topic "智能体工程全景" \
  --content-file runs/demo/source.md \
  --aspect-ratio 3:4 \
  --quality 2k
```

---

## 🧩 工作模式

| 模式 | 用途 | 典型产出 |
|---|---|---|
| `image-cards` | 图片卡片、知识拆解 | 系列卡片图 |
| `infographic` | 信息图、结构化表达 | 单页或多页信息图 |
| `comic` | 漫画叙事、角色对话 | 分镜漫画 |
| `article-illustrator` | 长文自动配图 | 每节配图 |
| `diagram` | 架构/流程/时序图 | 技术图示 |
| `cover-image` | 封面图设计 | 文章/视频封面 |

---

## ⚙️ 分模式参数说明

> 下面是“按模式”查看参数，避免不同模式参数混淆。

### 0) 所有模式通用参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `mode` | string | - | 模式名（必填） |
| `topic` | string | - | 主题（Web 可留空自动推断） |
| `content` | string | `""` | 直接输入文案 |
| `content_file` | string | `null` | 文案文件路径（`txt/md/docx`） |
| `ref_images` | string[] | `[]` | 参考图路径数组（仅支持的模式生效） |
| `image_count` | int | `4` | 输出图片数量 |
| `aspect_ratio` | string | `3:4` | 图片比例 |
| `quality` | enum | `2k` | `normal` / `2k` |
| `provider` | string | `null` | 绘图 provider |
| `model` | string | `null` | 绘图模型 |
| `image_api_dialect` | string | `null` | 图片 API 方言 |
| `dry_run` | bool | `false` | 仅生成规划文件，不执行出图 |
| `generate` | bool | `true` | 是否执行出图 |
| `anchor_chain` | bool | `true` | 是否启用首图风格锚定 |
| `fail_fast` | bool | `false` | 出错即停 |
| `skip_analysis_llm` | bool | `false` | 跳过 LLM 内容分析 |
| `skip_outline_llm` | bool | `false` | 跳过 LLM 大纲提炼 |
| `output_root` | string | `runs` | 输出目录根路径 |

### 1) `image-cards`

| 参数 | 是否可用 | 说明 |
|---|---|---|
| `style` | ✅ | 卡片风格 |
| `layout` | ✅ | 布局（`sparse/balanced/dense/list/...`） |
| `palette` | ✅ | 配色 |
| `preset` | ✅ | 预设（会映射 style/layout/palette） |
| `lang` | ✅ | 语言倾向 |
| `tone` | ❌ | 不使用 |
| `type` / `density` | ❌ | 不使用 |

### 2) `infographic`

| 参数 | 是否可用 | 说明 |
|---|---|---|
| `style` | ✅ | 信息图风格 |
| `layout` | ✅ | 信息图布局模板 |
| `lang` | ✅ | 语言倾向 |
| `palette` | ❌ | 不使用 |
| `tone` | ❌ | 不使用 |
| `type` / `density` / `preset` | ❌ | 不使用 |

### 3) `comic`

| 参数 | 是否可用 | 说明 |
|---|---|---|
| `style` | ✅ | 漫画画风 |
| `layout` | ✅ | 分镜布局 |
| `tone` | ✅ | 情绪基调 |
| `lang` | ✅ | 语言倾向 |
| `palette` | ❌ | 不使用 |
| `type` / `density` / `preset` | ❌ | 不使用 |

### 4) `article-illustrator`

| 参数 | 是否可用 | 说明 |
|---|---|---|
| `type` | ✅ | 配图类型（如 `infographic/scene/flowchart/...`） |
| `density` | ✅ | 配图密度（`minimal/balanced/per-section/rich`） |
| `preset` | ✅ | 预设（会映射 type/style/palette） |
| `style` | ✅ | 插画风格 |
| `palette` | ✅ | 配色 |
| `lang` | ✅ | 语言倾向 |
| `layout` | ❌ | 不使用 |
| `tone` | ❌ | 不使用 |

### 5) `diagram`

| 参数 | 是否可用 | 说明 |
|---|---|---|
| `layout` | ✅ | 图表类型（`architecture/flowchart/sequence/...`） |
| `style` | ✅ | 图表风格 |
| `lang` | ✅ | 语言倾向 |
| `palette` | ❌ | 不使用 |
| `tone` | ❌ | 不使用 |
| `type` / `density` / `preset` | ❌ | 不使用 |
| `ref_images` | ❌ | 不支持参考图 |

### 6) `cover-image`

| 参数 | 是否可用 | 说明 |
|---|---|---|
| `style` | ✅ | 封面风格预设 |
| `palette` | ✅ | 封面配色 |
| `cover_type` | ✅ | 封面类型 |
| `rendering` | ✅ | 渲染风格 |
| `text_level` | ✅ | 文字密度 |
| `mood` | ✅ | 情绪强度 |
| `font` | ✅ | 字体风格 |
| `lang` | ✅ | 语言倾向 |
| `layout` / `tone` / `type` / `density` | ❌ | 不使用 |

---

## 🔐 模型配置（Web + .env）

你可以通过两种方式配置模型：

### A) Web 设置页配置（推荐日常使用）

打开：`/settings` 页面，分别填写：

- Text Model：`API Key` / `Base URL` / `Model`
- Image Model：`API Key` / `Base URL` / `Model` / `Provider` / `API Dialect`

保存后会写入：`runs/web_settings.json`。

适用：
- 频繁改模型
- 团队内演示与测试
- 不想改文件时

### B) 根目录 `.env` 配置（推荐稳定部署）

项目根目录放置 `.env`（可从 `.env.example` 复制），示例：

```env
# 文本模型（用于分析/大纲/提示词）
COPY2IMAGE_WORKFLOW_TEXT_API_KEY=sk-xxx
COPY2IMAGE_WORKFLOW_TEXT_BASE_URL=https://api.openai.com/v1
COPY2IMAGE_WORKFLOW_TEXT_MODEL=gpt-4o-mini

# 生图模型（用于最终渲染）
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_IMAGE_MODEL=gpt-image-1
OPENAI_IMAGE_API_DIALECT=openai-native

# 可选
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_MODEL=gpt-4o-mini
```

适用：
- 本地长期开发
- 容器部署
- CI/CD 或自动化任务

### 配置优先级（非常重要）

#### 文本模型参数（Text）

1. 本次请求显式传入（如果有）
2. Web 设置页保存值（`runs/web_settings.json`）
3. 根目录 `.env` / 系统环境变量

#### 生图模型参数（Image）

1. 本次请求显式传入 `provider/model/image_api_dialect`
2. Web 设置页保存值（`runs/web_settings.json`）
3. 根目录 `.env` / 系统环境变量（`OPENAI_*`）

> 也就是说：你既可以用 Web 调参，也可以用 `.env` 固化默认值，两者可以并存。

---

## 🌐 Web 界面

启动服务：

```bash
uvicorn copy2image_workflow.web.app:app --host 0.0.0.0 --port 8000
```

访问地址：

- 中文：`http://localhost:8000/zh`
- 英文：`http://localhost:8000/en`
- 设置：`http://localhost:8000/settings`

支持能力：

- ✍️ 文案直输 / 文档上传
- 🖼️ 参考图上传
- 🛑 任务中断
- 🧾 最近任务回看
- 🔧 文本模型与生图模型独立配置

---

## 🐳 Docker

### 构建并运行

```bash
docker build -t copy2image-workflow:latest .
docker run --rm -p 8001:8000 -v %cd%:/app -w /app copy2image-workflow:latest
```

### Compose

> 程序会自动读取项目根目录 `.env`

```bash
docker compose up --build -d
```

浏览器访问：`http://localhost:8001/zh`

### 容器内运行 CLI

```bash
docker run --rm \
  -v %cd%:/app \
  -w /app \
  --entrypoint python \
  copy2image-workflow:latest \
  -m copy2image_workflow.cli run \
  --project-root /app \
  --mode image-cards \
  --topic "知识卡片示例" \
  --content "用简洁中文输出 4 页卡片" \
  --image-count 4
```

---

## 📂 输出结构

每次运行会在 `runs/<mode>/<topic>-<timestamp>/` 生成：

- `analysis.md`：内容分析
- `outline.md`：结构化大纲
- `prompts/*.md`：分图提示词
- `*.png`：生成图片
- `report.json`：状态、路径、命令与日志

示例：

```text
runs/
└─ image-cards/
   └─ ai-roadmap-20260420-190107/
      ├─ analysis.md
      ├─ outline.md
      ├─ prompts/
      │  ├─ 01-cover-xxx.md
      │  └─ 02-content-xxx.md
      ├─ 01-cover-xxx.png
      └─ report.json
```

---

## ❓ 常见问题

### 1) 为什么建议先用 `--dry-run`？

因为你可以先检查分析、大纲、提示词是否符合预期，再决定是否正式出图，能显著降低调参成本。

### 2) 任务运行中可以停止吗？

可以。Web 端点击“停止当前任务”，或调用 `POST /api/run/stop`。

### 3) 怎么提高多图风格一致性？

保持 `anchor_chain=true`，并固定 `style/layout/palette` 组合，通常能获得更稳定的系列视觉结果。

---

## 🤝 使用建议

如果你要给团队协作使用，推荐先沉淀 2-3 套“默认模板”（风格 + 布局 + 配色 + 比例），并把它写进内部 SOP。

这样可以让新成员也快速产出一致质量，减少反复沟通，把更多时间留给内容本身。
