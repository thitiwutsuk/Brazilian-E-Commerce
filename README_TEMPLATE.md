<!--
  README TEMPLATE — usage notes (delete this whole comment block before publishing)

  Distilled from the Telco Customer Churn project README. Works well for any data-science /
  ML / analysis project that proceeds in ordered steps and produces findings along the way.

  How to use:
  1. Copy this file into the new project as README.md
  2. Fill every <...> placeholder
  3. Delete any section that doesn't apply (e.g. no "Dataset" section for a non-data project —
     rename it to whatever the domain needs: "Architecture", "API", "Model", etc.)
  4. Keep the writing principles below as you fill it in:
     - Every Step/Stage gets an actual number or finding attached to it, not just a description
       of what it does. "73.8% vs 65.5%" beats "evaluated the model." Numbers are what convince
       a reader the work is real and not a stub.
     - The Status section at the end must be readable on its own — someone with 10 seconds should
       be able to scan it and know exactly what's done and what the headline results were, without
       reading the rest of the file.
     - Environment Setup must be copy-paste-and-it-runs. No prose describing what to do — the
       actual commands.
     - No emoji. Use **bold**, `code`, and structure (headers/tables/checklists) to create
       visual hierarchy instead.
-->

# <Project Name> — <one-line description of what it does>

![<Stack 1>](https://img.shields.io/badge/<Label>-<Version>-<HexColor>?style=flat-square&logo=<logo-slug>&logoColor=white)
![<Stack 2>](https://img.shields.io/badge/<Label>-<Version>-<HexColor>?style=flat-square&logo=<logo-slug>&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-3DA639?style=flat-square&logo=opensourceinitiative&logoColor=white)
![Progress](https://img.shields.io/badge/Progress-<status>-<color>?style=flat-square)

<One paragraph: what problem this solves, what data/system it works with, and the high-level
approach (e.g. "starts with EDA, then builds two models to compare"). Someone who has never seen
the project should understand the goal after this paragraph alone.>

## Project Structure

```
<project-folder>/
├── <folder>/
│   └── <file>                                     # <what it is / where it came from>
├── <folder>/
│   └── <file>                                     # <what it is / what produces or consumes it>
├── requirements.txt                                # Python dependencies, version-pinned
├── LICENSE
└── README.md                                       # This file
```

| File / Folder | Purpose |
|---|---|
| `<path>` | <what it is, and — if it's generated — which step produces it and which step consumes it> |
| `requirements.txt` | Python packages required, pinned to the exact tested versions |
| `LICENSE` | <license type> |
| `README.md` | This file |

## <Domain Section — e.g. "Dataset" / "Architecture" / "API">

- **Source:** <where the data/system came from>
- **Size / scope:** <rows×columns, or scale of the system>
- **<Domain-specific detail>:** <e.g. target variable, main entities, key constraints>

### <Sub-section if needed — e.g. "Data quality issues found and how they were handled">

- <Each issue found, and the concrete fix — not "cleaned the data" but what was actually wrong and
  what decision was made about it>

## Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

<Exact command(s) to reproduce the full pipeline end-to-end, non-interactively, in order — e.g.:>
```bash
<command to run step/notebook 1>
<command to run step/notebook 2>
```

## Methodology

<One short paragraph orienting the reader: how many steps, how they're organized/split across
files, and any note on writing style if relevant (e.g. "early steps explain every concept in full;
later steps only explain what's new").>

### Step 1: <Step name> *(done | in progress | planned)*
<What this step does and why it's necessary before the next one — 1-2 sentences.>

**Findings / Result:**
- <Concrete number, finding, or decision — not a restatement of what the step does>
- <Another one, if relevant>

### Step 2: <Step name> *(done | in progress | planned)*
...

<Repeat one block per step. Keep each step's Findings/Result section grounded in actual output —
if you haven't run it yet, don't write numbers, mark the step "planned" instead.>

## Status

- [ ] Stage 1 — <group of steps> (<headline result once done>)
- [ ] Stage 2 — <group of steps> (<headline result once done>)
- [ ] Stage 3 — <group of steps> (<headline result once done>)

<One line confirming the whole thing actually runs, once true — e.g. "Both notebooks run
end-to-end with no errors or warnings.">
