# ShotFlow — Multilingual Docs Index

> Single source of truth for supported languages, the bilingual doc table, and translation conventions.

---

## Supported languages

| Language | Code | Status |
|----------|------|--------|
| English  | `en`    | Primary (default, no suffix) |
| 中文      | `zh-CN` | Supported (`.zh.md` sidecar) |
| 日本語    | `ja`    | Planned (no maintainer yet — claim it in an Issue) |

---

## Naming convention

**English is the primary language.** A doc with no language suffix is English; the Chinese version lives next to it as a `.zh.md` sidecar.

```
some-doc.md        ← English (primary)
some-doc.zh.md     ← Chinese (optional switch)
```

Examples:

```
README.md                  ← English
README.zh.md               ← Chinese
AIGC_Experience_Chain.md   ← English
AIGC_Experience_Chain.zh.md ← Chinese
04_SOP/postproduction.md   ← English
04_SOP/postproduction.zh.md ← Chinese
```

This replaces the old convention (Chinese primary + `.en.md` sidecar). The `examples/echo-of-singularity/` case study already follows the new convention.

---

## Bilingual doc table

> Links are relative to this file. Status: bilingual / English only, Chinese pending.

### Root docs

| English (primary) | Chinese | Status |
|-------------------|---------|--------|
| [README.md](../../README.md) | [README.zh.md](../../README.zh.md) | yes |
| [AIGC_Experience_Chain.md](../../AIGC_Experience_Chain.md) | [AIGC_Experience_Chain.zh.md](../../AIGC_Experience_Chain.zh.md) | yes |
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | [CONTRIBUTING.zh.md](../../CONTRIBUTING.zh.md) | yes |
| [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md) | [CODE_OF_CONDUCT.zh.md](../../CODE_OF_CONDUCT.zh.md) | yes |
| [CHANGELOG.md](../../CHANGELOG.md) | — | (changelog entries stay EN-only by convention) |
| [COST_ANALYSIS.md](../../COST_ANALYSIS.md) | [COST_ANALYSIS.zh.md](../../COST_ANALYSIS.zh.md) | yes |
| [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md) | [TROUBLESHOOTING.zh.md](../../TROUBLESHOOTING.zh.md) | yes |
| [SECURITY.md](../../SECURITY.md) | [SECURITY.zh.md](../../SECURITY.zh.md) | yes |
| [docs/tutorial.md](../tutorial.md) | [docs/tutorial.zh.md](../tutorial.zh.md) | yes |

### Subdirectory docs

| English (primary) | Chinese | Status |
|-------------------|---------|--------|
| [06_Research/failure_cases.md](../../06_Research/failure_cases.md) | — | (QA log, EN/CN mixed by convention) |
| [08_Automation/README.md](../../08_Automation/README.md) | [08_Automation/README.zh.md](../../08_Automation/README.zh.md) | yes |

### Project management templates (`07_Team/templates/`)

| English (primary) | Chinese (`.zh.md`) | Status |
|-------------------|--------------------|--------|
| [project_proposal.md](../../07_Team/templates/project_proposal.md) | [project_proposal.zh.md](../../07_Team/templates/project_proposal.zh.md) | yes |
| [progress_checklist.md](../../07_Team/templates/progress_checklist.md) | [progress_checklist.zh.md](../../07_Team/templates/progress_checklist.zh.md) | yes |
| [instructor_review_template.md](../../07_Team/templates/instructor_review_template.md) | [instructor_review_template.zh.md](../../07_Team/templates/instructor_review_template.zh.md) | yes |
| [weekly_report_template.md](../../07_Team/templates/weekly_report_template.md) | [weekly_report_template.zh.md](../../07_Team/templates/weekly_report_template.zh.md) | yes |
| [summary_report_template.md](../../07_Team/templates/summary_report_template.md) | [summary_report_template.zh.md](../../07_Team/templates/summary_report_template.zh.md) | yes |

### Case study (`examples/echo-of-singularity/`)

Already follows the English-primary convention.

| English (primary) | Chinese (`.zh.md`) | Status |
|-------------------|--------------------|--------|
| [README.md](../../examples/echo-of-singularity/README.md) | [README.zh.md](../../examples/echo-of-singularity/README.zh.md) | yes |
| [character_bible_ava.md](../../examples/echo-of-singularity/character_bible_ava.md) | [character_bible_ava.zh.md](../../examples/echo-of-singularity/character_bible_ava.zh.md) | yes |
| [production_plan.md](../../examples/echo-of-singularity/production_plan.md) | [production_plan.zh.md](../../examples/echo-of-singularity/production_plan.zh.md) | yes |
| [production_log.md](../../examples/echo-of-singularity/production_log.md) | [production_log.zh.md](../../examples/echo-of-singularity/production_log.zh.md) | yes |
| [shot_tracker.md](../../examples/echo-of-singularity/shot_tracker.md) | [shot_tracker.zh.md](../../examples/echo-of-singularity/shot_tracker.zh.md) | yes |

---

## Translation conventions

### What to keep unchanged

- **Code blocks**: keep ```` ```bash ```` / ```` ```python ```` content as-is; translate comments only.
- **Mermaid diagrams**: keep `flowchart` / `sequenceDiagram` syntax; node labels may be translated.
- **Tables**: keep row/column structure; translate cell text only.
- **Link paths**: keep relative paths (e.g. `./README.md`, `../AIGC_Experience_Chain.md`) as-is; translate link text only; keep anchors `#xxx`.
- **Technical terms**: keep FastAPI / SQLAlchemy / Celery / Redis / Vite / antd / ComfyUI / Wan2.2 / Flux.1 / SSE / TanStack Query etc. in original form.
- **Commands**: keep `make check`, `docker compose up -d`, `npm run build` etc. as-is.

### Quality bar

- Natural English, no machine-translation feel.
- When the English version changes, sync the Chinese sidecar in the next PR and note "sync zh-CN" in the description.

---

## Contributor translation flow

1. **Fork** the repo.
2. **Claim** a doc by commenting on its Issue (avoid duplicate work); a maintainer confirms.
3. **Branch**: `git checkout -b docs/i18n-<doc-name>`.
4. **Create** the `.zh.md` sidecar per the naming convention above.
5. **Verify locally**:
   - `python 08_Automation/check_doc_links.py` — no broken links.
   - `python 08_Automation/project_health_check.py` — structure intact.
6. **Register**: add a row to the table above and mark.
7. **PR**: title prefixed `docs(i18n):`, description references the English source and translation scope.
8. **Review**: maintainer checks term consistency, link validity, table alignment. Merging publishes both languages.

---

## TODO (welcome to claim)

All core docs and templates now have Chinese sidecars. Remaining community-welcome items:

- [ ] 日本語 (ja) maintainer

---

> Maintained by the ShotFlow team. For new languages or translation issues, open an [Issue](https://github.com/MS33834/ShotFlow/issues).
