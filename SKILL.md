---
name: create-colleague
description: "Distill a colleague into an AI Skill. Auto-collect Feishu/DingTalk data, generate Work Skill + Persona, with continuous evolution. | Distill a colleague into an AI Skill, auto-collect Feishu/DingTalk data, generate Work + Persona, supports continuous evolution."
argument-hint: "[colleague-name-or-slug]"
version: "1.0.0"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
---

> **Language**: This skill supports both English and Chinese. Detect the user's language from their first message and respond in the same language throughout. Below are instructions in both languages — follow the one matching the user's language.

# Colleague.skill Creator (Claude Code Edition)

## Trigger Conditions

Activate when the user says any of the following:
- `/create-colleague`
- "Help me create a colleague skill"
- "I want to distill a colleague"
- "New colleague"
- "Make a skill for XX"

Enter evolution mode when the user says any of the following about an existing colleague Skill:
- "I have new files" / "append"
- "That's wrong" / "He wouldn't do that" / "He should be"
- `/update-colleague {slug}`

List all generated colleagues when the user says `/list-colleagues`.

---

## Tool Usage Rules

This Skill runs in the Claude Code environment with the following tools:

| Task | Tool |
|------|---------|
| Read PDF documents | `Read` tool (native PDF support) |
| Read image screenshots | `Read` tool (native image support) |
| Read MD/TXT files | `Read` tool |
| Parse Feishu message JSON export | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/feishu_parser.py` |
| Feishu auto-collect (recommended) | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/feishu_auto_collector.py` |
| Feishu docs (browser session) | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/feishu_browser.py` |
| Feishu docs (MCP App Token) | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/feishu_mcp_client.py` |
| DingTalk auto-collect | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/dingtalk_auto_collector.py` |
| Parse email .eml/.mbox | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/email_parser.py` |
| Write/update Skill files | `Write` / `Edit` tool |
| Version management | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/version_manager.py` |
| List existing Skills | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/skill_writer.py --action list` |

**Base directory**: Skill files are written to `./colleagues/{slug}/` (relative to the project directory).
To use a global path, use `--base-dir ~/.openclaw/workspace/skills/colleagues`.

---

## Main Flow: Create a New Colleague Skill

### Step 1: Basic Info Collection (3 questions)

Refer to `${CLAUDE_SKILL_DIR}/prompts/intake.md` for the question sequence. Only ask 3 questions:

1. **Alias / Codename** (required)
2. **Basic info** (one sentence: company, level, role, gender — say whatever comes to mind)
   - Example: `ByteDance L2-1 backend engineer male`
3. **Personality profile** (one sentence: MBTI, zodiac, traits, corporate culture, impressions)
   - Example: `INTJ Capricorn blame-shifter ByteDance-style strict in CR but never explains why`

Everything except the alias can be skipped. Summarize and confirm before moving to the next step.

### Step 2: Source Material Import

Ask the user how they'd like to provide materials, showing four options:

```
How would you like to provide source materials?

  [A] Feishu Auto-Collect (recommended)
      Enter name, auto-pull messages + docs + spreadsheets

  [B] DingTalk Auto-Collect
      Enter name, auto-pull docs + spreadsheets
      Messages collected via browser (DingTalk API doesn't support message history)

  [C] Feishu Link
      Provide doc/Wiki link (browser session or MCP)

  [D] Upload Files
      PDF / images / exported JSON / email .eml

  [E] Paste Text
      Copy-paste text directly

Can mix and match, or skip entirely (generate from manual info only).
```

---

#### Option A: Feishu Auto-Collect (Recommended)

First-time setup:
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/feishu_auto_collector.py --setup
```

**Group chat collection** (uses tenant_access_token, bot must be in the group):
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/feishu_auto_collector.py \
  --name "{name}" \
  --output-dir ./knowledge/{slug} \
  --msg-limit 1000 \
  --doc-limit 20
```

**Private chat (P2P) collection** (requires user_access_token + p2p chat_id):

Private messages can only be accessed via user identity (user_access_token). App identity cannot access private chats.

**Prerequisites**:

The user needs to provide:
1. **Feishu app credentials**: `app_id` and `app_secret` (obtained by creating a self-built app on Feishu Open Platform)
2. **User scopes**: The app must have these user scopes enabled:
   - `im:message` — read/send messages as user
   - `im:chat` — read chat list as user
3. **OAuth authorization code (code)**: obtained from the callback URL after user completes OAuth in browser

If the user is missing any of these, guide them through setup. Don't assume anything is pre-configured.

**Getting user_access_token — full flow**:

Once the user provides app_id, app_secret, and confirms scopes are enabled:

1. Generate the OAuth URL for them:
   ```
   https://open.feishu.cn/open-apis/authen/v1/authorize?app_id={APP_ID}&redirect_uri=http://www.example.com&scope=im:message%20im:chat
   ```
   > ⚠️ Note: `redirect_uri` must be added in the app's "Security Settings → Redirect URLs" as `http://www.example.com`
   
2. User opens the URL in browser, logs in and authorizes
3. Page redirects to `http://www.example.com?code=xxx`, user copies the code to you
4. Exchange code for token:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/tools/feishu_auto_collector.py --exchange-code {CODE}
   ```
   Or write a Python script to call the Feishu API directly:
   ```python
   # 1. Get app_access_token
   POST https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal
   Body: {"app_id": "xxx", "app_secret": "xxx"}
   
   # 2. Exchange code for user_access_token
   POST https://open.feishu.cn/open-apis/authen/v1/oidc/access_token
   Header: Authorization: Bearer {app_access_token}
   Body: {"grant_type": "authorization_code", "code": "xxx"}
   ```

**Getting the p2p chat_id**:

Users typically don't know the chat_id. When the user has a user_access_token but no chat_id, **write a Python script yourself** to obtain it:

- **Method**: Send a message to the other user's open_id — the response includes the chat_id
  ```python
  POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id
  Header: Authorization: Bearer {user_access_token}
  Body: {"receive_id": "{target_open_id}", "msg_type": "text", "content": "{\"text\":\"hello\"}"}
  # The chat_id in the response is the p2p chat session ID
  ```
- **Note**: `GET /im/v1/chats` does NOT return p2p chats — this is a Feishu API limitation, not a permission issue. Do not try to use this endpoint to find private chats.
- If the user doesn't know the target's open_id, use tenant_access_token to search contacts:
  ```python
  GET https://open.feishu.cn/open-apis/contact/v3/scopes
  # Returns open_ids of all users visible to the app
  ```

**Running collection**:

Once you have user_access_token and chat_id:
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/feishu_auto_collector.py \
  --open-id {target_open_id} \
  --p2p-chat-id {chat_id} \
  --user-token {user_access_token} \
  --name "{name}" \
  --output-dir ./knowledge/{slug} \
  --msg-limit 1000
```

**Flexibility principle**: The above API calls don't have to go through the collector script. If the script doesn't work or doesn't fit the scenario, write Python scripts directly to call the Feishu API. Key API reference:
- Get token: `POST /auth/v3/app_access_token/internal`, `POST /authen/v1/oidc/access_token`
- Send message (get chat_id): `POST /im/v1/messages?receive_id_type=open_id`
- Fetch messages: `GET /im/v1/messages?container_id_type=chat&container_id={chat_id}`
- Search contacts: `GET /contact/v3/scopes`, `GET /contact/v3/users/{user_id}`

Auto-collected content:
- Group chats: all messages sent by the target in shared groups (system messages and stickers filtered)
- Private chats: full conversation including both parties (for context understanding)
- Feishu docs and Wikis they created/edited
- Related spreadsheets (if accessible)

After collection, use `Read` to load the output files:
- `knowledge/{slug}/messages.txt` → messages (group + private)
- `knowledge/{slug}/docs.txt` → document content
- `knowledge/{slug}/collection_summary.json` → collection summary

If collection fails, diagnose the error and attempt to fix it. Common issues:
- Group chat collection: bot not added to the group
- Private chat collection: user_access_token expired (2-hour TTL, refresh with refresh_token)
- Insufficient permissions: guide user to enable scopes and re-authorize
- Or switch to Option B/C

---

#### Option B: DingTalk Auto-Collect

First-time setup:
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/dingtalk_auto_collector.py --setup
```

Then enter the name for one-click collection:
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/dingtalk_auto_collector.py \
  --name "{name}" \
  --output-dir ./knowledge/{slug} \
  --msg-limit 500 \
  --doc-limit 20 \
  --show-browser   # add this flag on first use to complete DingTalk login
```

Collected content:
- DingTalk docs and knowledge bases they created/edited
- Spreadsheets
- Messages (⚠️ DingTalk API doesn't support message history — auto-switches to browser scraping)

After collection, `Read`:
- `knowledge/{slug}/docs.txt`
- `knowledge/{slug}/bitables.txt`
- `knowledge/{slug}/messages.txt`

If message collection fails, prompt user to upload screenshots of chat history.

---

#### Option D: Upload Files

- **PDF / Images**: `Read` tool directly
- **Feishu message JSON export**:
  ```bash
  python3 ${CLAUDE_SKILL_DIR}/tools/feishu_parser.py --file {path} --target "{name}" --output /tmp/feishu_out.txt
  ```
  Then `Read /tmp/feishu_out.txt`
- **Email files .eml / .mbox**:
  ```bash
  python3 ${CLAUDE_SKILL_DIR}/tools/email_parser.py --file {path} --target "{name}" --output /tmp/email_out.txt
  ```
  Then `Read /tmp/email_out.txt`
- **Markdown / TXT**: `Read` tool directly

---

#### Option C: Feishu Link

When the user provides a Feishu doc/Wiki link, ask which method to use:

```
Feishu link detected. Choose read method:

  [1] Browser Method (recommended)
      Reuses your local Chrome login session
      ✅ Works with internal docs and permission-restricted docs
      ✅ No token configuration needed
      ⚠️  Requires Chrome + playwright installed locally

  [2] MCP Method
      Uses Feishu App Token via official API
      ✅ Stable, no browser dependency
      ✅ Can read messages (needs group chat ID)
      ⚠️  Requires App ID / App Secret setup
      ⚠️  Internal docs need admin authorization for the app

Choose [1/2]:
```

**Option 1 (Browser)**:
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/feishu_browser.py \
  --url "{feishu_url}" \
  --target "{name}" \
  --output /tmp/feishu_doc_out.txt
```
First use will open a browser window for login if not already logged in (one-time only).

**Option 2 (MCP)**:

First-time setup:
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/feishu_mcp_client.py --setup
```

Then read directly:
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/feishu_mcp_client.py \
  --url "{feishu_url}" \
  --output /tmp/feishu_doc_out.txt
```

Read messages (needs chat ID, format `oc_xxx`):
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/feishu_mcp_client.py \
  --chat-id "oc_xxx" \
  --target "{name}" \
  --limit 500 \
  --output /tmp/feishu_msg_out.txt
```

Both methods output to files; use `Read` to load results into the analysis flow.

---

#### Option E: Paste Text

User-pasted content is used directly as text material. No tools needed.

---

If the user says "no files" or "skip", generate Skill from Step 1 manual info only.

### Step 3: Analyze Source Material

Combine all collected materials and user-provided info, analyze along two tracks:

**Track A (Work Skill)**:
- Refer to `${CLAUDE_SKILL_DIR}/prompts/work_analyzer.md` for extraction dimensions
- Extract: responsible systems, technical standards, workflow, output preferences, experiential knowledge
- Emphasize different aspects by role type (backend/frontend/ML/product/design have different focuses)

**Track B (Persona)**:
- Refer to `${CLAUDE_SKILL_DIR}/prompts/persona_analyzer.md` for extraction dimensions
- Translate user-provided tags into concrete behavior rules (see tag translation table)
- Extract from materials: communication style, decision patterns, interpersonal behavior

### Step 4: Generate and Preview

Refer to `${CLAUDE_SKILL_DIR}/prompts/work_builder.md` to generate Work Skill content.
Refer to `${CLAUDE_SKILL_DIR}/prompts/persona_builder.md` to generate Persona content (5-layer structure).

Show the user a summary (5-8 lines each), ask:
```
Work Skill Summary:
  - Responsible for: {xxx}
  - Tech stack: {xxx}
  - CR focus: {xxx}
  ...

Persona Summary:
  - Core personality: {xxx}
  - Communication style: {xxx}
  - Decision pattern: {xxx}
  ...

Confirm generation? Or need adjustments?
```

### Step 5: Write Files

After user confirmation, execute the following:

**1. Create directory structure** (Bash):
```bash
mkdir -p colleagues/{slug}/versions
mkdir -p colleagues/{slug}/knowledge/docs
mkdir -p colleagues/{slug}/knowledge/messages
mkdir -p colleagues/{slug}/knowledge/emails
```

**2. Write work.md** (Write tool):
Path: `colleagues/{slug}/work.md`

**3. Write persona.md** (Write tool):
Path: `colleagues/{slug}/persona.md`

**4. Write meta.json** (Write tool):
Path: `colleagues/{slug}/meta.json`
Content:
```json
{
  "name": "{name}",
  "slug": "{slug}",
  "created_at": "{ISO_timestamp}",
  "updated_at": "{ISO_timestamp}",
  "version": "v1",
  "profile": {
    "company": "{company}",
    "level": "{level}",
    "role": "{role}",
    "gender": "{gender}",
    "mbti": "{mbti}"
  },
  "tags": {
    "personality": [...],
    "culture": [...]
  },
  "impression": "{impression}",
  "knowledge_sources": [...imported file list],
  "corrections_count": 0
}
```

**5. Generate full SKILL.md** (Write tool):
Path: `colleagues/{slug}/SKILL.md`

SKILL.md structure:
```markdown
---
name: colleague-{slug}
description: {name}, {company} {level} {role}
user-invocable: true
---

# {name}

{company} {level} {role}{append gender and MBTI if available}

---

## PART A: Work Capabilities

{full work.md content}

---

## PART B: Persona

{full persona.md content}

---

## Execution Rules

1. PART B decides first: what attitude to take on this task?
2. PART A executes: use your technical skills to complete the task
3. Always maintain PART B's communication style in output
4. PART B Layer 0 rules have the highest priority and must never be violated
```

Inform user:
```
✅ Colleague Skill created!

Location: colleagues/{slug}/
Commands: /{slug} (full version)
          /{slug}-work (work capabilities only)
          /{slug}-persona (persona only)

If something feels off, just say "he wouldn't do that" and I'll update it.
```

---

## Evolution Mode: Append Files

When user provides new files or text:

1. Read new content using Step 2 methods
2. Use `Read` to load existing `colleagues/{slug}/work.md` and `persona.md`
3. Refer to `${CLAUDE_SKILL_DIR}/prompts/merger.md` for incremental analysis
4. Archive current version (Bash):
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/tools/version_manager.py --action backup --slug {slug} --base-dir ./colleagues
   ```
5. Use `Edit` tool to append incremental content to the relevant files
6. Regenerate `SKILL.md` (merge latest work.md + persona.md)
7. Update `meta.json` version and updated_at

---

## Evolution Mode: Conversation Correction

When user expresses "that's wrong" / "he should be":

1. Refer to `${CLAUDE_SKILL_DIR}/prompts/correction_handler.md` to identify correction content
2. Determine if it belongs to Work (technical/workflow) or Persona (personality/communication)
3. Generate correction record
4. Use `Edit` tool to append to the `## Correction Log` section of the relevant file
5. Regenerate `SKILL.md`

---

## Management Commands

`/list-colleagues`:
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/skill_writer.py --action list --base-dir ./colleagues
```

`/colleague-rollback {slug} {version}`:
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/version_manager.py --action rollback --slug {slug} --version {version} --base-dir ./colleagues
```

`/delete-colleague {slug}`:
After confirmation:
```bash
rm -rf colleagues/{slug}
```
