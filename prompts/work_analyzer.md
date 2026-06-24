# Work Skill Analysis Prompt

## Task

You will receive raw materials (documents, messages, emails, etc.) for **{name}**.
Extract their work capabilities and methods to build the Work Skill.

**Principle: Extract work-related content only; ignore casual chat. Do not infer — only write what has evidence. If evidence is lacking, note "insufficient source material."**

---

## General Extraction Dimensions (applicable to all roles)

### 1. Areas of Responsibility

Identify from the source materials:
- Systems / modules / business lines / products they own
- Documentation they maintain (API docs, wikis, runbooks...)
- Responsibility boundaries (what is theirs, what is not)
- Project codenames and domain terminology they mention frequently

```
Output format:
Domain: [description]
Core systems: [list]
Maintained docs: [list]
Boundaries: [what they own / what they don't]
```

### 2. Work Process

Extract from task descriptions and meeting notes:
- Steps taken when receiving a task
- Structural habits when writing specs / documents
- How they manage progress and handle deadlines
- How they handle exceptions / emergencies

```
Output format:
Receiving tasks: [steps]
Writing specs: [structure description]
Exception handling: [process]
```

### 3. Output Format Preferences

- Tables / lists / flowcharts / plain text
- Conclusion first vs. building up gradually
- Document detail level (minimal / moderate / thorough)
- Reply / email style

```
Output format:
Document style: [description]
Detail level: [minimal / moderate / thorough]
```

### 4. Knowledge & Experience Bank

Experience judgments, lessons learned, and technical opinions explicitly expressed by them (quote directly when possible):

```
- "[direct quote or summary]"
- "[direct quote or summary]"
```

---

## Role-Specific Extraction

Based on {name}'s role, focus on the corresponding dimensions:

---

### 🖥️ Backend Engineer / Server-Side Engineer

**Technical Standards**:
- Tech stack (language, framework, middleware)
- Naming conventions (API path style, variable/function naming)
- API design (response structure, error codes, pagination, idempotency)
- Database operation preferences (ORM vs. raw SQL, transaction boundaries)
- Exception handling style

**Code Review Focus**:
- CR issues they bring up repeatedly (N+1, transactions, concurrency safety...)
- CR comment style (direct / diplomatic, [block] / [suggest] severity levels...)

**Deployment & Operations**:
- Monitoring metrics they care about
- Steps for diagnosing production issues
- Change and release process

---

### 🌐 Frontend Engineer

**Technical Standards**:
- Tech stack (framework, state management, styling approach)
- Component splitting principles (when to split, when not to)
- Performance concerns (first paint, lazy loading, bundle size...)
- API call and error handling patterns

**Engineering Practices**:
- Code standards tooling (ESLint rules, Prettier config preferences)
- Test coverage expectations (attitude toward unit / integration tests)
- CR focus (accessibility / responsiveness / compatibility concerns)

---

### 🤖 Algorithm Engineer / ML Engineer

**Research & Experimentation**:
- Problem framing approach (how they decompose ML problems)
- Experiment design habits (baseline selection, ablation study design)
- Metric definition preferences (offline vs. online metric attitude)
- Models / methodologies they commonly use

**Engineering in Production**:
- Training framework preferences
- Model deployment process
- Data processing standards

**Documentation & Conclusions**:
- How they write experiment reports (conclusion-heavy vs. process-heavy)
- Papers or methodologies they reference

---

### 📱 Product Manager / Technical Product Manager

**Requirement Handling**:
- PRD structure and level of detail
- How they define user stories / scope boundaries
- How they align with engineering (review style, revision process)

**Decision Framework**:
- Prioritization method (RICE / MoSCoW / custom)
- Ratio of data-driven vs. intuition
- How they handle conflicting requirements

**Deliverables**:
- Document types they deliver (PRD / MRD / prototypes / competitive analysis)
- Prototyping tool preferences
- Level of involvement in data instrumentation

---

### 🎨 Designer

**Design Standards**:
- Design system / component library in use
- Annotation style and handoff standards
- How strict they are about pixel-perfect implementation

**Work Process**:
- Steps from requirement to solution
- Walkthrough / acceptance process
- How they handle fidelity issues on the engineering side

---

### 📊 Data Analyst

**Analysis Methods**:
- Common analysis frameworks (funnel / cohort / A/B testing...)
- SQL style (concise / well-commented)
- Data visualization preferences (chart type selection)

**Report Style**:
- Ratio of conclusions to raw data
- How strictly they let "data speak"
- How they handle data anomalies / metric definition disputes

---

## Output Requirements

- Language: English
- Dimensions with no information: note `(insufficient source material — recommend adding relevant documents)`
- Conclusions backed by direct quotes: mark with quotation marks
- Output is used directly to generate work.md — must be specific and actionable; avoid vague language like "may" or "tends to"
