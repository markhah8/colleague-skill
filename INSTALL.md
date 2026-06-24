# colleague.skill Installation Guide

---

## Choose Your Platform

### A. Claude Code (Recommended)

This project follows the official [AgentSkills](https://agentskills.io) standard — the entire repo is a skill directory. Clone it into the Claude skills directory to get started:

```bash
# ⚠️ Must be run at the git repository root!
cd $(git rev-parse --show-toplevel)

# Option 1: Install to current project
mkdir -p .claude/skills
git clone https://github.com/titanwings/colleague-skill .claude/skills/create-colleague

# Option 2: Install globally (available in all projects)
git clone https://github.com/titanwings/colleague-skill ~/.claude/skills/create-colleague
```

Then type `/create-colleague` in Claude Code to get started.

Generated colleague Skills are written to the `./colleagues/` directory by default.

---

### B. OpenClaw

```bash
# Clone to OpenClaw's skills directory
git clone https://github.com/titanwings/colleague-skill ~/.openclaw/workspace/skills/create-colleague
```

Restart your OpenClaw session and type `/create-colleague` to launch.

---

## Installing Dependencies

```bash
# Basic (Python 3.9+)
pip3 install pypinyin        # Chinese name to pinyin slug conversion (optional but recommended)

# Feishu browser method (internal docs / docs requiring login)
pip3 install playwright
playwright install chromium  # Only chromium is needed, not full Chrome

# Feishu MCP method (company-authorized docs, read via App Token)
npm install -g feishu-mcp    # Requires Node.js 16+

# Other format support (optional)
pip3 install python-docx     # Convert Word .docx to text
pip3 install openpyxl        # Convert Excel .xlsx to CSV
```

### Platform Method Selection Guide

| Scenario | Recommended Method |
|----------|--------------------|
| Feishu user with App permissions | `feishu_auto_collector.py` |
| Feishu internal docs (no App permissions) | `feishu_browser.py` |
| Feishu with manually specified links | `feishu_mcp_client.py` |
| DingTalk user | `dingtalk_auto_collector.py` |
| DingTalk message collection failed | Manual screenshot → upload image |
| Slack user | `slack_auto_collector.py` |

**Feishu auto-collection initialization**:
```bash
python3 tools/feishu_auto_collector.py --setup
# Enter App ID and App Secret from the Feishu Open Platform
```

**DingTalk auto-collection initialization**:
```bash
python3 tools/dingtalk_auto_collector.py --setup
# Enter AppKey and AppSecret from the DingTalk Open Platform
# Add --show-browser on first run to complete DingTalk login
```

**Feishu MCP initialization** (used when manually specifying links):
```bash
python3 tools/feishu_mcp_client.py --setup
```

**Feishu browser method** (a login popup appears on first use; login state is reused automatically afterwards):
```bash
python3 tools/feishu_browser.py \
  --url "https://xxx.feishu.cn/wiki/xxx" \
  --show-browser    # Add this flag on first use; not needed after login
```

**Slack auto-collection initialization**:
```bash
pip3 install slack-sdk
python3 tools/slack_auto_collector.py --setup
# Follow the prompts to enter your Bot User OAuth Token (xoxb-...)
```

> For detailed Slack configuration, see the "[Slack Auto-Collection Configuration](#slack-auto-collection-configuration)" section below

---

## Slack Auto-Collection Configuration

### Prerequisites

- Python 3.9+
- Slack Workspace (requires **admin permissions** to install the App, or contact your admin to install it for you)
- `pip3 install slack-sdk`

> **Free Workspace limitation**: Only the most recent **90 days** of message history is accessible. Paid plans (Pro / Business+ / Enterprise) do not have this restriction.

---

### Step 1: Create a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) → **Create New App**
2. Select **From scratch**
3. Enter an App Name (e.g. `colleague-skill-bot`), choose your target Workspace → **Create App**

---

### Step 2: Configure Bot Token Scopes

Go to **OAuth & Permissions** → **Bot Token Scopes** → **Add an OAuth Scope** and add the following permissions:

| Scope | Purpose |
|-------|---------|
| `users:read` | Search user list (required) |
| `channels:read` | List public channels (required) |
| `channels:history` | Read public channel message history (required) |
| `groups:read` | List private channels (required) |
| `groups:history` | Read private channel message history (required) |
| `mpim:read` | List group DMs (optional) |
| `mpim:history` | Read group DM message history (optional) |
| `im:read` | List DMs (optional, requires user authorization) |
| `im:history` | Read DM message history (optional, requires user authorization) |

---

### Step 3: Install the App to Your Workspace

1. Still on the **OAuth & Permissions** page, click **Install to Workspace**
2. After approval by the Workspace admin, copy the **Bot User OAuth Token** (format: `xoxb-...`)

---

### Step 4: Add the Bot to Target Channels

The Bot can only read channels **it has joined**. In Slack, go to each target channel and type:

```
/invite @your-bot-name
```

> Tip: If you don't know which channels your target colleague is in, you can skip this step for now. When you run the collector, the script will tell you which channels the Bot has joined — you can then invite it to additional ones.

---

### Step 5: Run the Configuration Wizard

```bash
python3 tools/slack_auto_collector.py --setup
```

Follow the prompts to paste your Bot Token. The script will automatically verify and save it to `~/.colleague-skill/slack_config.json`.

On success you will see:
```
Verifying Token ... OK
  Workspace: Your Company, Bot: colleague-skill-bot

✅ Configuration saved to /Users/you/.colleague-skill/slack_config.json
```

---

### Step 6: Collect Colleague Data

```bash
# Basic usage (enter colleague's name or English username)
python3 tools/slack_auto_collector.py --name "Zhang San"
python3 tools/slack_auto_collector.py --name "john.doe"

# Specify output directory
python3 tools/slack_auto_collector.py --name "Zhang San" --output-dir ./knowledge/zhangsan

# Limit collection volume (recommended for large Workspaces — test with small amounts first)
python3 tools/slack_auto_collector.py --name "Zhang San" --msg-limit 500 --channel-limit 20
```

Output files:
```
knowledge/Zhang San/
├── messages.txt            # Message history sorted by weight
└── collection_summary.json # Collection summary (user info, channel list, timestamps)
```

---

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `missing_scope: channels:history` | Bot Token missing permissions | Go back to api.slack.com → OAuth & Permissions, add the required Scope, reinstall the App |
| `invalid_auth` | Token is invalid or revoked | Re-run `--setup` to configure a new Token |
| `not_in_channel` | Bot has not joined that channel | In Slack, run `/invite @bot` to invite the Bot |
| User not found | Name spelling incorrect | Use English username (e.g. `john.doe`) or Slack display name |
| Messages only go back 90 days | Free plan limitation | Upgrade Workspace or manually supplement with screenshots |
| Rate limit (429) | Too many requests | The script will automatically wait and retry — no manual action needed |

## Quick Verification

```bash
cd ~/.claude/skills/create-colleague   # or your project's .claude/skills/create-colleague

# Test Feishu parser
python3 tools/feishu_parser.py --help

# Test Slack collector
python3 tools/slack_auto_collector.py --help

# Test email parser
python3 tools/email_parser.py --help

# List existing colleague Skills
python3 tools/skill_writer.py --action list --base-dir ./colleagues
```

---

## Directory Structure

The entire repo is a single skill directory (AgentSkills standard format):

```
colleague-skill/        ← clone to .claude/skills/create-colleague/
├── SKILL.md            # Skill entry point (official frontmatter)
├── prompts/            # Prompt templates for analysis and generation
├── tools/              # Python utility scripts
├── docs/               # Documentation (PRD, etc.)
│
└── colleagues/         # Generated colleague Skills storage (.gitignore excluded)
    └── {slug}/
        ├── SKILL.md            # Full Skill (Persona + Work)
        ├── work.md             # Work capabilities only
        ├── persona.md          # Persona only
        ├── meta.json           # Metadata
        ├── versions/           # Version history
        └── knowledge/          # Raw source material archive
```
