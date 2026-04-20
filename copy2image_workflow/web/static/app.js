const i18n = window.COPY2IMAGE_I18N || {};
const LANG = window.COPY2IMAGE_LANG || "zh";

const autoLabel = i18n?.placeholders?.auto || "Auto (recommended)";
const emptyUploadLabel = i18n?.placeholders?.upload_status_empty || "No file uploaded";
const runningLabel = LANG === "zh" ? "运行中..." : "Running...";
const stoppingLabel = LANG === "zh" ? "正在停止..." : "Stopping...";
const uploadingLabel = LANG === "zh" ? "上传中..." : "Uploading...";
const uploadFailedLabel = LANG === "zh" ? "上传失败" : "Upload failed";
const emptyRefUploadLabel = i18n?.placeholders?.ref_status_empty || (LANG === "zh" ? "未上传参考图" : "No reference image uploaded");
const refUploadingLabel = LANG === "zh" ? "参考图上传中..." : "Uploading reference images...";
const refUploadFailedLabel = LANG === "zh" ? "参考图上传失败" : "Reference upload failed";
const dryRunHint = LANG === "zh" ? "当前是 dry-run，仅展示规划文件。" : "This is dry-run. Planned outputs only.";
const noImageHint = LANG === "zh" ? "当前任务没有可展示图片。" : "No images available for this run.";
const cancelledHint = LANG === "zh" ? "任务已取消。" : "Task cancelled.";
const sourceRequiredHint = LANG === "zh" ? "请先上传文档或切回直接输入。" : "Upload a document first or switch back to direct input.";
const resultEmptyLabel = LANG === "zh" ? "生成结果" : "Results";

const THEME_KEY = "copy2image_theme";

let optionsByMode = {};
let activeSource = "text";
let activeRunController = null;
let hasLoadedInitialHistory = false;
let activeRefImages = [];
let activeRefPreviewRows = [];
let resultImageUrls = [];
let resultPage = 1;
const RESULT_PAGE_SIZE = 4;

function themeIconSvg(isDark) {
  if (isDark) {
    return `
      <span class="btn-icon-wrap" aria-hidden="true">
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="4.2"></circle>
          <path d="M12 2v2.2"></path>
          <path d="M12 19.8V22"></path>
          <path d="m4.9 4.9 1.5 1.5"></path>
          <path d="m17.6 17.6 1.5 1.5"></path>
          <path d="M2 12h2.2"></path>
          <path d="M19.8 12H22"></path>
          <path d="m4.9 19.1 1.5-1.5"></path>
          <path d="m17.6 6.4 1.5-1.5"></path>
        </svg>
      </span>
    `;
  }
  return `
    <span class="btn-icon-wrap" aria-hidden="true">
      <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"></path>
      </svg>
    </span>
  `;
}

function emptyResultMarkup(label) {
  return `
    <div class="result-empty">
      <svg class="result-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3.5" y="5" width="13" height="13" rx="2.2"></rect>
        <circle cx="8.2" cy="9.2" r="1.3"></circle>
        <path d="m7 15 2.8-2.6L12.2 15"></path>
        <path d="m18 6 3 3"></path>
        <path d="M21 6h-3"></path>
        <path d="M21 6v3"></path>
      </svg>
      <span>${label || resultEmptyLabel}</span>
    </div>
  `;
}

function prefersReducedMotion() {
  return Boolean(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
}

function setButtonLoading(button, loading) {
  if (!button) return;
  button.classList.toggle("btn-loading", loading);
  button.setAttribute("aria-busy", loading ? "true" : "false");
}

function applyStagger(container, selector) {
  if (!container) return;
  const items = Array.from(container.querySelectorAll(selector));
  if (!items.length) return;

  const reduced = prefersReducedMotion();
  items.forEach((item, idx) => {
    item.classList.add("stagger-item");
    item.style.setProperty("--stagger-index", String(idx));
    if (reduced) {
      item.classList.add("is-visible");
      return;
    }
    requestAnimationFrame(() => item.classList.add("is-visible"));
  });
}

const ZH_OPTION_LABELS = {
  "image-cards": {
    style: {
      "bold": "高对比强调风",
      "chalkboard": "黑板手绘风",
      "cute": "可爱贴纸风",
      "fresh": "清新自然风",
      "minimal": "极简专业风",
      "notion": "知识笔记风",
      "pop": "潮流波普风",
      "retro": "复古胶片风",
      "screen-print": "丝网印刷海报风",
      "sketch-notes": "手绘草图笔记风",
      "study-notes": "真实学习笔记风",
      "warm": "温暖生活风"
    },
    layout: {
      "sparse": "稀疏布局",
      "balanced": "均衡布局",
      "dense": "高密布局",
      "list": "列表布局",
      "comparison": "对比布局",
      "flow": "流程布局",
      "mindmap": "脑图布局",
      "quadrant": "四象限布局"
    },
    palette: {
      "macaron": "马卡龙配色",
      "warm": "暖色配色",
      "neon": "霓虹配色"
    },
    preset: {
      "knowledge-card": "知识卡片",
      "checklist": "清单卡片",
      "concept-map": "概念图",
      "swot": "SWOT 分析",
      "tutorial": "教程流程",
      "classroom": "课堂风",
      "study-guide": "学习指南",
      "cute-share": "可爱分享",
      "girly": "少女风",
      "cozy-story": "温暖故事",
      "product-review": "产品测评",
      "nature-flow": "自然流程",
      "warning": "警示清单",
      "versus": "对比风",
      "clean-quote": "极简金句",
      "pro-summary": "专业总结",
      "retro-ranking": "复古排行",
      "throwback": "怀旧风",
      "pop-facts": "流行事实",
      "hype": "高能封面",
      "poster": "海报风",
      "editorial": "社论风",
      "cinematic": "电影感",
      "hand-drawn-edu": "手绘教育",
      "sketch-card": "手绘卡片",
      "sketch-summary": "手绘总结"
    },
    lang: {
      "auto": "自动",
      "zh": "中文",
      "en": "英文",
      "ja": "日文"
    }
  },
  "infographic": {
    style: {
      "aged-academia": "复古学院风",
      "bold-graphic": "粗线图形风",
      "chalkboard": "黑板粉笔风",
      "claymation": "黏土插画风",
      "corporate-memphis": "孟菲斯商务风",
      "craft-handmade": "手作拼贴风",
      "cyberpunk-neon": "赛博霓虹风",
      "hand-drawn-edu": "手绘教育风",
      "ikea-manual": "宜家说明书风",
      "kawaii": "日系可爱风",
      "knolling": "平铺整理风",
      "lego-brick": "乐高积木风",
      "morandi-journal": "莫兰迪手账风",
      "origami": "折纸风",
      "pixel-art": "像素风",
      "pop-laboratory": "流行实验室风",
      "retro-pop-grid": "复古波普网格风",
      "storybook-watercolor": "绘本水彩风",
      "subway-map": "地铁线路图风",
      "technical-schematic": "技术示意图风",
      "ui-wireframe": "UI 线框风"
    },
    layout: {
      "bento-grid": "便当网格",
      "binary-comparison": "二元对照",
      "bridge": "桥接结构",
      "circular-flow": "环形流程",
      "comic-strip": "漫画条带",
      "comparison-matrix": "对比矩阵",
      "dashboard": "仪表盘",
      "dense-modules": "高密模块",
      "funnel": "漏斗",
      "hierarchical-layers": "层级结构",
      "hub-spoke": "中心辐射",
      "iceberg": "冰山结构",
      "isometric-map": "等距地图",
      "jigsaw": "拼图结构",
      "linear-progression": "线性推进",
      "periodic-table": "周期表结构",
      "story-mountain": "故事山",
      "structural-breakdown": "结构拆解",
      "tree-branching": "树状分叉",
      "venn-diagram": "维恩图",
      "winding-roadmap": "蜿蜒路线图"
    },
    lang: {
      "auto": "自动",
      "zh": "中文",
      "en": "英文",
      "ja": "日文"
    }
  },
  "comic": {
    style: {
      "chalk": "粉笔漫画风",
      "ink-brush": "水墨漫画风",
      "ligne-claire": "清线漫画风",
      "manga": "日漫风",
      "minimalist": "极简漫画风",
      "realistic": "写实漫画风"
    },
    layout: {
      "cinematic": "电影分镜布局",
      "dense": "高密分镜布局",
      "four-panel": "四格布局",
      "mixed": "混合分镜布局",
      "splash": "跨页大场景布局",
      "standard": "标准分镜布局",
      "webtoon": "条漫竖屏布局"
    },
    tone: {
      "action": "动作热血",
      "dramatic": "戏剧张力",
      "energetic": "活力动感",
      "neutral": "中性叙事",
      "romantic": "浪漫情绪",
      "vintage": "复古调性",
      "warm": "温暖氛围"
    },
    lang: {
      "auto": "自动",
      "zh": "中文",
      "en": "英文",
      "ja": "日文"
    }
  },
  "article-illustrator": {
    type: {
      "infographic": "信息图",
      "scene": "场景插图",
      "flowchart": "流程图",
      "comparison": "对比图",
      "framework": "框架图",
      "timeline": "时间线",
      "mixed": "混合类型"
    },
    density: {
      "minimal": "简约（1-2）",
      "balanced": "均衡（3-5）",
      "per-section": "按章节（推荐）",
      "rich": "丰富（6+）"
    },
    preset: {
      "tech-explainer": "技术解读",
      "system-design": "系统设计",
      "architecture": "架构解读",
      "science-paper": "科研论文",
      "knowledge-base": "知识库风",
      "saas-guide": "SaaS 指南",
      "tutorial": "教程模式",
      "process-flow": "流程说明",
      "warm-knowledge": "暖色知识卡",
      "edu-visual": "教育可视化",
      "hand-drawn-edu": "手绘教育",
      "ink-notes-compare": "墨线对比",
      "ink-notes-flow": "墨线流程",
      "ink-notes-framework": "墨线框架",
      "data-report": "数据报告",
      "versus": "对比分析",
      "business-compare": "商业对比",
      "storytelling": "叙事风",
      "lifestyle": "生活方式",
      "history": "历史时间线",
      "evolution": "演进路径",
      "opinion-piece": "观点评论",
      "editorial-poster": "社论海报",
      "cinematic": "电影感叙事"
    },
    style: {
      "blueprint": "蓝图工程风",
      "chalkboard": "黑板风",
      "editorial": "杂志编辑风",
      "elegant": "优雅精致风",
      "fantasy-animation": "幻想动画风",
      "flat": "扁平插画风",
      "flat-doodle": "扁平涂鸦风",
      "ink-notes": "墨线笔记风",
      "intuition-machine": "技术机理风",
      "minimal": "极简风",
      "nature": "自然有机风",
      "notion": "知识笔记风",
      "pixel-art": "像素风",
      "playful": "活泼趣味风",
      "retro": "复古风",
      "scientific": "科学示意风",
      "screen-print": "丝网印刷风",
      "sketch": "速写草图风",
      "sketch-notes": "手绘笔记风",
      "vector-illustration": "矢量插画风",
      "vintage": "旧时代风",
      "warm": "温暖叙事风",
      "watercolor": "水彩风"
    },
    palette: {
      "macaron": "马卡龙配色",
      "mono-ink": "单色墨线配色",
      "neon": "霓虹配色",
      "warm": "暖色配色"
    },
    lang: {
      "auto": "自动",
      "zh": "中文",
      "en": "英文",
      "ja": "日文"
    }
  },
  "diagram": {
    style: {
      "clean-diagram": "清晰图表风"
    },
    layout: {
      "architecture": "架构图",
      "flowchart": "流程图",
      "sequence": "时序图",
      "structural": "结构图",
      "mind-map": "思维导图",
      "timeline": "时间线",
      "illustrative": "示意图",
      "state-machine": "状态机",
      "data-flow": "数据流图"
    },
    lang: {
      "auto": "自动",
      "zh": "中文",
      "en": "英文",
      "ja": "日文"
    }
  },
  "cover-image": {
    style: {
      "elegant": "优雅预设",
      "blueprint": "蓝图预设",
      "chalkboard": "黑板预设",
      "dark-atmospheric": "暗调氛围",
      "editorial-infographic": "社论信息图",
      "fantasy-animation": "幻想动画",
      "flat-doodle": "扁平涂鸦",
      "intuition-machine": "机理风",
      "minimal": "极简预设",
      "nature": "自然预设",
      "notion": "笔记预设",
      "pixel-art": "像素预设",
      "playful": "活泼预设",
      "retro": "复古预设",
      "sketch-notes": "手绘笔记",
      "vector-illustration": "矢量插图",
      "vintage": "复古质感",
      "warm": "暖色预设",
      "warm-flat": "暖色扁平",
      "hand-drawn-edu": "手绘教育",
      "watercolor": "水彩预设",
      "poster-art": "海报艺术",
      "mondo": "Mondo 风",
      "art-deco": "装饰艺术",
      "propaganda": "宣传画风",
      "cinematic": "电影感"
    },
    preset: {
      "elegant": "优雅预设",
      "blueprint": "蓝图预设",
      "chalkboard": "黑板预设",
      "dark-atmospheric": "暗调氛围",
      "editorial-infographic": "社论信息图",
      "fantasy-animation": "幻想动画",
      "flat-doodle": "扁平涂鸦",
      "intuition-machine": "机理风",
      "minimal": "极简预设",
      "nature": "自然预设",
      "notion": "笔记预设",
      "pixel-art": "像素预设",
      "playful": "活泼预设",
      "retro": "复古预设",
      "sketch-notes": "手绘笔记",
      "vector-illustration": "矢量插图",
      "vintage": "复古质感",
      "warm": "暖色预设",
      "warm-flat": "暖色扁平",
      "hand-drawn-edu": "手绘教育",
      "watercolor": "水彩预设",
      "poster-art": "海报艺术",
      "mondo": "Mondo 风",
      "art-deco": "装饰艺术",
      "propaganda": "宣传画风",
      "cinematic": "电影感"
    },
    cover_type: {
      "hero": "主视觉封面",
      "conceptual": "概念化封面",
      "typography": "排版主导封面",
      "metaphor": "隐喻封面",
      "scene": "场景化封面",
      "minimal": "极简封面"
    },
    rendering: {
      "flat-vector": "扁平矢量",
      "hand-drawn": "手绘",
      "painterly": "绘画感",
      "digital": "数字插画",
      "pixel": "像素风",
      "chalk": "粉笔风",
      "screen-print": "丝网印刷"
    },
    text_level: {
      "none": "无文字",
      "title-only": "仅标题",
      "title-subtitle": "标题+副标题",
      "text-rich": "高文字密度"
    },
    mood: {
      "subtle": "克制",
      "balanced": "均衡",
      "bold": "强烈"
    },
    font: {
      "clean": "简洁",
      "handwritten": "手写",
      "serif": "衬线",
      "display": "展示体"
    },
    palette: {
      "cool": "冷色配色",
      "dark": "暗色配色",
      "duotone": "双色调配色",
      "earth": "大地配色",
      "elegant": "优雅配色",
      "macaron": "马卡龙配色",
      "mono": "单色配色",
      "pastel": "粉彩配色",
      "retro": "复古配色",
      "vibrant-contrast": "高对比鲜明配色",
      "vivid": "高饱和配色",
      "warm": "暖色配色"
    },
    lang: {
      "auto": "自动",
      "zh": "中文",
      "en": "英文",
      "ja": "日文"
    }
  }
};

function textFromForm(fd, name) {
  return (fd.get(name) || "").toString().trim();
}

function checked(form, name) {
  return form.querySelector(`[name="${name}"]`)?.checked ?? false;
}

function modeLabel(mode) {
  return i18n?.modes?.[mode] || mode;
}

function displayOptionLabel(item, mode, kind) {
  if (LANG !== "zh") return item;
  const map = ZH_OPTION_LABELS?.[mode]?.[kind] || {};
  return map[item] || item;
}

function setSelectOptions(select, items, currentValue, mode, kind) {
  if (!select) return;
  select.innerHTML = "";

  const autoOption = document.createElement("option");
  autoOption.value = "";
  autoOption.textContent = autoLabel;
  select.appendChild(autoOption);

  const safeItems = Array.isArray(items) ? items : [];
  safeItems.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = displayOptionLabel(item, mode, kind);
    select.appendChild(opt);
  });

  if (currentValue && safeItems.includes(currentValue)) {
    select.value = currentValue;
  } else {
    select.value = "";
  }
}

function toggleBlock(container, visible) {
  if (!container) return;

  const computedDisplay = window.getComputedStyle(container).display;
  if (!container.dataset.origDisplay && computedDisplay !== "none") {
    container.dataset.origDisplay = computedDisplay;
  }
  if (container.classList.contains("hidden")) {
    container.classList.remove("hidden");
  }
  container.classList.add("collapsible");

  const reduced = prefersReducedMotion();
  const isCollapsed = container.classList.contains("is-collapsed");
  if (visible && !isCollapsed) return;
  if (!visible && isCollapsed) return;

  if (reduced) {
    container.classList.toggle("is-collapsed", !visible);
    container.style.maxHeight = visible ? "none" : "0px";
    container.style.display = visible ? (container.dataset.origDisplay || "") : "none";
    return;
  }

  if (visible) {
    container.style.display = container.dataset.origDisplay || "";
    container.classList.remove("is-collapsed");
    container.style.maxHeight = "0px";
    container.style.opacity = "0";
    container.style.transform = "translateY(-6px)";
    requestAnimationFrame(() => {
      container.style.maxHeight = `${container.scrollHeight + 8}px`;
      container.style.opacity = "1";
      container.style.transform = "translateY(0)";
    });
    window.setTimeout(() => {
      if (!container.classList.contains("is-collapsed")) {
        container.style.maxHeight = "none";
      }
    }, 290);
    return;
  }

  const startHeight = container.scrollHeight;
  container.style.maxHeight = `${startHeight}px`;
  requestAnimationFrame(() => {
    container.classList.add("is-collapsed");
    container.style.maxHeight = "0px";
    container.style.opacity = "0";
    container.style.transform = "translateY(-6px)";
  });
  container.addEventListener("transitionend", () => {
    if (container.classList.contains("is-collapsed")) {
      container.style.display = "none";
    }
  }, { once: true });
}

function applyModeOptions(mode) {
  const cfg = optionsByMode?.[mode] || {};
  const styles = cfg.styles || [];
  const layouts = cfg.layouts || [];
  const palettes = cfg.palettes || [];
  const tones = cfg.tones || [];
  const langs = cfg.langs || [];
  const types = cfg.types || [];
  const presets = cfg.presets || [];
  const densities = cfg.densities || [];
  const coverTypes = cfg.cover_types || [];
  const renderings = cfg.renderings || [];
  const textLevels = cfg.text_levels || [];
  const moods = cfg.moods || [];
  const fonts = cfg.fonts || [];
  const supportsPalette = Boolean(cfg.supports_palette);
  const supportsRef = Boolean(cfg.supports_ref);

  const styleWrap = document.getElementById("style-wrap");
  const styleSelect = document.getElementById("style-select");
  const layoutWrap = document.getElementById("layout-wrap");
  const layoutSelect = document.getElementById("layout-select");
  const paletteWrap = document.getElementById("palette-wrap");
  const paletteSelect = document.getElementById("palette-select");
  const toneWrap = document.getElementById("tone-wrap");
  const toneSelect = document.getElementById("tone-select");
  const langWrap = document.getElementById("lang-wrap");
  const langSelect = document.getElementById("lang-select");
  const coverTypeWrap = document.getElementById("cover-type-wrap");
  const coverTypeSelect = document.getElementById("cover-type-select");
  const renderingWrap = document.getElementById("rendering-wrap");
  const renderingSelect = document.getElementById("rendering-select");
  const textLevelWrap = document.getElementById("text-level-wrap");
  const textLevelSelect = document.getElementById("text-level-select");
  const moodWrap = document.getElementById("mood-wrap");
  const moodSelect = document.getElementById("mood-select");
  const fontWrap = document.getElementById("font-wrap");
  const fontSelect = document.getElementById("font-select");
  const typeWrap = document.getElementById("type-wrap");
  const typeSelect = document.getElementById("type-select");
  const presetWrap = document.getElementById("preset-wrap");
  const presetSelect = document.getElementById("preset-select");
  const densityWrap = document.getElementById("density-wrap");
  const densitySelect = document.getElementById("density-select");
  const refWrap = document.getElementById("ref-wrap");
  const styleLabel = document.getElementById("style-label");

  toggleBlock(styleWrap, styles.length > 0);
  setSelectOptions(styleSelect, styles, styleSelect?.value || "", mode, "style");
  if (styleLabel) {
    styleLabel.textContent = mode === "comic"
      ? (LANG === "zh" ? "画风（art，可选）" : "Art (--art, optional)")
      : (LANG === "zh" ? "风格（可选）" : "Style (optional)");
  }

  toggleBlock(layoutWrap, layouts.length > 0);
  setSelectOptions(layoutSelect, layouts, layoutSelect?.value || "", mode, "layout");

  const showPalette = supportsPalette && palettes.length > 0;
  toggleBlock(paletteWrap, showPalette);
  setSelectOptions(paletteSelect, palettes, paletteSelect?.value || "", mode, "palette");
  if (!showPalette && paletteSelect) paletteSelect.value = "";

  toggleBlock(toneWrap, tones.length > 0);
  setSelectOptions(toneSelect, tones, toneSelect?.value || "", mode, "tone");
  if (!tones.length && toneSelect) toneSelect.value = "";

  toggleBlock(langWrap, langs.length > 0);
  setSelectOptions(langSelect, langs, langSelect?.value || "", mode, "lang");
  if (!langs.length && langSelect) langSelect.value = "";

  toggleBlock(coverTypeWrap, coverTypes.length > 0);
  setSelectOptions(coverTypeSelect, coverTypes, coverTypeSelect?.value || "", mode, "cover_type");
  if (!coverTypes.length && coverTypeSelect) coverTypeSelect.value = "";

  toggleBlock(renderingWrap, renderings.length > 0);
  setSelectOptions(renderingSelect, renderings, renderingSelect?.value || "", mode, "rendering");
  if (!renderings.length && renderingSelect) renderingSelect.value = "";

  toggleBlock(textLevelWrap, textLevels.length > 0);
  setSelectOptions(textLevelSelect, textLevels, textLevelSelect?.value || "", mode, "text_level");
  if (!textLevels.length && textLevelSelect) textLevelSelect.value = "";

  toggleBlock(moodWrap, moods.length > 0);
  setSelectOptions(moodSelect, moods, moodSelect?.value || "", mode, "mood");
  if (!moods.length && moodSelect) moodSelect.value = "";

  toggleBlock(fontWrap, fonts.length > 0);
  setSelectOptions(fontSelect, fonts, fontSelect?.value || "", mode, "font");
  if (!fonts.length && fontSelect) fontSelect.value = "";

  toggleBlock(typeWrap, types.length > 0);
  setSelectOptions(typeSelect, types, typeSelect?.value || "", mode, "type");
  if (!types.length && typeSelect) typeSelect.value = "";

  toggleBlock(presetWrap, presets.length > 0);
  setSelectOptions(presetSelect, presets, presetSelect?.value || "", mode, "preset");
  if (!presets.length && presetSelect) presetSelect.value = "";

  toggleBlock(densityWrap, densities.length > 0);
  setSelectOptions(densitySelect, densities, densitySelect?.value || "", mode, "density");
  if (!densities.length && densitySelect) densitySelect.value = "";

  toggleBlock(refWrap, supportsRef);
  if (!supportsRef) {
    activeRefImages = [];
    activeRefPreviewRows = [];
    renderRefPreviewGrid();
    const refStatus = document.getElementById("ref-upload-status");
    if (refStatus) refStatus.textContent = emptyRefUploadLabel;
  }
}

async function loadOptions() {
  const res = await fetch("/api/options");
  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data));
  }
  optionsByMode = data.modes || {};
}

function switchSource(source) {
  activeSource = source;
  const textPane = document.getElementById("pane-text");
  const uploadPane = document.getElementById("pane-upload");
  const tabs = Array.from(document.querySelectorAll(".tab-btn"));
  const textInput = document.getElementById("content-text");

  tabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.source === source);
  });
  toggleBlock(textPane, source === "text");
  toggleBlock(uploadPane, source === "upload");
  if (textInput) {
    textInput.disabled = source !== "text";
  }
}

function pathToRunsUrl(path) {
  if (!path) return null;
  const normalized = String(path).replace(/\\/g, "/");
  if (normalized.startsWith("/runs/")) return normalized;
  const idx = normalized.indexOf("/runs/");
  if (idx >= 0) return normalized.slice(idx);
  return null;
}

function resolveImageUrls(data) {
  const urls = Array.isArray(data?.image_urls) ? data.image_urls.filter(Boolean) : [];
  if (urls.length) return urls;
  const fallback = Array.isArray(data?.images) ? data.images : [];
  return fallback.map((p) => pathToRunsUrl(p)).filter(Boolean);
}

function renderRefPreviewGrid() {
  const grid = document.getElementById("ref-preview-grid");
  if (!grid) return;
  if (!activeRefPreviewRows.length) {
    grid.classList.add("hidden");
    grid.innerHTML = "";
    return;
  }
  grid.classList.remove("hidden");
  grid.innerHTML = activeRefPreviewRows
    .map((row, idx) => {
      const safeUrl = String(row.url || "");
      const safeName = String(row.name || `${LANG === "zh" ? "参考图" : "Ref"} ${idx + 1}`);
      return `
      <figure class="ref-preview-item">
        <img src="${safeUrl}" alt="${safeName}" loading="lazy">
        <figcaption>${safeName}</figcaption>
      </figure>`;
    })
    .join("");
}

function syncResultPager() {
  const pager = document.getElementById("result-pager");
  const prev = document.getElementById("result-prev");
  const next = document.getElementById("result-next");
  const text = document.getElementById("result-page-text");
  if (!pager || !prev || !next || !text) return;

  const total = resultImageUrls.length;
  const pages = Math.max(1, Math.ceil(total / RESULT_PAGE_SIZE));
  if (resultPage < 1) resultPage = 1;
  if (resultPage > pages) resultPage = pages;

  if (total <= RESULT_PAGE_SIZE) {
    pager.classList.add("hidden");
  } else {
    pager.classList.remove("hidden");
  }

  prev.disabled = resultPage <= 1;
  next.disabled = resultPage >= pages;
  text.textContent = `${resultPage} / ${pages}`;
}

function renderPagedResultGallery(gallery) {
  if (!gallery) return;
  const total = resultImageUrls.length;
  const pages = Math.max(1, Math.ceil(total / RESULT_PAGE_SIZE));
  if (resultPage > pages) resultPage = pages;
  const start = (resultPage - 1) * RESULT_PAGE_SIZE;
  const pageUrls = resultImageUrls.slice(start, start + RESULT_PAGE_SIZE);
  const slots = [...pageUrls];
  while (slots.length < RESULT_PAGE_SIZE) slots.push("");

  gallery.innerHTML = slots
    .map((url, idx) => {
      if (!url) {
        return `<div class="result-slot-empty" aria-hidden="true"></div>`;
      }
      const globalIndex = start + idx + 1;
      const label = LANG === "zh" ? `图片 ${globalIndex}` : `Image ${globalIndex}`;
      return `
      <figure class="result-card">
        <div class="result-image-wrap">
          <button type="button" class="img-preview-btn" data-src="${url}" data-label="${label}">
            <img src="${url}" loading="lazy" alt="${label}">
          </button>
          <a class="img-download-corner" href="${url}" download="image-${globalIndex}.png" title="${LANG === "zh" ? "下载" : "Download"}" aria-label="${LANG === "zh" ? "下载" : "Download"}">
            ↓
          </a>
        </div>
      </figure>
    `;
    })
    .join("");

  applyStagger(gallery, ".result-card");
  syncResultPager();
}

function isDryRunResult(data) {
  if (data?.dry_run === true) return true;
  const rows = Array.isArray(data?.render_results) ? data.render_results : [];
  return rows.length > 0 && rows.every((row) => Number(row?.code) === -1);
}

function runIdFromData(data) {
  if (typeof data?.run_id === "string" && data.run_id) return data.run_id;
  const runDir = String(data?.run_dir || "");
  if (!runDir) return "";
  return runDir.split("/").filter(Boolean).slice(-1)[0] || "";
}

function renderResult(data) {
  const summary = document.getElementById("result-summary");
  const gallery = document.getElementById("result-gallery");
  const debugBox = document.getElementById("result-box");
  const pager = document.getElementById("result-pager");
  if (!summary || !gallery || !debugBox) return;

  const urls = resolveImageUrls(data);
  const dryRun = isDryRunResult(data);
  summary.textContent = "";
  summary.classList.add("hidden");
  if (pager) pager.classList.add("hidden");
  resultImageUrls = [];
  resultPage = 1;

  if (dryRun) {
    gallery.classList.add("result-gallery-empty");
    gallery.innerHTML = emptyResultMarkup(dryRunHint);
    debugBox.textContent = JSON.stringify(data, null, 2);
    return;
  }

  if (!urls.length) {
    gallery.classList.add("result-gallery-empty");
    gallery.innerHTML = emptyResultMarkup(data?.status === "cancelled" ? cancelledHint : noImageHint);
    debugBox.textContent = JSON.stringify(data, null, 2);
    return;
  }

  gallery.classList.remove("result-gallery-empty");
  resultImageUrls = urls.slice();
  resultPage = 1;
  renderPagedResultGallery(gallery);
  debugBox.textContent = JSON.stringify(data, null, 2);
}

function formToPayload(form) {
  const fd = new FormData(form);
  const hiddenContentFile = document.getElementById("content-file-hidden");
  const mode = textFromForm(fd, "mode");
  const textContent = textFromForm(fd, "content");
  const uploadedPath = (hiddenContentFile?.value || "").trim();

  if (activeSource === "upload" && !uploadedPath) {
    throw new Error(sourceRequiredHint);
  }

  return {
    mode,
    topic: textFromForm(fd, "topic") || null,
    content: activeSource === "text" ? textContent : "",
    content_file: activeSource === "upload" ? uploadedPath : null,
    type: textFromForm(fd, "type") || null,
    preset: textFromForm(fd, "preset") || null,
    density: textFromForm(fd, "density") || null,
    style: textFromForm(fd, "style") || null,
    layout: textFromForm(fd, "layout") || null,
    palette: textFromForm(fd, "palette") || null,
    tone: textFromForm(fd, "tone") || null,
    lang: textFromForm(fd, "lang") || null,
    cover_type: textFromForm(fd, "cover_type") || null,
    rendering: textFromForm(fd, "rendering") || null,
    text_level: textFromForm(fd, "text_level") || null,
    mood: textFromForm(fd, "mood") || null,
    font: textFromForm(fd, "font") || null,
    ref_images: activeRefImages.slice(),
    image_count: Number(textFromForm(fd, "image_count") || "4"),
    aspect_ratio: textFromForm(fd, "aspect_ratio") || "3:4",
    quality: textFromForm(fd, "quality") || "2k",
    provider: null,
    model: null,
    image_api_dialect: null,
    dry_run: false,
    generate: true,
    anchor_chain: checked(form, "anchor_chain"),
    fail_fast: false,
    skip_analysis_llm: checked(form, "skip_analysis_llm"),
    skip_outline_llm: checked(form, "skip_outline_llm"),
    output_root: "runs",
    thread_id: "copy2image-web"
  };
}

async function postRun(payload, signal) {
  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal,
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data));
  }
  return data;
}

async function stopCurrentRun() {
  const res = await fetch("/api/run/stop", { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data));
  }
  return data;
}

async function switchLanguage(lang) {
  const res = await fetch("/api/lang", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lang })
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data));
  }
  return data;
}

async function uploadDocument(file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", body: fd });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data));
  }
  return data;
}

async function uploadReferenceImages(files) {
  const fd = new FormData();
  Array.from(files || []).forEach((file) => fd.append("files", file));
  const res = await fetch("/api/upload_ref", { method: "POST", body: fd });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data));
  }
  return data;
}

async function loadRecentRuns(limit = 20, autoLoadFirst = false) {
  const list = document.getElementById("recent-list");
  if (!list) return;

  const res = await fetch(`/api/runs?limit=${limit}`);
  const data = await res.json();
  const items = Array.isArray(data?.items) ? data.items : [];

  if (!items.length) {
    list.innerHTML = `<div class="run-meta">${LANG === "zh" ? "暂无历史任务" : "No runs"}</div>`;
    return;
  }

  list.innerHTML = items
    .map((item) => {
      const title = item.title || item.run_id;
      return `
      <article class="run-item" data-mode="${item.mode}" data-run="${item.run_id}">
        <div><strong>${modeLabel(item.mode)}</strong> / ${title}</div>
      </article>`;
    })
    .join("");

  applyStagger(list, ".run-item");

  if (autoLoadFirst && !hasLoadedInitialHistory) {
    hasLoadedInitialHistory = true;
    const first = items[0];
    if (first?.mode && first?.run_id) {
      await loadRunDetail(first.mode, first.run_id);
    }
  }
}

async function loadRunDetail(mode, runId) {
  const res = await fetch(`/api/runs/${mode}/${runId}`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data));
  }
  renderResult(data);
}

function applyTheme(theme, animate = false) {
  const body = document.body;
  const root = document.documentElement;
  const isDark = theme === "dark";
  const canAnimate = animate && !prefersReducedMotion();

  if (canAnimate) body.classList.add("theme-switching");
  root.setAttribute("data-theme", isDark ? "dark" : "light");

  const btn = document.getElementById("theme-toggle");
  if (btn) {
    btn.innerHTML = themeIconSvg(isDark);
    btn.setAttribute("aria-label", LANG === "zh" ? (isDark ? "切换到浅色" : "切换到深色") : (isDark ? "Switch to light" : "Switch to dark"));
    btn.title = btn.getAttribute("aria-label") || "";
  }

  localStorage.setItem(THEME_KEY, isDark ? "dark" : "light");
  if (canAnimate) {
    window.setTimeout(() => body.classList.remove("theme-switching"), 280);
  }
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = saved === "dark" || saved === "light" ? saved : (prefersDark ? "dark" : "light");
  applyTheme(theme, false);
}

function wireModeSelect() {
  const modeSelect = document.getElementById("mode-select");
  if (!modeSelect) return;
  modeSelect.addEventListener("change", () => applyModeOptions(modeSelect.value));
}

function wireSourceTabs() {
  const tabs = Array.from(document.querySelectorAll(".tab-btn"));
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => switchSource(tab.dataset.source || "text"));
  });
  switchSource("text");
}

function wireUpload() {
  const uploadInput = document.getElementById("upload-file");
  const uploadStatus = document.getElementById("upload-status");
  const hiddenContentFile = document.getElementById("content-file-hidden");
  if (!uploadInput || !uploadStatus || !hiddenContentFile) return;

  uploadInput.addEventListener("change", async () => {
    const file = uploadInput.files?.[0];
    if (!file) {
      uploadStatus.textContent = emptyUploadLabel;
      hiddenContentFile.value = "";
      return;
    }
    uploadInput.disabled = true;
    uploadStatus.textContent = uploadingLabel;
    try {
      const data = await uploadDocument(file);
      hiddenContentFile.value = data.content_file || "";
      uploadStatus.textContent = `${file.name} ${LANG === "zh" ? "已上传并使用" : "uploaded and active"}`;
    } catch (err) {
      uploadStatus.textContent = `${uploadFailedLabel}: ${String(err)}`;
      hiddenContentFile.value = "";
    } finally {
      uploadInput.disabled = false;
    }
  });
}

function wireRefUpload() {
  const uploadInput = document.getElementById("ref-file");
  const uploadStatus = document.getElementById("ref-upload-status");
  if (!uploadInput || !uploadStatus) return;

  uploadInput.addEventListener("change", async () => {
    const files = uploadInput.files;
    if (!files || files.length === 0) {
      uploadStatus.textContent = emptyRefUploadLabel;
      activeRefImages = [];
      activeRefPreviewRows = [];
      renderRefPreviewGrid();
      return;
    }
    // Immediate local preview before upload completes.
    activeRefPreviewRows = Array.from(files).map((f) => ({
      name: f.name,
      url: URL.createObjectURL(f),
    }));
    renderRefPreviewGrid();
    uploadInput.disabled = true;
    uploadStatus.textContent = refUploadingLabel;
    try {
      const data = await uploadReferenceImages(files);
      const refs = Array.isArray(data?.ref_images) ? data.ref_images.filter(Boolean) : [];
      const items = Array.isArray(data?.items) ? data.items : [];
      activeRefImages = refs;
      activeRefPreviewRows = items
        .map((it, idx) => ({
          name: String(it?.original_file || `${LANG === "zh" ? "参考图" : "Ref"} ${idx + 1}`),
          url: pathToRunsUrl(String(it?.ref_file || "")) || "",
        }))
        .filter((row) => row.url);
      renderRefPreviewGrid();
      uploadStatus.textContent = refs.length
        ? `${refs.length} ${LANG === "zh" ? "张参考图已上传并使用" : "reference image(s) uploaded and active"}`
        : emptyRefUploadLabel;
    } catch (err) {
      uploadStatus.textContent = `${refUploadFailedLabel}: ${String(err)}`;
      activeRefImages = [];
      activeRefPreviewRows = [];
      renderRefPreviewGrid();
    } finally {
      uploadInput.disabled = false;
    }
  });
}

function wireRunForm() {
  const form = document.getElementById("run-form");
  const runBtn = document.getElementById("run-btn");
  const stopBtn = document.getElementById("stop-btn");
  if (!form || !runBtn || !stopBtn) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const oldStop = stopBtn.textContent;
    const controller = new AbortController();
    activeRunController = controller;
    runBtn.disabled = true;
    setButtonLoading(runBtn, true);
    stopBtn.disabled = false;

    try {
      const payload = formToPayload(form);
      const data = await postRun(payload, controller.signal);
      renderResult(data);
      await loadRecentRuns(20, false);
    } catch (err) {
      if (err?.name === "AbortError") {
        renderResult({ status: "cancelled", message: cancelledHint, images: [] });
      } else {
        renderResult({ status: "error", message: String(err), images: [] });
      }
    } finally {
      activeRunController = null;
      setButtonLoading(runBtn, false);
      runBtn.disabled = false;
      stopBtn.disabled = true;
      stopBtn.textContent = oldStop || (LANG === "zh" ? "停止当前任务" : "Stop Current Task");
    }
  });

  stopBtn.addEventListener("click", async () => {
    if (stopBtn.disabled) return;
    const oldStop = stopBtn.textContent;
    stopBtn.disabled = true;
    stopBtn.textContent = stoppingLabel;
    try {
      await stopCurrentRun();
      if (activeRunController) activeRunController.abort();
    } catch (err) {
      renderResult({ status: "error", message: String(err), images: [] });
    } finally {
      stopBtn.textContent = oldStop;
    }
  });
}

function wireRunItems() {
  const list = document.getElementById("recent-list");
  if (!list) return;
  list.addEventListener("click", async (e) => {
    const target = e.target.closest(".run-item");
    if (!target) return;
    const mode = target.getAttribute("data-mode");
    const run = target.getAttribute("data-run");
    if (!mode || !run) return;
    try {
      await loadRunDetail(mode, run);
    } catch (err) {
      renderResult({ status: "error", message: String(err), images: [] });
    }
  });
}

function wireRefresh() {
  const btn = document.getElementById("refresh-btn");
  if (!btn) return;
  btn.addEventListener("click", () => loadRecentRuns(20, false));
}

function wireResultPager() {
  const prev = document.getElementById("result-prev");
  const next = document.getElementById("result-next");
  const gallery = document.getElementById("result-gallery");
  if (!prev || !next || !gallery) return;

  prev.addEventListener("click", () => {
    if (resultPage <= 1) return;
    resultPage -= 1;
    renderPagedResultGallery(gallery);
  });
  next.addEventListener("click", () => {
    const pages = Math.max(1, Math.ceil(resultImageUrls.length / RESULT_PAGE_SIZE));
    if (resultPage >= pages) return;
    resultPage += 1;
    renderPagedResultGallery(gallery);
  });
}

function wireImagePreview() {
  const gallery = document.getElementById("result-gallery");
  const modal = document.getElementById("image-modal");
  const modalImg = document.getElementById("image-modal-img");
  const closeBtn = document.getElementById("image-modal-close");
  if (!gallery || !modal || !modalImg || !closeBtn) return;

  const closeModal = () => {
    modal.classList.add("hidden");
    modalImg.removeAttribute("src");
  };

  gallery.addEventListener("click", (e) => {
    const trigger = e.target.closest(".img-preview-btn");
    if (!trigger) return;
    const src = trigger.getAttribute("data-src");
    const label = trigger.getAttribute("data-label") || "preview";
    if (!src) return;
    modalImg.setAttribute("src", src);
    modalImg.setAttribute("alt", label);
    modal.classList.remove("hidden");
  });

  closeBtn.addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.classList.contains("hidden")) closeModal();
  });
}

function wireLanguageToggle() {
  const btn = document.getElementById("lang-toggle");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    const target = window.COPY2IMAGE_ALT_LANG || (LANG === "zh" ? "en" : "zh");
    const old = btn.textContent;
    btn.disabled = true;
    document.body.classList.add("page-switching");
    try {
      await switchLanguage(target);
      window.location.reload();
    } catch (err) {
      btn.disabled = false;
      btn.textContent = old;
      document.body.classList.remove("page-switching");
      renderResult({ status: "error", message: String(err), images: [] });
    }
  });
}

function wireThemeToggle() {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    applyTheme(current === "dark" ? "light" : "dark", true);
  });
}

async function init() {
  initTheme();
  await loadOptions();

  wireThemeToggle();
  wireLanguageToggle();
  wireModeSelect();
  wireSourceTabs();
  wireUpload();
  wireRefUpload();
  wireRunForm();
  wireRunItems();
  wireRefresh();
  wireResultPager();
  wireImagePreview();

  const modeSelect = document.getElementById("mode-select");
  if (modeSelect) applyModeOptions(modeSelect.value);

  await loadRecentRuns(20, true);
}

init().catch((err) => {
  renderResult({ status: "error", message: String(err), images: [] });
});

