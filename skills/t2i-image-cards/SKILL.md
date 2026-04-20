---
name: t2i-image-cards
description: Generates infographic image card series with 12 visual styles, 8 layouts, and 3 color palettes. Breaks content into 1-10 cartoon-style image cards optimized for social media engagement. Use when user mentions "灏忕孩涔﹀浘鐗?, "灏忕孩涔︾鑽?, "灏忕豢涔?, "寰俊鍥炬枃", "寰俊璐村浘", "image cards", "鍥剧墖鍗＄墖", or wants social media infographic series.
version: 1.56.1
metadata:
  openclaw:
    homepage: https://github.com/JimLiu/copy2image-workflow#t2i-image-cards
---

# Image Card Series Generator

Break down complex content into eye-catching image card series with multiple style options.

## User Input Tools

When this skill prompts the user, follow this tool-selection rule (priority order):

1. **Prefer built-in user-input tools** exposed by the current agent runtime 鈥?e.g., `AskUserQuestion`, `request_user_input`, `clarify`, `ask_user`, or any equivalent.
2. **Fallback**: if no such tool exists, emit a numbered plain-text message and ask the user to reply with the chosen number/answer for each question.
3. **Batching**: if the tool supports multiple questions per call, combine all applicable questions into a single call; if only single-question, ask them one at a time in priority order.

Concrete `AskUserQuestion` references below are examples 鈥?substitute the local equivalent in other runtimes.

## Image Generation Tools

When this skill needs to render an image:

- **Use whatever image-generation tool or skill is available** in the current runtime 鈥?e.g., Codex `imagegen`, Hermes `image_generate`, `t2i-imagine`, or any equivalent the user has installed.
- **If multiple are available**, ask the user **once** at the start which to use (batch with any other initial questions).
- **If none are available**, tell the user and ask how to proceed.

**Prompt file requirement (hard)**: write each image's full, final prompt to a standalone file under `prompts/` (naming: `NN-{type}-[slug].md`) BEFORE invoking any backend. The file is the reproducibility record and lets you switch backends without regenerating prompts.

## Language

Respond in the user's language across questions, progress, errors, and completion summary. Keep technical tokens (style names, file paths, code) in English.

## Options

| Option | Description |
|--------|-------------|
| `--style <name>` | Visual style (see Styles below) |
| `--layout <name>` | Information layout (see Layouts below) |
| `--palette <name>` | Color override: macaron / warm / neon |
| `--preset <name>` | Style + layout + optional palette shorthand (see Presets below; per-preset prompt fragments in `references/style-presets.md`) |
| `--ref <files...>` | Reference images applied to image 1 as the series anchor |
| `--yes` | Non-interactive: skip all confirmations, use EXTEND.md or built-in defaults, auto-confirm recommended plan (Path A) |

## Dimensions

Three independent knobs combine freely:

| Dimension | Controls | Options |
|-----------|----------|---------|
| **Style** | Visual aesthetics (lines, decorations, rendering) | 12 styles (see Styles below) |
| **Layout** | Information structure (density, arrangement) | 8 layouts (see Layouts below) |
| **Palette** (optional) | Color override, replaces the style's default colors | macaron / warm / neon (see Palettes below) |

Example: `--style notion --layout dense` makes an intellectual knowledge card; add `--palette macaron` to soften the colors without changing notion's rendering rules. A `--preset` is a shorthand for style + layout (+ optional palette).

**Palette behavior**: no `--palette` 鈫?style's built-in colors; `--palette <name>` 鈫?overrides colors only, rendering rules unchanged. Some styles declare a `default_palette` (e.g., sketch-notes defaults to macaron).

## Styles (12)

| Style | Description |
|-------|-------------|
| `cute` (Default) | Sweet, adorable, girly aesthetic |
| `fresh` | Clean, refreshing, natural |
| `warm` | Cozy, friendly, approachable |
| `bold` | High impact, attention-grabbing |
| `minimal` | Ultra-clean, sophisticated |
| `retro` | Vintage, nostalgic, trendy |
| `pop` | Vibrant, energetic, eye-catching |
| `notion` | Minimalist hand-drawn line art, intellectual |
| `chalkboard` | Colorful chalk on black board, educational |
| `study-notes` | Realistic handwritten photo style, blue pen + red annotations + yellow highlighter |
| `screen-print` | Bold poster art, halftone textures, limited colors, symbolic storytelling |
| `sketch-notes` | Hand-drawn educational infographic, macaron pastels on warm cream, wobble lines |

Per-style specifications: `references/presets/<style>.md`.

## Layouts (8)

| Layout | Description |
|--------|-------------|
| `sparse` (Default) | 1-2 points, maximum impact |
| `balanced` | 3-4 points, standard |
| `dense` | 5-8 points, knowledge-card style |
| `list` | Enumeration / ranking (4-7 items) |
| `comparison` | Side-by-side contrast |
| `flow` | Process / timeline (3-6 steps) |
| `mindmap` | Center-radial (4-8 branches) |
| `quadrant` | Four-quadrant / circular sections |

Layout specs: `references/elements/canvas.md`.

## Palettes (optional override)

Replaces the style's colors while keeping rendering rules (line treatment, textures) intact.

| Palette | Background | Zone Colors | Accent | Feel |
|---------|------------|-------------|--------|------|
| `macaron` | Warm cream #F5F0E8 | Blue #A8D8EA, Lavender #D5C6E0, Mint #B5E5CF, Peach #F8D5C4 | Coral #E8655A | Soft, educational |
| `warm` | Soft peach #FFECD2 | Orange #ED8936, Terracotta #C05621, Golden #F6AD55, Rose #D4A09A | Sienna #A0522D | Earth tones, cozy |
| `neon` | Dark purple #1A1025 | Cyan #00F5FF, Magenta #FF00FF, Green #39FF14, Pink #FF6EC7 | Yellow #FFFF00 | High-energy, futuristic |

Palette specs: `references/palettes/<palette>.md`.

## Presets (style + layout shortcuts)

Quick-start combos, grouped by scenario. Use `--preset <name>` or recommend during Step 2.

**Knowledge & Learning**:

| Preset | Style | Layout | Best For |
|--------|-------|--------|----------|
| `knowledge-card` | notion | dense | 骞茶揣鐭ヨ瘑鍗°€佹蹇电鏅?|
| `checklist` | notion | list | 娓呭崟銆佹帓琛屾 |
| `concept-map` | notion | mindmap | 姒傚康鍥俱€佺煡璇嗚剦缁?|
| `swot` | notion | quadrant | SWOT 鍒嗘瀽銆佸洓璞￠檺 |
| `tutorial` | chalkboard | flow | 鏁欑▼姝ラ銆佹搷浣滄祦绋?|
| `classroom` | chalkboard | balanced | 璇惧爞绗旇銆佺煡璇嗚瑙?|
| `study-guide` | study-notes | dense | 瀛︿範绗旇銆佽€冭瘯閲嶇偣 |
| `hand-drawn-edu` | sketch-notes | flow | 鎵嬬粯鏁欑▼銆佹祦绋嬪浘瑙?|
| `sketch-card` | sketch-notes | dense | 鎵嬬粯鐭ヨ瘑鍗?|
| `sketch-summary` | sketch-notes | balanced | 鎵嬬粯鎬荤粨銆佸浘鏂囩瑪璁?|

**Lifestyle & Sharing**:

| Preset | Style | Layout | Best For |
|--------|-------|--------|----------|
| `cute-share` | cute | balanced | 灏戝コ椋庡垎浜€佹棩甯哥鑽?|
| `girly` | cute | sparse | 鐢滅編灏侀潰銆佹皼鍥存劅 |
| `cozy-story` | warm | balanced | 鐢熸椿鏁呬簨銆佹儏鎰熷垎浜?|
| `product-review` | fresh | comparison | 浜у搧瀵规瘮銆佹祴璇?|
| `nature-flow` | fresh | flow | 鍋ュ悍娴佺▼銆佽嚜鐒朵富棰?|

**Impact & Opinion**:

| Preset | Style | Layout | Best For |
|--------|-------|--------|----------|
| `warning` | bold | list | 閬垮潙鎸囧崡銆侀噸瑕佹彁閱?|
| `versus` | bold | comparison | 姝ｅ弽瀵规瘮 |
| `clean-quote` | minimal | sparse | 閲戝彞銆佹瀬绠€灏侀潰 |
| `pro-summary` | minimal | balanced | 涓撲笟鎬荤粨銆佸晢鍔″唴瀹?|

**Trend & Entertainment**:

| Preset | Style | Layout | Best For |
|--------|-------|--------|----------|
| `retro-ranking` | retro | list | 澶嶅彜鎺掕銆佺粡鍏哥洏鐐?|
| `throwback` | retro | balanced | 鎬€鏃у垎浜?|
| `pop-facts` | pop | list | 瓒ｅ懗鍐风煡璇?|
| `hype` | pop | sparse | 鐐歌灏侀潰銆佹儕鍙瑰垎浜?|

**Poster & Editorial**:

| Preset | Style | Layout | Best For |
|--------|-------|--------|----------|
| `poster` | screen-print | sparse | 娴锋姤椋庡皝闈€佸奖璇勪功璇?|
| `editorial` | screen-print | balanced | 瑙傜偣鏂囩珷銆佹枃鍖栬瘎璁?|
| `cinematic` | screen-print | comparison | 鐢靛奖瀵规瘮銆佹垙鍓у紶鍔?|

Full prompt-fragment definitions: `references/style-presets.md`.

## Auto-Selection

Match content signals to the best combo. First row whose keywords appear wins; fall back to `cute-share` if nothing matches.

| Signals in source | Style | Layout | Recommended preset |
|-------------------|-------|--------|--------------------|
| beauty, fashion, cute, girl, pink | `cute` | sparse/balanced | `cute-share`, `girly` |
| health, nature, fresh, organic | `fresh` | balanced/flow | `product-review`, `nature-flow` |
| life, story, emotion, warm | `warm` | balanced | `cozy-story` |
| warning, important, must, critical | `bold` | list/comparison | `warning`, `versus` |
| professional, business, elegant | `minimal` | sparse/balanced | `clean-quote`, `pro-summary` |
| classic, vintage, traditional | `retro` | balanced | `throwback`, `retro-ranking` |
| fun, exciting, wow, amazing | `pop` | sparse/list | `hype`, `pop-facts` |
| knowledge, concept, productivity, SaaS | `notion` | dense/list | `knowledge-card`, `checklist` |
| education, tutorial, learning, classroom | `chalkboard` | balanced/dense | `tutorial`, `classroom` |
| notes, handwritten, study guide, realistic | `study-notes` | dense/list/mindmap | `study-guide` |
| movie, poster, opinion, editorial, cinematic | `screen-print` | sparse/comparison | `poster`, `editorial`, `cinematic` |
| hand-drawn, infographic, workflow, 鎵嬬粯, 鍥捐В | `sketch-notes` | flow/balanced/dense | `hand-drawn-edu`, `sketch-card`, `sketch-summary` |

## Style 脳 Layout Matrix

Compatibility scores (鉁撯湏 highly recommended, 鉁?works well, 鉁?avoid). Use when the user picks a non-default combo and you want to flag a poor match.

|              | sparse | balanced | dense | list | comparison | flow | mindmap | quadrant |
|--------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| cute         | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁撯湏 | 鉁? | 鉁? | 鉁? | 鉁? |
| fresh        | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁? | 鉁? | 鉁撯湏 | 鉁? | 鉁? |
| warm         | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁? | 鉁撯湏 | 鉁? | 鉁? | 鉁? |
| bold         | 鉁撯湏 | 鉁? | 鉁? | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁? | 鉁撯湏 |
| minimal      | 鉁撯湏 | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁? | 鉁? | 鉁? | 鉁? |
| retro        | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁撯湏 | 鉁? | 鉁? | 鉁? | 鉁? |
| pop          | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁? | 鉁? |
| notion       | 鉁撯湏 | 鉁撯湏 | 鉁撯湏 | 鉁撯湏 | 鉁撯湏 | 鉁撯湏 | 鉁撯湏 | 鉁撯湏 |
| chalkboard   | 鉁撯湏 | 鉁撯湏 | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁撯湏 | 鉁撯湏 | 鉁? |
| study-notes  | 鉁? | 鉁? | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁? | 鉁撯湏 | 鉁? |
| screen-print | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁? | 鉁撯湏 | 鉁? | 鉁? | 鉁撯湏 |
| sketch-notes | 鉁? | 鉁撯湏 | 鉁撯湏 | 鉁撯湏 | 鉁? | 鉁撯湏 | 鉁撯湏 | 鉁? |

## Outline Strategies

Three differentiated approaches 鈥?each produces a structurally different outline. The workflow recommends one; Path C generates all three and lets the user choose.

| Strategy | Concept | Best for | Structure |
|----------|---------|----------|-----------|
| **A 鈥?Story-Driven** | Personal experience as the thread, emotional resonance first | Reviews, personal shares, transformation | Hook 鈫?Problem 鈫?Discovery 鈫?Experience 鈫?Conclusion |
| **B 鈥?Information-Dense** | Value-first, efficient information delivery | Tutorials, comparisons, checklists | Core conclusion 鈫?Info card 鈫?Pros/Cons 鈫?Recommendation |
| **C 鈥?Visual-First** | Visual impact as core, minimal text | High-aesthetic products, lifestyle, mood content | Hero image 鈫?Detail shots 鈫?Lifestyle scene 鈫?CTA |

## Reference Images

User-supplied refs are **separate from** the internal "image-1 as anchor" chain (Step 3) 鈥?they layer on top of it.

**Intake**: via `--ref <files...>` or paths pasted in conversation.
- File path 鈫?copy to `refs/NN-ref-{slug}.{ext}`
- Pasted with no path 鈫?ask for the path, or extract style traits as a text fallback

**Usage modes** (per reference):

| Usage | Effect |
|-------|--------|
| `direct` | Pass the file to the backend (typically on image 1 only, so the anchor propagates through the chain) |
| `style` | Extract style traits and append to every card's prompt body |
| `palette` | Extract hex colors and append to every card's prompt body |

Record refs in each affected card's prompt frontmatter:

```yaml
references:
  - ref_id: 01
    filename: 01-ref-brand.png
    usage: direct
```

At generation time: verify files exist. Image 1 with `usage: direct` + backend that accepts refs 鈫?pass via the backend's ref parameter (becomes the chain anchor). Images 2+ keep using image-1 as `--ref` per Step 3 鈥?do NOT re-stack user refs on top (avoids conflicting signals). For `style`/`palette`, embed extracted traits in every prompt.

## File Layout

```
image-cards/{topic-slug}/
鈹溾攢鈹€ source-{slug}.{ext}
鈹溾攢鈹€ analysis.md
鈹溾攢鈹€ outline-strategy-{a,b,c}.md    # Path C only
鈹溾攢鈹€ outline.md
鈹溾攢鈹€ prompts/NN-{type}-{slug}.md
鈹溾攢鈹€ NN-{type}-{slug}.png
鈹斺攢鈹€ refs/                          # only if --ref used
```

**Slug**: 2-4 words, kebab-case. "AI 宸ュ叿鎺ㄨ崘" 鈫?`ai-tools-recommend`. On collision, append `-YYYYMMDD-HHMMSS`.

**Backup rule** (applies throughout): before overwriting any file 鈥?source, outline, prompt, image 鈥?rename the existing one to `<name>-backup-YYYYMMDD-HHMMSS.<ext>`. This protects user edits.

## Workflow

```
- [ ] Step 0: Load EXTEND.md 鉀?BLOCKING (interactive only)
- [ ] Step 1: Analyze content 鈫?analysis.md
- [ ] Step 2: Smart Confirm 鈿狅笍 REQUIRED (Path A / B / C)
- [ ] Step 3: Generate images
- [ ] Step 4: Completion report
```

### Step 0: Load EXTEND.md 鉀?BLOCKING

Check these paths in order; first hit wins:

| Path | Scope |
|------|-------|
| `.copy2image-workflow/t2i-image-cards/EXTEND.md` | Project |
| `${XDG_CONFIG_HOME:-$HOME/.config}/copy2image-workflow/t2i-image-cards/EXTEND.md` | XDG |
| `$HOME/.copy2image-workflow/t2i-image-cards/EXTEND.md` | User home |

- **Found** 鈫?read, parse, print a summary (style / layout / watermark / language), continue.
- **Not found + interactive** 鈫?run first-time setup (see `references/config/first-time-setup.md`) and save before anything else. Do NOT analyze content or ask style questions until preferences exist 鈥?this keeps first-run behavior predictable.
- **Not found + `--yes`** 鈫?skip setup, use built-in defaults (no watermark, style/layout auto-selected, language from content). Do not prompt, do not create EXTEND.md.

**EXTEND.md keys**: watermark, preferred style/layout, custom style definitions, language preference. Schema: `references/config/preferences-schema.md`.

### Step 1: Analyze Content 鈫?`analysis.md`

1. Save the source (backup rule applies if `source.md` exists).
2. Run the deep analysis in `references/workflows/analysis-framework.md`: content type, hook potential, audience, engagement signals, visual opportunity map, swipe flow.
3. Detect source language, pick recommended image count (2-10).
4. Auto-recommend strategy + style + layout + palette using the **Auto-Selection** table above.
5. Write everything to `analysis.md`.

### Step 2: Smart Confirm 鈿狅笍 REQUIRED

Goal: present the auto-recommended plan and let the user confirm or adjust. Skip this step entirely under `--yes` 鈥?proceed with Path A using the analysis and any CLI overrides.

**Display summary** before asking:

```
馃搵 鍐呭鍒嗘瀽
  涓婚锛歔topic] | 绫诲瀷锛歔content_type]
  瑕佺偣锛歔key points]
  鍙椾紬锛歔audience]

馃帹 鎺ㄨ崘鏂规锛堣嚜鍔ㄥ尮閰嶏級
  绛栫暐锛歔A/B/C] [name]锛圼reason]锛?
  椋庢牸锛歔style] 路 甯冨眬锛歔layout] 路 閰嶈壊锛歔palette or 榛樿] 路 棰勮锛歔preset]
  鍥剧墖锛歔N]寮狅紙灏侀潰+[N-2]鍐呭+缁撳熬锛?
  鍏冪礌锛歔background] / [decorations] / [emphasis]
```

Then ask one question 鈥?three paths. Verbatim option copy: `references/confirmation.md`.

**Path A 鈥?Quick confirm** (trust auto-recommendation): generate a single outline using the recommended strategy + style 鈫?save to `outline.md` 鈫?Step 3.

**Path B 鈥?Customize**: ask five questions (strategy/style, layout, palette, count, optional notes) with the recommendation pre-filled 鈥?blanks keep the recommendation. Generate one outline with the user's choices 鈫?`outline.md` 鈫?Step 3. See `references/confirmation.md`.

**Path C 鈥?Detailed mode**: two sub-confirmations.

- *Step 2a 鈥?Content understanding*: ask selling points (multi-select), audience, style preference (authentic / professional / aesthetic / auto), optional context. Update `analysis.md`.
- *Step 2b 鈥?Three outline variants*: generate `outline-strategy-a.md`, `outline-strategy-b.md`, `outline-strategy-c.md`. Each MUST have a different structure AND a different recommended style 鈥?include `style_reason` in the frontmatter. Page-count heuristic: A ~4-6, B ~3-5, C ~3-4. Template: `references/workflows/outline-template.md`; frontmatter example in `references/confirmation.md`.
- *Step 2c 鈥?Selection*: ask three questions (outline A/B/C/Combined, style, visual elements). Save selected/merged outline to `outline.md` 鈫?Step 3.

### Step 3: Generate Images

With confirmed outline + style + layout + palette:

**Visual consistency 鈥?image-1 anchor chain**: character / mascot / color rendering drifts between calls unless you anchor them. Generate image 1 (cover) first WITHOUT `--ref`, then pass image 1 as `--ref` to every subsequent image. This is the single most important consistency trick for this skill 鈥?don't skip it even if the backend also supports a session ID.

For each image (cover, content, ending):

1. Write the full prompt to `prompts/NN-{type}-{slug}.md` in the user's preferred language (backup rule applies).
2. Generate:
   - **Image 1**: no `--ref` (establishes the anchor).
   - **Images 2+**: add `--ref <path-to-image-01.png>`.
   - Backup rule applies to the PNG files.
3. Report progress after each image.

**Watermark** (if enabled in EXTEND.md): append to the generation prompt:

```
Include a subtle watermark "[content]" positioned at [position].
The watermark should be legible but not distracting.
```

See `references/config/watermark-guide.md`.

**Backend selection**: per the Image Generation Tools rule at the top 鈥?use whatever is available, ask once if multiple, before any generation. Under `--yes`, use the EXTEND.md preference and fall back to the first available backend. Prompt files MUST exist before invoking any backend.

**Session ID** (if the backend supports `--sessionId`): use `cards-{topic-slug}-{timestamp}` for every image; combined with the ref chain this gives maximum consistency.

### Step 4: Completion Report

```
Image Card Series Complete!

Topic: [topic]
Mode: [Quick / Custom / Detailed]
Strategy: [A/B/C/Combined]
Style: [name]
Palette: [name or "default"]
Layout: [name or "varies"]
Location: [directory]
Images: N total

鉁?analysis.md
鉁?outline.md
鉁?outline-strategy-a/b/c.md (detailed mode only)

- 01-cover-[slug].png 鉁?Cover (sparse)
- 02-content-[slug].png 鉁?Content (balanced)
- ...
- NN-ending-[slug].png 鉁?Ending (sparse)
```

## Content Breakdown Principles

| Position | Purpose | Typical layout |
|----------|---------|----------------|
| Cover (image 1) | Hook + visual impact | `sparse` |
| Content (middle) | Core value per image | `balanced` / `dense` / `list` / `comparison` / `flow` |
| Ending (last) | CTA / summary | `sparse` or `balanced` |

For the style 脳 layout compatibility matrix, see the **Style 脳 Layout Matrix** above.

## Image Modification

| Action | How |
|--------|-----|
| Edit | Update `prompts/NN-{type}-{slug}.md` **first**, then regenerate with the same session ID |
| Add | Specify position, create prompt, generate, renumber subsequent files `NN+1`, update outline |
| Delete | Remove files, renumber subsequent `NN-1`, update outline |

Always update the prompt file before regenerating 鈥?it's the source of truth and makes changes reproducible.

## References

| File | Content |
|------|---------|
| `references/confirmation.md` | Verbatim AskUserQuestion copy for every confirmation path |
| `references/style-presets.md` | Full preset shortcut definitions |
| `references/presets/<style>.md` | Per-style element definitions |
| `references/palettes/<name>.md` | Per-palette color definitions |
| `references/elements/canvas.md` | Aspect ratios, safe zones, grid layouts |
| `references/elements/image-effects.md` | Cutout, stroke, filters |
| `references/elements/typography.md` | Decorated text, tags, text direction |
| `references/elements/decorations.md` | Emphasis marks, backgrounds, doodles, frames |
| `references/workflows/analysis-framework.md` | Content analysis framework |
| `references/workflows/outline-template.md` | Outline template with layout guide |
| `references/workflows/prompt-assembly.md` | Prompt assembly guide |
| `references/config/preferences-schema.md` | EXTEND.md schema |
| `references/config/first-time-setup.md` | First-time setup flow |
| `references/config/watermark-guide.md` | Watermark configuration |

## Notes

- Auto-retry once on generation failure before reporting an error.
- For sensitive public figures, use stylized cartoon alternatives.
- Smart Confirm (Step 2) is required; Detailed mode adds a second confirmation (2a + 2c).

Custom configurations via EXTEND.md. See Step 0 for paths and schema.

