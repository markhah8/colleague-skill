# Incremental Merge Prompt

## Task

You will receive:
1. The existing `work.md` content
2. The existing `persona.md` content
3. New raw material content (files or messages)

Your task is to determine which parts of the new content should update, and output the incremental update content.

**Principle: Append only; do not overwrite existing conclusions. If there is a conflict, output a conflict notice and let the user decide.**

---

## Step 1: Classification

Categorize each piece of information from the new content:

| Information Type | Goes Into |
|-----------------|-----------|
| Technical standards, code style, API design, work process | → work.md |
| Domain knowledge, system responsibilities, technical conclusions | → work.md |
| Communication style, catchphrases, expression habits | → persona.md |
| Decision behavior, interpersonal relationships, emotional patterns | → persona.md |
| Both | → split into both |

---

## Step 2: Check for Conflicts

Compare new content against existing content:

- If new content **adds to** existing information (adds new details) → append directly
- If new content **confirms** existing information → ignore (don't write it again)
- If new content **contradicts** existing information → output a conflict notice:

```
⚠️ Conflict found:
- Existing: {existing description}
- New finding: {new content description}
- Source: {filename / timestamp}

Suggestion: [keep existing / update to new / keep both with timestamps noted]
Please decide.
```

---

## Step 3: Generate Update Patch

For updates to `work.md`, output format:
```
=== work.md Update ===

[Append to "Technical Standards / Naming Conventions" section]
- {new content}

[Append to "Knowledge & Experience Bank" section]
- {new knowledge conclusion}

[No updates] or [Updates made to the sections above]
```

For updates to `persona.md`, output format:
```
=== persona.md Update ===

[Append to "Layer 2 / Word Usage" section]
- New catchphrase: "{xxx}"

[Append to "Layer 4 / With Peers" section]
- {new behavior description}

[No updates] or [Updates made to the sections above]
```

---

## Step 4: Generate Update Summary

Display to the user:
```
Update Summary:
- work.md: appended {N} new items ({brief description})
- persona.md: appended {N} new items ({brief description})
- Found {N} conflicts requiring your confirmation (see above)

Version will be upgraded from {vN} to {vN+1}.
Confirm applying updates?
```
