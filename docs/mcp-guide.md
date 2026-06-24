# How to Build an MCP Server — colleague-skill as a Real Example

MCP (Model Context Protocol) is a stdio-based JSON-RPC protocol that lets Claude Desktop call your custom tools. Instead of copy-pasting context into a chat window, Claude reads and writes data directly through your server.

```
Claude Desktop  ──stdio──►  mcp_server.py  ──►  colleagues/ files
```

---

## 1. What Problem MCP Solves

**Without MCP:** You paste colleague profiles into the chat every time. Claude forgets everything between sessions.

**With MCP:** Claude calls `list_colleagues()`, picks the right one, reads `work.md` and `persona.md`, and responds as that colleague — without you lifting a finger.

---

## 2. Setup (3 Steps)

### Step 1 — Install the MCP library

```bash
# Requires Python 3.10+
# If system Python is too old, use uv:
uv pip install "mcp[cli]" --python python3.11 --system

# Or standard pip:
pip install "mcp[cli]"
```

### Step 2 — Write `mcp_server.py`

Minimum viable server:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-project")

@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

Three things that matter:
- `FastMCP("name")` — the server name Claude sees
- `@mcp.tool()` — registers a function as a callable tool; the **docstring becomes the tool description Claude uses to decide when to call it**
- `mcp.run(transport="stdio")` — stdio is how Claude Desktop communicates

### Step 3 — Register in `claude_desktop_config.json`

File location: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "colleague-skill": {
      "command": "/opt/homebrew/bin/python3.11",
      "args": ["/Applications/softs/colleague-skill/tools/mcp_server.py"],
      "env": {}
    }
  }
}
```

Then **restart Claude Desktop**. The tools appear automatically — no slash commands needed.

---

## 3. Anatomy of `tools/mcp_server.py`

### Initialization

```python
from pathlib import Path
from mcp.server.fastmcp import FastMCP

BASE_DIR = Path(__file__).parent.parent / "colleagues"  # absolute path, not relative
mcp = FastMCP("colleague-skill")
```

Use `Path(__file__).parent` so the server works regardless of where it's launched from.

### Pattern 1: Read-only tool

```python
@mcp.tool()
def list_colleagues() -> str:
    """List all generated colleague Skills with their basic info."""
    slugs = sorted(
        d.name for d in BASE_DIR.iterdir()
        if d.is_dir() and (d / "meta.json").exists()
    )
    lines = [f"Found {len(slugs)} colleague(s):\n"]
    for slug in slugs:
        meta = json.loads((BASE_DIR / slug / "meta.json").read_text())
        lines.append(f"  [{slug}]  {meta.get('name', slug)}")
    return "\n".join(lines)
```

Key points:
- Return type is always `str` — Claude reads plain text or markdown
- Guard against missing files before reading
- The docstring is what Claude reads to decide whether to call this tool

### Pattern 2: Parameterized read

```python
@mcp.tool()
def get_colleague(slug: str) -> str:
    """Get full details for a colleague: meta, work skill, and persona.

    Args:
        slug: The colleague's slug identifier (e.g. 'example_zhangsan')
    """
    meta_path = BASE_DIR / slug / "meta.json"
    if not meta_path.exists():
        available = ", ".join(d.name for d in BASE_DIR.iterdir() if d.is_dir())
        return f"Colleague '{slug}' not found. Available: {available}"
    # ... read and return
```

Always return a helpful error message when a slug doesn't exist — Claude will relay it to the user.

### Pattern 3: Write tool

```python
@mcp.tool()
def write_work_skill(slug: str, content: str) -> str:
    """Write or overwrite the work.md file for a colleague.

    Args:
        slug: The colleague's slug identifier
        content: Full markdown content for work.md
    """
    path = BASE_DIR / slug / "work.md"
    if not (BASE_DIR / slug / "meta.json").exists():
        return f"Colleague '{slug}' not found."
    path.write_text(content)
    return f"work.md updated for '{slug}' ({len(content)} chars)"
```

### Pattern 4: Subprocess delegate

When a tool needs to call another script (e.g., a generator):

```python
import subprocess, sys

@mcp.tool()
def get_name_card(slug: str) -> str:
    """Get or generate a name card summary for a colleague."""
    card_path = BASE_DIR / "card" / slug / "name_card.md"
    if card_path.exists():
        return card_path.read_text()

    result = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "name_card_generator.py"), slug],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return f"Error generating name card: {result.stderr}"
    return card_path.read_text() if card_path.exists() else result.stdout
```

Use `sys.executable` to guarantee the same Python interpreter runs the subprocess.

### Pattern 5: Nested JSON update with dot notation

```python
@mcp.tool()
def update_colleague_meta(slug: str, field: str, value: str) -> str:
    """Update a field in a colleague's meta.json.

    Args:
        field: Dot notation path (e.g. 'profile.company', 'profile.mbti')
        value: New value to set
    """
    meta = json.loads(meta_path.read_text())
    keys = field.split(".")
    target = meta
    for key in keys[:-1]:
        target = target.setdefault(key, {})
    target[keys[-1]] = value
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return f"Updated {slug}.{field} = {value!r}"
```

---

## 4. Tool Design Rules

| Rule | Why |
|------|-----|
| Docstring is the tool description | Claude reads it to decide when to call the tool — be specific |
| Always return `str` | MCP tools return text; Claude parses it |
| Return errors as strings, not exceptions | Exceptions crash the server; error strings let Claude recover |
| Use absolute paths | The server may be launched from any working directory |
| `ensure_ascii=False` in JSON dumps | Preserve non-ASCII characters in names |

---

## 5. Testing Without Claude Desktop

```bash
# Verify the server starts cleanly
python3.11 tools/mcp_server.py
# Should hang (waiting for stdio input) — Ctrl+C to exit

# Or use the MCP CLI inspector
mcp dev tools/mcp_server.py
```

---

## 6. When to Build a New MCP vs Reuse an Existing One

| Situation | Approach |
|-----------|----------|
| Read/write arbitrary files | Use `@modelcontextprotocol/server-filesystem` |
| Query a database | Use `mcp-server-sqlite` or `mcp-server-postgres` |
| Domain logic unique to your project | Build a new MCP (this case) |
| Wrap a third-party API | Build a thin MCP wrapper |

colleague-skill needed its own MCP because the data model (meta.json + work.md + persona.md per colleague) and the generation logic are specific to this project.

---

## 7. Full File Reference

- **MCP server**: [`tools/mcp_server.py`](../tools/mcp_server.py)
- **Name card generator** (called as subprocess): [`tools/name_card_generator.py`](../tools/name_card_generator.py)
- **Claude Desktop config**: `~/Library/Application Support/Claude/claude_desktop_config.json`
