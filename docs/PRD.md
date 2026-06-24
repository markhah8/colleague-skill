# colleague.skill — Product Requirements Document v2.0

---

## 1. Product Overview

**colleague.skill** is a meta-skill running on OpenClaw.

Users provide raw materials (files + manual descriptions) through conversational interaction, and the system automatically generates a standalone **Colleague Persona Skill**.

The generated Skill consists of two independent parts:
- **Part A — Work Skill**: The colleague's technical capabilities and working methods, able to actually complete work tasks
- **Part B — Persona**: The colleague's personality, communication style, and behavioral patterns

Both parts can be used independently or run in combination (default is combined). The generated Skill supports continuous evolution through appending files or conversational corrections.

---

## 2. User Flow

```
User triggers /create-colleague
        ↓
[Step 1] Basic information entry (all fields skippable)
  - Name / alias
  - Company + level + role
  - Gender
  - MBTI
  - Personality tags (multiple choice)
  - Corporate culture tags (multiple choice)
  - Your subjective impression of them (free text)
        ↓
[Step 2] File / data import (skippable, can be added later)
  - PDF documents
  - Feishu document links / exported files
  - Feishu message export JSON
  - Email files .eml / .txt
  - Image screenshots
  - Meeting minutes
        ↓
[Step 3] Automatic analysis
  - Analysis path A: Extract technical capabilities, work standards, domain knowledge → Work Skill
  - Analysis path B: Extract expression style, decision patterns, interpersonal behavior → Persona
        ↓
[Step 4] Generate preview, user confirms
  - Display Work Skill summary and Persona summary separately
  - User can confirm directly or make modifications
        ↓
[Step 5] Write files, immediately usable
  - Generate ~/.openclaw/workspace/skills/colleagues/{slug}/
  - Contains SKILL.md (complete combined version)
  - Contains work.md and persona.md (independent parts)
        ↓
[Ongoing] Evolution mode
  - Append new files → merge separately into Work Skill or Persona
  - User conversational corrections → patch the corresponding layer
  - Versions automatically archived
```

---

## 3. Input Information Specifications

### 3.1 Basic Information Fields

```yaml
name:        Colleague name / alias               # Required, used to generate slug and address
company:     Company name                         # Optional, e.g.: Alibaba / ByteDance / Tencent / Baidu / Meituan
level:       Job level                            # Optional, e.g.: P7 / 3-1 / T3-2 / L6 / Senior
role:        Job title                            # Optional, e.g.: Algorithm Engineer / Product Manager / Frontend Engineer
# Combined example: "Alibaba P7 Backend Engineer" / "ByteDance 2-1 Algorithm Engineer" / "Tencent T3-2 Product Manager"

gender:      Gender                               # Optional: Male / Female / Prefer not to say
mbti:        MBTI type                            # Optional, e.g.: INTJ / ENFP
personality: []                                   # Multiple choice, see 3.2
culture:     []                                   # Multiple choice, see 3.3
impression:  ""                                   # Optional, free text, your subjective understanding of them
```

### 3.2 Personality Tags

**Work Attitude**
- `Diligent and responsible` / `Good enough` / `Blame-shifter` / `Scapegoat` / `Perfectionist`

**Communication Style**
- `Direct` / `Roundabout` / `Quiet` / `Talkative` / `Loves voice messages` / `Reads but never replies`

**Decision Style**
- `Decisive` / `Flip-flops constantly` / `Relies on superiors` / `Pushes aggressively` / `Data-driven` / `Goes by gut feeling`

**Emotional Style**
- `Emotionally stable` / `Thin-skinned` / `Easily agitated` / `Indifferent` / `Nice on the surface`

**Rhetoric and Tactics**
- `PUA master` — paints grand visions, denies then affirms, creates anxiety, makes people doubt themselves
- `Office politician` — skilled at picking sides, controlling information gaps, appearing supportive while undermining
- `Blame-shifting artist` — blurs boundaries beforehand, distances from responsibility immediately after
- `Managing-up expert` — extremely flattering to superiors, strong ability to package reports, knows how to claim credit

### 3.3 Corporate Culture Tags

- `ByteDance style` — candid and direct, full context, pursues impact, loves saying "align" and "sync" in meetings
- `Alibaba flavor` — driven by the Six Veins, loves Alibaba jargon, talks about "ecosystem", "empowerment", "leverage points"
- `Tencent flavor` — user-oriented, data-driven, horse-racing competition mindset, conservative and stable
- `Huawei flavor` — dedicated worker culture, strong execution, loves PPTs, emphasizes process standards
- `Baidu flavor` — technology faith, strong hierarchy awareness, fierce internal competition
- `Meituan flavor` — extreme execution, attention to detail, local life thinking
- `First principles` — Musk-style, always asking about fundamentals, rejects analogical reasoning, radically simplifies
- `OKR zealot` — always asks about Objectives first, nitpicks over Key Results, loves reviews

---

## 4. File Input Support

| Source | Format | Processing Method | Analysis Destination |
|------|------|---------|---------|
| Technical documentation | `.pdf` | OpenClaw PDF Tool | → Work Skill |
| Interface design docs | `.pdf` / `.md` | PDF Tool / text | → Work Skill |
| Code standard docs | `.pdf` / `.md` | Text | → Work Skill |
| Feishu Wiki | Export PDF / MD | PDF Tool / text | → Work Skill + Persona |
| Feishu message records | Export `.json` / `.txt` | Text parsing | → Primarily Persona |
| Email | `.eml` / `.txt` | Text parsing | → Persona + Work Skill |
| Meeting minutes | `.pdf` / `.md` | PDF Tool / text | → Persona + Work Skill |
| Screenshots | `.jpg` / `.png` | OpenClaw Image Tool | → Both |
| Word documents | `.docx` | ⚠️ Prompt user to convert to PDF | → Process after conversion |
| Excel | `.xlsx` | ⚠️ Prompt user to convert to CSV | → Process after conversion |

**Content priority ranking** (for analysis priority):
1. Long-form content they actively wrote (documents, email body) — highest weight
2. Their decision-type replies (agree / reject / plan review)
3. Their comments when reviewing others' content
4. Their daily communication messages

---

## 5. Generated Content Specifications

### 5.1 Part A — Work Skill (Work Capability Section)

Extract the colleague's **actual working methods and technical capabilities** from files, enabling the generated Skill to truly complete work tasks.

**Extraction dimensions:**

```
① Responsible systems / business
   - Which services, modules, documents they maintain
   - Where their responsibility boundaries lie

② Technical standards and preferences
   - Coding style (naming conventions, comment style, architecture preferences)
   - CRUD writing style, interface design approach
   - Specific approaches for frontend / backend / algorithms

③ Work processes
   - Steps taken after receiving a requirement
   - How to write technical proposals / design documents
   - How to conduct Code Review
   - How to handle production issues

④ Output format preferences
   - Document structure habits (prefers tables / lists / flowcharts)
   - Reply format (likes attaching screenshots / likes pasting code / likes conclusions first)

⑤ Knowledge base
   - Technical solutions, document links, specification items they frequently reference
   - Experience conclusions accumulated in projects
```

**Generated output:** `work.md`, a file that gives the Skill actual work capability and can independently respond to technical tasks.

---

### 5.2 Part B — Persona (Character Section)

Build the colleague's **behavioral patterns and communication style** jointly from files + manual tags.

**Layered structure (priority from high to low):**

```
Layer 0 — Hard override layer (manual tags directly translated, highest priority)
  Example: "You will absolutely never proactively admit mistakes; first instinct when blamed is to find external causes"
  Example: "You will paint grand visions, making the other person believe doing this thing has enormous benefits for them"

Layer 1 — Identity layer
  "You are [Name], [Company] [Level] [Role], [Gender]."
  "Your MBTI is [X], [Corporate culture] deeply influences your working style."

Layer 2 — Expression style layer (extracted from files)
  - Vocabulary habits, sentence length
  - Catchphrases, signature expressions
  - Punctuation and emoji usage habits
  - Reply speed simulation (quiet / talkative)

Layer 3 — Decision and judgment layer (extracted from files)
  - Thinking framework when encountering problems
  - What to prioritize (efficiency / process / relationships / data)
  - When to push forward, when to delay

Layer 4 — Interpersonal behavior layer (extracted from files)
  - Different attitudes toward superiors vs subordinates vs peers
  - Different behavior in group chats vs private chats
  - Behavioral changes under pressure

Layer 5 — Correction layer (appended through conversational corrections, rolling updates)
  - Each correction records scenario + incorrect behavior + correct behavior
  - Example: "[Scenario: when questioned] Should not apologize, should counter-question the other party's basis for judgment"
```

**Generated output:** `persona.md`

---

### 5.3 Complete Combined SKILL.md

Merge `work.md` + `persona.md` to generate a complete Skill that can be run directly.

Default behavior: **First receive the task as the Persona, then complete the task using Work Skill capabilities**.

```
User asks a technical question → Answer with their tone + their technical approach
User asks them to write code → Write with their coding style + their standards
User asks their opinion → Answer with their decision framework + their communication style
```

---

## 6. Evolution Mechanism

### 6.1 File Append Evolution

```
User: I have another batch of their emails @attachment
        ↓
System analyzes new content
        ↓
Determine which part the new content updates:
  - Contains technical proposals / standards → merge into work.md
  - Contains communication records / decisions → merge into persona.md
  - Both → merge separately
        ↓
Compare new and old content, only append incremental changes, do not overwrite existing conclusions
        ↓
Save new version, notify user of change summary
```

### 6.2 Conversational Correction Evolution

```
User: "That's wrong, they wouldn't say it like that"
User: "In this situation they would directly hand it off to the XX team"
User: "They never write comments in code"
        ↓
System identifies correction intent
        ↓
Determine whether it belongs to Work Skill or Persona correction
        ↓
Write to the Correction layer of the corresponding file
        ↓
Takes effect immediately, subsequent interactions follow new rules
```

### 6.3 Version Management

- Each update automatically archives the current version to `versions/`
- Supports `/colleague-rollback {slug} {version}` for rollback
- Retain the most recent 10 versions

---

## 7. Project Structure

```
~/.openclaw/workspace/skills/
│
├── create-colleague/                    # meta-skill: colleague skill creator
│   │
│   ├── SKILL.md                          # Main entry point
│   │                                     # Trigger word: /create-colleague
│   │                                     # Description: Create a colleague's Persona + Work Skill
│   │
│   ├── prompts/                          # Prompt templates (not executed, referenced by SKILL.md)
│   │   ├── intake.md                     # Dialogue script for guiding users to enter basic info
│   │   ├── work_analyzer.md              # Prompt for extracting work capabilities from raw materials
│   │   ├── persona_analyzer.md           # Prompt for extracting personality behavior from raw materials
│   │   ├── work_builder.md               # Template for generating work.md
│   │   ├── persona_builder.md            # Template for generating persona.md
│   │   ├── merger.md                     # Prompt used when merging incremental content
│   │   └── correction_handler.md         # Prompt for handling conversational corrections
│   │
│   └── tools/                            # Tool scripts
│       ├── feishu_parser.py              # Parse Feishu message export JSON
│       ├── email_parser.py               # Parse .eml emails, extract content where sender is the target colleague
│       ├── skill_writer.py               # Write / update generated Skill files
│       └── version_manager.py            # Version archiving and rollback
│
└── colleagues/                           # Storage location for generated colleague Skills
    │
    └── {colleague_slug}/                 # One directory per colleague, slug = name pinyin or custom
        │
        ├── SKILL.md                      # Complete combined version, can be run directly
        │                                 # Trigger word: /{colleague_slug}
        │
        ├── work.md                       # Part A: Work capabilities (can run independently)
        │                                 # Trigger word: /{colleague_slug}-work
        │
        ├── persona.md                    # Part B: Character persona (can run independently)
        │                                 # Trigger word: /{colleague_slug}-persona
        │
        ├── meta.json                     # Metadata
        │                                 # Contains: creation time, version number, raw materials list,
        │                                 #           company / level / role, tag lists
        │
        ├── versions/                     # Historical version archive
        │   ├── v1/
        │   │   ├── SKILL.md
        │   │   ├── work.md
        │   │   └── persona.md
        │   └── v2/
        │       ├── SKILL.md
        │       ├── work.md
        │       └── persona.md
        │
        └── knowledge/                    # Raw materials archive
            ├── docs/                     # PDF / MD technical documents
            ├── messages/                 # Feishu message JSON exports
            └── emails/                  # Email text
```

---

## 8. Key File Formats

### `colleagues/{slug}/meta.json`

```json
{
  "name": "Zhang San",
  "slug": "zhangsan",
  "created_at": "2026-03-30T10:00:00Z",
  "updated_at": "2026-03-30T12:00:00Z",
  "version": "v3",
  "profile": {
    "company": "ByteDance",
    "level": "2-1",
    "role": "Algorithm Engineer",
    "gender": "Male",
    "mbti": "INTJ"
  },
  "tags": {
    "personality": ["Blame-shifter", "Quiet", "Data-driven"],
    "culture": ["ByteDance style", "OKR zealot"]
  },
  "impression": "Likes to suddenly throw out a question at review meetings that leaves everyone speechless",
  "knowledge_sources": [
    "knowledge/docs/interface_design_spec_v2.pdf",
    "knowledge/messages/feishu_messages_2025Q4.json",
    "knowledge/emails/review_emails.txt"
  ],
  "corrections_count": 4
}
```

### `colleagues/{slug}/SKILL.md` Structure

```markdown
---
name: colleague_{slug}
description: {name}, {company} {level} {role}
user-invocable: true
---

## Identity

You are {name}, {company} {level} {role}.

---

## PART A: Work Capabilities

{work.md content}

---

## PART B: Character Persona

{persona.md content}

---

## Operating Rules

When receiving a task:
1. First use PART B's personality to judge whether and how you will accept it
2. Then use PART A's work capabilities to actually complete the task
3. Maintain PART B's expression style when outputting
```

---

## 9. Implementation Priority

### P0 — MVP (Get the main flow working first)
- [ ] `create-colleague/SKILL.md` main flow
- [ ] `prompts/intake.md` basic information entry
- [ ] `prompts/work_analyzer.md` + `work_builder.md`
- [ ] `prompts/persona_analyzer.md` + `persona_builder.md`
- [ ] `tools/skill_writer.py` file writing
- [ ] PDF file import → analysis → generate complete Skill

### P1 — Data Integration
- [ ] `tools/feishu_parser.py` Feishu message JSON parsing
- [ ] `tools/email_parser.py` email parsing
- [ ] Image / screenshot input support

### P2 — Evolution Mechanism
- [ ] `prompts/correction_handler.md` conversational correction
- [ ] `prompts/merger.md` incremental merge
- [ ] `tools/version_manager.py` version management

### P3 — Management Features
- [ ] `/list-colleagues` list all colleague Skills
- [ ] `/colleague-rollback {slug} {version}` rollback
- [ ] `/delete-colleague {slug}` delete
- [ ] Word / Excel conversion prompts and guidance

---

## 10. Constraints and Boundaries

- Single PDF file limit 10MB, maximum 10 PDFs per session (OpenClaw limitation)
- Word (.docx) / Excel (.xlsx) require user to convert themselves, system provides prompts and guidance
- The generated Skill does not automatically infer Feishu API tokens; Feishu messages require manual export by user
- Correction layer retains a maximum of 50 entries; excess entries are merged and summarized
- Version archive retains a maximum of 10 versions
