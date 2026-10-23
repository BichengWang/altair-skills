# AGENTS.md

Notes for agents working on this repo. Edit this file; `CLAUDE.md` imports it.

## Layout

- `skills/<name>/SKILL.md` plus `scripts/`: one folder per skill. The frontmatter `name` must match the folder; `description` is at most 1024 characters.
- `.claude-plugin/plugin.json` and `marketplace.json`: the Claude Code plugin. Keep the plugin name and description the same in both.
- `README.md`: install and usage for each skill. Update it with any user-visible change.

## Changing a skill

- Scripts use the standard library only and must run on Python 3.8.
- Verify against the live server: `python3 skills/altair-research/scripts/altair_research.py tickers` and `latest SPY NVDA`. Set `ALTAIR_MCP_URL` to test against a preview deployment.
- If a change depends on a new server tool, merge only after the server change is deployed.
- Bump the semver `version` in `plugin.json` when skill behavior changes.
- Keep the disclaimer: reports are AI-generated and not financial advice.

## Pull requests

- `main` changes only through pull requests; the main ruleset requires the `check` job.
- Fill in `.github/pull_request_template.md`: Summary and Verification.
- The `auto-merge` label squash-merges a PR once `check` passes.
- Use the system git identity; no co-authors.

## Release

Build the committed directory package from the repo root (git archive excludes `.git`; the path exclusions omit review/workflow files):

```bash
git archive --format=zip --output=/Users/kw/my-code/tmp/altair-openai-plugin.zip HEAD -- . ':!.github' ':!AGENTS.md' ':!CLAUDE.md'
```
