---
name: first-time-setup
description: First-time setup flow for baoyu-infographic preferences
---

# First-Time Setup

## Overview

When no EXTEND.md is found, guide the user through preference setup before generating any infographic.

**鉀?BLOCKING OPERATION**: This setup MUST complete before ANY other workflow steps. Do NOT:
- Ask about source content or topic
- Ask about layout, style, or aspect
- Begin Step 1.2 content analysis

ONLY ask the questions in this setup flow, save EXTEND.md, then continue to Step 1.2.

## Setup Flow

```
No EXTEND.md found
        鈹?
        鈻?
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?AskUserQuestion     鈹?
鈹?(all questions)     鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
        鈹?
        鈻?
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?Create EXTEND.md    鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
        鈹?
        鈻?
    Continue to Step 1.2
```

## Questions

**Language**: Use the user's input language for question text. Do not always default to English.

Use a single `AskUserQuestion` with multiple questions (the runtime auto-adds an "Other" option):

### Question 1: Preferred Layout

```
header: "Layout"
question: "Default layout preference?"
options:
  - label: "Auto-select (Recommended)"
    description: "Pick layout per content in Step 3"
  - label: "bento-grid"
    description: "Multiple topics, overview (general default)"
  - label: "linear-progression"
    description: "Timelines, processes, tutorials"
  - label: "dense-modules"
    description: "High-density modules, data-rich guides"
```

### Question 2: Preferred Style

```
header: "Style"
question: "Default visual style preference?"
options:
  - label: "Auto-select (Recommended)"
    description: "Pick style per tone in Step 3"
  - label: "craft-handmade"
    description: "Hand-drawn, paper craft (general default)"
  - label: "corporate-memphis"
    description: "Flat vector, vibrant"
  - label: "morandi-journal"
    description: "Hand-drawn doodle, warm Morandi tones"
```

### Question 3: Preferred Aspect

```
header: "Aspect"
question: "Default aspect ratio?"
options:
  - label: "Auto-select (Recommended)"
    description: "Pick per layout in Step 4"
  - label: "landscape"
    description: "16:9 (slides, blogs, web)"
  - label: "portrait"
    description: "9:16 (mobile, social, dense modules)"
  - label: "square"
    description: "1:1 (social, thumbnails)"
```

### Question 4: Language

```
header: "Language"
question: "Output language for infographic text?"
options:
  - label: "Auto-detect (Recommended)"
    description: "Match source content language"
  - label: "zh"
    description: "Chinese (涓枃)"
  - label: "en"
    description: "English"
```

### Question 5: Save Location

```
header: "Save"
question: "Where to save preferences?"
options:
  - label: "Project"
    description: ".copy2image-workflow/ (this project only)"
  - label: "User"
    description: "~/.copy2image-workflow/ (all projects)"
```

## Save Locations

| Choice | Path | Scope |
|--------|------|-------|
| Project | `.copy2image-workflow/baoyu-infographic/EXTEND.md` | Current project |
| User | `~/.copy2image-workflow/baoyu-infographic/EXTEND.md` | All projects |

XDG path (`${XDG_CONFIG_HOME:-$HOME/.config}/copy2image-workflow/baoyu-infographic/EXTEND.md`) is also recognized at read time but not offered as a save target during first-time setup.

## After Setup

1. Create the directory if needed
2. Write EXTEND.md with frontmatter (see template below)
3. Confirm: "Preferences saved to [path]"
4. Continue to Step 1.2

## EXTEND.md Template

```yaml
---
version: 1
preferred_layout: [selected layout or null]
preferred_style: [selected style or null]
preferred_aspect: [landscape|portrait|square|null]
language: [selected language or null]
custom_styles: []
---
```

## Modifying Preferences Later

Users can edit EXTEND.md directly or trigger setup again:
- Delete EXTEND.md to re-trigger setup
- Edit YAML frontmatter for quick changes
- Full schema: `references/config/preferences-schema.md`

