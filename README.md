# Spec-Driven Development Project Template

A GitHub repository template for **Spec-Driven Development (SDD)** — a workflow
where every feature starts as a written specification before any code is written.

## What is Spec-Driven Development?

SDD enforces a structured, document-first development process:

1. **Specify** — write a feature spec with user stories, requirements, and
   acceptance criteria
2. **Clarify** — surface ambiguities and encode answers back into the spec
3. **Plan** — produce a technical design (data model, contracts, project
   structure)
4. **Tasks** — break the plan into a dependency-ordered task list
5. **Implement** — execute tasks one-by-one, guided by the spec
6. **Analyze** — cross-check spec, plan, and tasks for consistency

Each step is supported by a [Spec Kit](https://github.com/github/spec-kit)
command available through GitHub Copilot.

## What's Included

```sh
.specify/
├── templates/          # Spec, plan, tasks, constitution & checklist templates
├── extensions/         # Git integration hooks (auto-branch, auto-commit)
├── extensions.yml      # Hook configuration for each workflow step
├── workflows/          # Spec Kit workflow definitions
└── integrations/       # Optional third-party integrations
```

### Key Concepts

| Artifact | Command | Purpose |
|---|---|---|
| `constitution.md` | `speckit.constitution` | Project-wide principles and non-negotiables |
| `spec.md` | `speckit.specify` | Feature specification (user stories, requirements) |
| `plan.md` | `speckit.plan` | Technical design and research |
| `tasks.md` | `speckit.tasks` | Ordered, actionable implementation tasks |

## Getting Started

1. **Use this template** — click *Use this template* on GitHub to create your repo
2. **Set your constitution** — run `speckit.constitution` to define your project's
   core principles
3. **Start a feature** — run `speckit.specify` with a plain-language description
4. **Follow the workflow** — progress through clarify → plan → tasks → implement

## Git Integration

The template ships with automatic Git hooks:
- Creates a feature branch before specification (`speckit.git.feature`)
- Auto-commits after each workflow step
- Initializes the repository on first use (`speckit.git.initialize`)

Configure or disable hooks in `.specify/extensions.yml`.
