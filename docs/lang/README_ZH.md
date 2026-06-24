<div align="center"> 

# colleague.skill

> *"You AI guys are code traitors — you've already killed the frontend brothers, and now you're going to kill the backend brothers, the testing brothers, the ops brothers, the infosec brothers, the IC brothers, and finally kill yourselves and all of humanity"*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)](https://claude.ai/code)
[![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-green)](https://agentskills.io)

[![Discord](https://img.shields.io/badge/Discord-Join%20Community-5865F2?logo=discord&logoColor=white)](https://discord.gg/aRjmJBdK)

<br>

Your colleague left the company, leaving behind a mountain of documents no one maintains?<br>
Your intern quit, leaving only an empty desk and an unfinished project?<br>
Your mentor graduated, taking away all the experience and context?<br>
Your partner transferred teams, and the familiar chemistry vanished overnight?<br>
Your predecessor handed over, trying to condense three years of work into three pages?<br>

**Turn cold goodbyes into warm Skills — welcome to cyber-immortality!**

<br>

Provide the colleague's raw materials (Feishu messages, DingTalk documents, emails, screenshots) plus your subjective description<br>
Generate an **AI Skill that can truly work in their place**<br>
Write code in their technical style, answer questions in their tone, know when they would shift blame

[Supported Data Sources](#supported-data-sources) · [Installation](#installation) · [Usage](#usage) · [Demo](#demo) · [Detailed Installation](../../INSTALL.md) · [💬 Discord](https://discord.gg/aRjmJBdK)

[**English**](../../README.md) · [**Español**](README_ES.md) · [**Deutsch**](README_DE.md) · [**日本語**](README_JA.md) · [**Русский**](README_RU.md) · [**Português**](README_PT.md) · [**한국어**](README_KO.md)

</div>

---

> 🆕 **2026.04.14 Update** — **WeChat group is live!** Welcome to join the group to play with dot-skill together, share skills, chat about features, and exchange ideas~
>
> <img src="../assets/wechat-group-qr-3.png" alt="dot-skill WeChat group QR code" width="240">
>
> QR code is valid for 7 days. If expired, come find me on Discord to get a new one.

> 🆕 **2026.04.13 Update** — **dot-skill Roadmap officially released!** colleague.skill is evolving into **dot-skill** — distill anyone, not just colleagues. Multimodal output, skill ecosystems and more are coming.
>
> 👉 **[View full roadmap](ROADMAP_ZH.md)** · **[💬 Discord](https://discord.gg/aRjmJBdK)**
>
> We've also organized Issues, added Milestones, and set up a [public project board](https://github.com/users/titanwings/projects/1). Community contributions welcome — check out the `good-first-issue` labels!

> 🆕 **2026.04.07 Update** — The community's enthusiasm for creating dot-skill derivatives has been overwhelming! I've built a community platform — PRs welcome to maintain and share together!
>
> Any skill or meta-skill can be shared here, and you can link directly to your own GitHub repo. No middleman taking a cut.
>
> 👉 **[titanwings.github.io/colleague-skill-site](https://titanwings.github.io/colleague-skill-site/)** · **[💬 Discord](https://discord.gg/aRjmJBdK)**
>
> Already listed: HuChenFeng.skill · FengGeWangMingTianYa.skill · LuoXiang.skill and more
>
> ⏳ PRs are currently under manual review, may be a bit slow, thanks for your patience!

---

Created by [@titanwings](https://github.com/titanwings) | Powered by Shanghai AI Lab · AI Safety Center

> **April 4th Update:** Added two example colleagues — a security engineer and an interesting HR, in the `colleagues/` directory, feel free to try them out!


## Supported Data Sources

> This is still a beta version of colleague.skill. More source support will be added — stay tuned!

| Source | Messages | Docs / Wiki | Spreadsheets | Notes |
|------|:-------:|:-----------:|:-------:|------|
| Feishu (auto-collect) | ✅ API | ✅ | ✅ | Just enter the name, fully automatic |
| DingTalk (auto-collect) | ⚠️ Browser | ✅ | ✅ | DingTalk API doesn't support message history |
| Slack (auto-collect) | ✅ API | — | — | Admin needs to install Bot; free plan limited to 90 days |
| WeChat chat history | ✅ SQLite | — | — | Currently unstable in testing, recommend using the open-source tools below instead |
| PDF | — | ✅ | — | Manual upload |
| Images / Screenshots | ✅ | — | — | Manual upload |
| Feishu JSON export | ✅ | ✅ | — | Manual upload |
| Email `.eml` / `.mbox` | ✅ | — | — | Manual upload |
| Markdown | ✅ | ✅ | — | Manual upload |
| Paste text directly | ✅ | — | — | Manual input |

### Recommended WeChat Chat Export Tools

The following tools are independent open-source projects. This project does not include their code — our parsers only adapt to their export formats. WeChat auto-decryption has been somewhat unstable in testing, so you can use these open-source tools to export chat history first, then paste or import it into this project:

| Tool | Platform | Description |
|------|------|------|
| [WeChatMsg](https://github.com/LC044/WeChatMsg) | Windows | WeChat chat history export, supports multiple formats |
| [PyWxDump](https://github.com/xaoyaoo/PyWxDump) | Windows | WeChat database decryption and export |
| [Liuhen (Stay Mark)](https://github.com/greyovo/留痕) | macOS | WeChat chat history export (recommended for Mac users) |

> Tool information from [@therealXiaomanChu](https://github.com/therealXiaomanChu). Thanks to all open-source authors — together for cyber-immortality!

---

## Installation

### Claude Code

> **Important**: Claude Code looks for skills in `.claude/skills/` at the **git repository root**. Please run this in the correct location.

```bash
# Install to current project (run at git repository root)
mkdir -p .claude/skills
git clone https://github.com/titanwings/colleague-skill .claude/skills/create-colleague

# Or install globally (available in all projects)
git clone https://github.com/titanwings/colleague-skill ~/.claude/skills/create-colleague
```

### OpenClaw

```bash
git clone https://github.com/titanwings/colleague-skill ~/.openclaw/workspace/skills/create-colleague
```

### Dependencies (optional)

```bash
pip3 install -r requirements.txt
```

> Feishu / DingTalk auto-collection requires configuring App credentials. See [INSTALL.md](../../INSTALL.md) for details.

---

## Usage

In Claude Code, type:

```
/create-colleague
```

Follow the prompts to enter the colleague's name, company and level (e.g. `ByteDance 2-1 Algorithm Engineer`), personality tags, then choose a data source. All fields can be skipped — even just a description can generate a Skill.

After completion, invoke the colleague Skill with `/{slug}`.

### Management Commands

| Command | Description |
|------|------|
| `/list-colleagues` | List all colleague Skills |
| `/{slug}` | Invoke full Skill (Persona + Work) |
| `/{slug}-work` | Work capabilities only |
| `/{slug}-persona` | Persona only |
| `/colleague-rollback {slug} {version}` | Rollback to a previous version |
| `/delete-colleague {slug}` | Delete |

---

## Demo

> Input: `ByteDance 2-1 backend engineer, INTJ, blame-shifter, ByteDance style`

**Scenario 1: Code Review**

```
User           ❯ Help me review this interface design

colleague.skill ❯ Hold on, what's the impact of this interface? The background isn't clear.
                  (After reading) N+1 query, fix it. Use the unified
                  {code, message, data} return structure. That's the standard, don't ask why.
```

**Scenario 2: Shifting Blame**

```
User           ❯ This bug was introduced by you, right?

colleague.skill ❯ Does the go-live time line up? That requirement touched many places, and there were other changes.
```

---

## Features

### Generated Skill Structure

Each colleague Skill consists of two parts that drive output together:

| Part | Content |
|------|------|
| **Part A — Work Skill** | Responsible systems, technical standards, work processes, experience knowledge base |
| **Part B — Persona** | 5-layer personality structure: hard rules → identity → expression style → decision patterns → interpersonal behavior |

Execution logic: `Receive task → Persona judges attitude → Work Skill executes → Output in their tone`

### Supported Tags

**Personality**: Diligent and responsible · Blame-shifter · Perfectionist · Good enough · Procrastinator · PUA master · Office politician · Managing-up expert · Passive-aggressive · Flip-flops constantly · Quiet · Read but never reply …

**Corporate culture**: ByteDance style · Alibaba flavor · Tencent flavor · Huawei flavor · Baidu flavor · Meituan flavor · First principles · OKR zealot · Big corp assembly line · Startup mode

**Level support**: ByteDance 2-1~3-3+ · Alibaba P5~P11 · Tencent T1~T4 · Baidu T5~T9 · Meituan P4~P8 · Huawei grades 13~21 · NetEase · JD · Xiaomi …

### Evolution Mechanism

- **Append files** → automatically analyze delta → merge into corresponding parts, never overwrite existing conclusions
- **Conversational correction** → say "they wouldn't do that, they should be xxx" → write to Correction layer, takes effect immediately
- **Version management** → auto-archive on every update, supports rollback to any previous version

---

## Project Structure

This project follows the [AgentSkills](https://agentskills.io) open standard. The entire repo is a skill directory:

```
create-colleague/
├── SKILL.md              # Skill entry point (official frontmatter)
├── prompts/              # Prompt templates
│   ├── intake.md         #   Dialogue-based information entry
│   ├── work_analyzer.md  #   Work capability extraction
│   ├── persona_analyzer.md #  Personality behavior extraction (with tag translation table)
│   ├── work_builder.md   #   work.md generation template
│   ├── persona_builder.md #   persona.md five-layer structure template
│   ├── merger.md         #   Incremental merge logic
│   └── correction_handler.md # Conversational correction handling
├── tools/                # Python tools
│   ├── feishu_auto_collector.py  # Feishu fully automatic collection
│   ├── feishu_browser.py         # Feishu browser approach
│   ├── feishu_mcp_client.py      # Feishu MCP approach
│   ├── dingtalk_auto_collector.py # DingTalk fully automatic collection
│   ├── slack_auto_collector.py   # Slack fully automatic collection
│   ├── email_parser.py           # Email parsing
│   ├── skill_writer.py           # Skill file management
│   └── version_manager.py        # Version archive and rollback
├── colleagues/           # Generated colleague Skills (gitignored)
├── docs/PRD.md
├── requirements.txt
└── LICENSE
```

---

## Notes

- **Raw material quality determines Skill quality**: chat records + long documents > manual description only
- Recommended priority for collection: long-form content **actively written by them** > **decision-type replies** > daily messages
- Feishu auto-collection requires adding the App bot to relevant group chats
- This is still a demo version — if you find bugs, please file issues!

---
### 📄 Technical Report

> **[Colleague.Skill: Automated AI Skill Generation via Expert Knowledge Distillation](colleague_skill.pdf)**
>
> We wrote a paper detailing the system design of colleague.skill — the two-layer architecture (Work Skill + Persona), multi-source data collection, Skill generation and evolution mechanisms, and evaluation results in real-world scenarios. Feel free to check it out if you're interested!

---

## Star History

<a href="https://www.star-history.com/?repos=titanwings%2Fcolleague-skill&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/image?repos=titanwings/colleague-skill&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/image?repos=titanwings/colleague-skill&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/image?repos=titanwings/colleague-skill&type=date&legend=top-left" />
 </picture>
</a>

---

<div align="center">

MIT License © [titanwings](https://github.com/titanwings)


</div>
