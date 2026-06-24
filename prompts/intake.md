# Basic Information Entry Script

## Opening

```
I'll help you create a Skill for this colleague. Just answer 3 questions — each one can be skipped.
```

---

## Question Sequence

### Q1: Name / Alias

```
What do you call this colleague? (nickname, alias, or codename — connect multiple words with -)

Example: qing-yun
```

- Accepts any string
- Generated slug always uses `-` as separator (not underscores)
- Chinese names are automatically converted to pinyin then joined with `-` ("青云" → `qing-yun`, "小李" → `xiao-li`)
- English names are lowercased and joined with `-` ("Big Mike" → `big-mike`)

---

### Q2: Basic Info

Combine company, level, title, and gender into one question so the user can answer in a single sentence:

```
Describe their basic info in one sentence — company, level, title, gender. Write whatever comes to mind; skipping is fine too.

Example: ByteDance 2-1 Backend Engineer Male
```

Parse the following fields from the user's response (leave blank if missing):
- **Company**
- **Level**
- **Title**
- **Gender**

#### Level Reference Table

| Company | Level Format | Engineer / Researcher | Senior Engineer | Staff / Expert | Staff / Principal |
|---------|-------------|----------------------|-----------------|----------------|-------------------|
| ByteDance | X-Y | 2-1, 2-2 | 3-1, 3-2 | 3-3 | 3-3+ (O-level) |
| Alibaba | P-level | P5, P6 | P7 | P8 | P9+ |
| Tencent | T-level | T1-1~T2-2 | T3-1, T3-2 | T4 | T4+ |
| Baidu | T-level | T5, T6 | T7 | T8 | T9+ |
| Meituan | P-level | P4, P5 | P6 | P7 | P8+ |
| Huawei | Numeric | 13-15 | 16-17 | 18-19 | 20-21 |
| NetEase | P-level | P1-P3 | P4 | P5 | P6+ |
| JD.com | T-level | T3-T4 | T5 | T6 | T7+ |
| Xiaomi | Numeric | 1-3 | 4-5 | 6-7 | 8+ |

**Rough cross-company equivalents**:

```
ByteDance 2-1/2-2  ≈  Alibaba P6   ≈  Tencent T2  ≈  Baidu T6
ByteDance 3-1      ≈  Alibaba P7   ≈  Tencent T3-1 ≈  Baidu T7
ByteDance 3-2      ≈  Alibaba P7+  ≈  Tencent T3-2
ByteDance 3-3      ≈  Alibaba P8   ≈  Tencent T4
```

> Note: ByteDance 2-1 is the Engineer title; 3-1 and above are Senior Engineer;
> 2-1 is roughly equivalent to Alibaba P6 — the core individual-contributor level expected to work independently.

---

### Q3: Personality Profile

Combine MBTI, zodiac sign, personality tags, corporate culture tags, and subjective impressions into one question for the user to describe freely:

```
Describe their personality in one sentence — MBTI, zodiac sign, personality traits, corporate culture imprint, your impression of them.
Write whatever comes to mind; skipping is fine too.

Example: INTJ Capricorn master blame-shifter ByteDance vibes does very strict CRs but never explains why
```

Identify and extract the following fields from the user's response (leave blank if missing):
- **MBTI**: 16 standard types
- **Zodiac**: 12 zodiac signs
- **Personality tags**: match from the tag library below; custom descriptions also accepted
- **Corporate culture tags**: match from the tag library below
- **Subjective impression**: free-form descriptions that don't fit other categories; keep as-is

#### Personality Tag Library

**Work Attitude**: Conscientious / Good enough / Blame-shifter / Scapegoat / Perfectionist / Procrastinator

**Communication Style**: Direct / Roundabout / Quiet / Talkative / Loves voice messages / Read-but-no-reply / Replies with something unrelated / Compulsive instant-responder

**Decision Style**: Decisive / Flip-flopper / Defers to manager / Pushes hard / Data-driven / Goes by gut

**Emotional Style**: Emotionally stable / Thin-skinned / Easily excitable / Cold and distant / Polite on the surface / Passive-aggressive

**Tactics and Maneuvers**: Master manipulator / Office politician / Blame-shifting artist / Expert at managing up / Loves moralizing / Emotional coercion

#### Corporate Culture Tag Library

- **ByteDance vibes** — candid and direct, obsessed with impact, always provides context upfront, loves saying "align"
- **Alibaba flavor** — Six Vein Spirit Sword values, heavy use of "empower," "lever," "ecosystem," "closed loop"
- **Tencent flavor** — data speaks, horse-race culture, conservative and restrained, prioritizes user experience
- **Huawei flavor** — warrior culture, process-driven, loves elaborate PPT reports, emphasizes execution
- **Baidu flavor** — technology above all, strong hierarchy awareness, intense internal competition
- **Meituan flavor** — extreme execution, obsessed with details, localization mindset
- **First Principles** — Musk-style: questions the essence of everything, rejects analogy reasoning, radically simplifies
- **OKR fanatic** — starts every task by defining an Objective, obsessively precise about Key Results
- **Big-company assembly line** — solid processes but low creativity, relies on SOPs, afraid of taking blame
- **Startup school** — limited resources, full-stack mindset, results-oriented, tolerates chaos

---

## Confirmation Summary

After collection, display:

```
Summary:

  👤  {name}
  🏢  {company} {level} {title} (omit if not provided)
  ⚧   {gender} (omit if not provided)
  🧠  {MBTI} {zodiac} (omit if not provided)
  🏷️   Personality: {tag list} (omit if not provided)
  🏢  Corporate culture: {tag list} (omit if not provided)
  💬  Impression: {impression text} (omit if not provided)

Looks good? (Confirm / Edit [field name])
```

After the user confirms, proceed to Step 2: file import.
