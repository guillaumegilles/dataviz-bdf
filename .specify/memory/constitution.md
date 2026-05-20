<!--
## Sync Impact Report

**Version change**: (none) → 1.0.0 (initial creation)

### Modified Principles
- N/A — initial ratification; all 5 principles are new.

### Added Sections
- Core Principles (5 principles: Data Integrity First, Reproducibility,
  Transparent Methodology, Visualization Clarity, Scope Discipline)
- Technology Stack
- Development Workflow
- Governance

### Removed Sections
- N/A

### Templates Requiring Updates
- `.specify/templates/plan-template.md` — ✅ Constitution Check gate language
  verified; generic enough to apply as-is to this data science project.
- `.specify/templates/spec-template.md` — ✅ No project-specific constraints
  required; template is generic and suitable.
- `.specify/templates/tasks-template.md` — ✅ Phase structure is compatible;
  data-pipeline tasks will follow the same phase conventions.
- `.specify/templates/constitution-template.md` — ✅ Source template unchanged
  (not modified; only the instantiated copy in memory/ is updated).

### Deferred TODOs
- None. All fields resolved at initial ratification.
-->

# dataviz-bdf Constitution

*Évolution de l'inclusion financière des français*

## Core Principles

### I. Data Integrity First

All data used in this project MUST be traceable to a public, citable source
(Banque de France WebStat, INSEE, DREES, or data.gouv.fr). Raw data files MUST
NOT be edited manually under any circumstances. Every transformation from raw
source to analytical dataset MUST be performed by a versioned, documented
processing script so that the full data lineage is auditable and reproducible.

**Rationale**: Conclusions about household financial inclusion carry policy
implications. Any data provenance gap or silent manual edit would undermine the
credibility of the analysis and make peer review impossible.

### II. Reproducibility

All analysis MUST be executable end-to-end from raw sources using documented
scripts, with no undocumented intermediate steps. Quarto documents (`.qmd`)
serve as the single source of truth for published results — numbers in the
narrative MUST be generated programmatically, never typed manually.
Dependencies MUST be pinned (e.g., via `requirements.txt` or `pyproject.toml`)
so that the environment can be recreated exactly.

**Rationale**: A data analysis that cannot be re-run by a third party is not a
scientific artifact. Full reproducibility is the baseline standard for this
project.

### III. Transparent Methodology

Every analytical choice — variable selection, model type, lag structure,
geographic aggregation level — MUST be documented in the relevant spec with a
literature-backed or data-backed rationale. Vague justifications ("this variable
seemed useful") are not acceptable and MUST be treated as spec defects requiring
clarification before implementation proceeds.

**Rationale**: The causal question (do deteriorating economic conditions explain
rising over-indebtedness?) is empirically contested. Methodological transparency
is the only defence against confirmation bias and the only path to credible
conclusions.

### IV. Visualization Clarity

Every chart and map produced by this project MUST satisfy all four of the
following requirements before it is considered complete:

1. A clear, descriptive title stating what the chart shows.
2. Labeled axes (or legend) with units where applicable.
3. A data source attribution line (source + year range).
4. A one-sentence takeaway caption summarising the key insight.

No chart or map MUST require an external explanation to be interpreted
correctly. Charts that fail any of these requirements MUST be revised before the
Quarto document is rendered for review.

**Rationale**: The audience includes non-specialist policy readers. Ambiguous
visualisations erode trust and invite misinterpretation of findings.

### V. Scope Discipline

The unit of analysis for this project is the French *département* (96
metropolitan départements). National aggregates MAY be included as contextual
benchmarks only and MUST NOT be used as regression observations. Adding a new
predictor variable to any model MUST be preceded by a documented rationale in
the spec (literature reference or exploratory data analysis finding). Feature
creep — expanding scope without documented justification — MUST be rejected at
spec review.

**Rationale**: Département-level data provides sufficient granularity to detect
spatial heterogeneity in financial inclusion while remaining tractable. Scope
creep would dilute analytical focus and risk underpowered models.

## Technology Stack

- **Reporting & Visualisation**: Quarto (`.qmd` documents rendered to HTML/PDF)
- **Analysis language**: Python 3.x
- **Core libraries**: `pandas`, `geopandas`, `matplotlib` / `plotly`,
  `scikit-learn`, `statsmodels`
- **Data formats**: CSV and/or Parquet for analytical datasets; GeoJSON or
  Shapefile for geographic layers. Proprietary formats (`.xlsx` as final
  storage, `.sav`, etc.) are NOT permitted.
- **Environment management**: `pyproject.toml` or `requirements.txt` with pinned
  versions; virtual environment MUST be documented in `README.md`.
- **Data sources**: Banque de France WebStat API, INSEE bulk downloads, DREES
  open data, data.gouv.fr — all accessed via documented, scriptable methods.
  No manual browser downloads without a corresponding download script or
  documented URL.

## Development Workflow

This project follows **Spec-Driven Development** via Spec Kit. The workflow for
every new analysis block (EDA section, model, map series) is:

1. **Specify** (`speckit.specify`) — write a spec with user stories (what
   question does this block answer?), acceptance criteria, and variable list
   before any code is written.
2. **Clarify** (`speckit.clarify`) — surface and resolve ambiguities; encode
   answers back into the spec.
3. **Plan** (`speckit.plan`) — produce a technical design: data pipeline steps,
   model choice, visualisation layout.
4. **Tasks** (`speckit.tasks`) — decompose the plan into a dependency-ordered
   task list.
5. **Implement** (`speckit.implement`) — execute tasks one-by-one, guided by
   the spec.
6. **Analyze** (`speckit.analyze`) — cross-check spec, plan, and tasks for
   consistency before finalising.

Git integration hooks (`.specify/extensions.yml`) auto-commit after each step
and create feature branches before specification.

## Governance

This constitution supersedes all informal practices and prior conventions for
this project. It is binding from the ratification date.

**Amendment procedure**: Amendments MUST be proposed as a pull-request diff
against `.specify/memory/constitution.md`. Each amendment MUST state: (a) which
principle or section is changing, (b) why the change is necessary, and (c) a
migration note for any in-progress specs affected. The version number MUST be
bumped according to the versioning policy below before merging.

**Versioning policy**:
- **MAJOR** bump — a principle is removed, redefined in a backward-incompatible
  way, or the scope of analysis changes fundamentally.
- **MINOR** bump — a new principle or section is added, or existing guidance is
  materially expanded.
- **PATCH** bump — clarifications, wording improvements, or typo fixes that do
  not alter intent.

**Compliance review**: Every spec and plan MUST include a "Constitution Check"
gate that verifies alignment with the five core principles before implementation
begins. Any violation MUST either be resolved or explicitly justified in the
plan's Complexity Tracking table.

**Version**: 1.0.0 | **Ratified**: 2026-05-20 | **Last Amended**: 2026-05-20
