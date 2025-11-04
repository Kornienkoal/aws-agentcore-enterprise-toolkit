# 🚀 Release Guide

Authoritative steps for cutting and verifying a release of the Bedrock Agent Template. This document is version-agnostic and focuses on process and quality gates.

## Versioning

We follow Semantic Versioning:
- MAJOR: breaking changes
- MINOR: new functionality, backward compatible
- PATCH: bug fixes and docs-only updates

The source of truth for changes is `CHANGELOG.md`. Governance and engineering standards are defined in `.specify/memory/constitution.md` (currently v2.0.0).

## Preconditions

- All stage READMEs are up to date (Infrastructure, Global Tools, Agent Runtime, Frontend)
- Docs diagrams validate and render (see `docs/diagrams/*.mmd` and inline blocks)
- Unit tests are passing locally/CI
- Terraform validates for target envs (e.g., `envs/dev`)
- No local, developer-specific files committed (e.g., `.bedrock_agentcore.yaml`)

## Cut a Release

1) Update versions and changelog
```bash
# Add a new section to CHANGELOG.md under the new version per Keep a Changelog
git add CHANGELOG.md
git commit -m "chore(release): vX.Y.Z"
```

2) Tag the release
```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

3) Create a GitHub Release (recommended)
- Title: `vX.Y.Z`
- Notes: Copy from `CHANGELOG.md` for this version
- CLI (optional):
```bash
gh release create vX.Y.Z -t "Agent Template vX.Y.Z" -n "$(awk '/^## \[vX.Y.Z\]/{flag=1;next}/^## /{flag=0}flag' CHANGELOG.md)"
```

## Verification Checklist

- Documentation
  - [ ] Root README updated (Quick Start, links to stage READMEs)
  - [ ] Stage READMEs render Mermaid inline diagrams
  - [ ] `docs/README.md` links work

- Quality
  - [ ] Unit tests green
  - [ ] Terraform `fmt`, `validate`, and `plan` pass for `infrastructure/terraform/envs/dev`
  - [ ] Optionally deploy to a dev account and perform smoke tests

- Security
  - [ ] No secrets or credentials committed
  - [ ] IAM examples follow least-privilege and document any wildcards

## Sample Commands

```bash
# Validate Terraform (dev)
terraform -chdir=infrastructure/terraform/envs/dev fmt -recursive
terraform -chdir=infrastructure/terraform/envs/dev validate
terraform -chdir=infrastructure/terraform/envs/dev plan -out tf.plan

# Run unit tests
uv run pytest -q tests/unit
```

## Release Notes Template

```markdown
# vX.Y.Z – Summary Title

Highlights
- Short bullet list of the most important changes

Changes
- Infra: brief summary
- Agents/Tools: brief summary
- Frontend: brief summary
- Docs: brief summary

Verification
- Unit tests passing; Terraform validated for envs/dev

Links
- CHANGELOG: <link to section>
- Docs index: docs/README.md
```

## Post-Release

- Monitor issues and triage regressions
- Consider tagging the commit SHA in your infra environment’s change log

---

For background and diagrams, see `docs/README.md`.
