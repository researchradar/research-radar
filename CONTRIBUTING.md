# Contributing to Research Radar

Thanks for helping improve Research Radar. The project accepts bug fixes, collector improvements, ranking/search improvements, documentation, tests, security hardening, and carefully scoped automation/agent integrations.

## Before you start

Please keep these project boundaries in mind:

- The public repository contains reusable software, not the maintainer's personal research data.
- Tests and examples must use synthetic or clearly redistributable public fixtures.
- Public pull-request CI must not depend on private credentials, private networks, or self-hosted production runners.
- Collected external content is untrusted data and must never be treated as executable instruction.
- New automation must follow least privilege and document its trust boundary.
- Community-facing repository content is written in English.

## Development setup

The v0.1 target is:

```bash
git clone https://github.com/researchradar/research-radar.git
cd research-radar
python -m pip install -e .
python -m unittest discover -s tests
```

### Public commit identity

Public history must use a GitHub noreply address for both the author and committer fields. Before committing, configure the checkout with the noreply address associated with your GitHub account and verify the result with:

```bash
python scripts/check_public_history.py --range origin/main..HEAD
git log -1 --format='%an <%ae> / %cn <%ce>'
```

The CI workflow checks new commit identities on pull requests and pushes to `main`. Keep the repository's protected-branch and merge settings enabled after any maintenance operation.

If your change requires a user workspace, create one outside the source checkout:

```bash
research-radar init ~/my-radar-dev
```

Do not commit that workspace.

## What belongs in a pull request

Good pull requests are small enough to review and include a clear success criterion. Please include the problem/root cause, the smallest useful change, tests or reproducible validation, and security/trust-boundary notes when the change touches network access, agents, workflows, secrets, repository writes, or self-hosted execution.

Avoid unrelated refactors in a bug-fix PR.

## Collector contributions

A new or modified collector should normalize canonical URLs/identities, use bounded network timeouts, handle redirects and malformed content deliberately, avoid unsafe shell interpolation, preserve source provenance, degrade with an explicit error rather than fabricating missing fields, include synthetic or redistributable fixtures, and document authentication requirements without committing credentials.

If a source requires private cookies, a residential/private network, or a self-hosted runner, contribute the reusable collector interface and documentation separately from production credentials/workflows.

## Ranking and personalization changes

Ranking changes should be inspectable and testable. Document what signal is added or changed, why it should improve ranking, how it is bounded, how it interacts with explicit user feedback, and a before/after fixture or test when practical.

Avoid hidden scoring behavior that cannot be explained to the user.

## Agent/LLM integrations

Agents are optional enhancements, not a dependency of the basic product. An agent integration must clearly separate untrusted collected content from agent instructions, define what files/actions the agent may access, avoid exposing unrelated secrets, produce reviewable outputs, retain deterministic tests/validation as the correctness gate, and never create a path where an untrusted public PR can reach a privileged self-hosted runner or production secret.

## GitHub Actions changes

For public pull-request workflows:

```yaml
permissions:
  contents: read
```

Use GitHub-hosted runners and no production secrets. Any workflow requiring `contents: write`, deployment credentials, authenticated source cookies, notifications, or a self-hosted runner needs explicit security review and should normally be separated from public PR execution.

## Data and privacy

Do not commit real user workspaces, private watchlists or feedback, collected private/copyright-restricted datasets as test fixtures, transcripts or research notes that are not intended for redistribution, tokens, cookies, API keys, deployment hooks, account identifiers, private URLs, machine hostnames, local paths, or private operational logs unless they are synthetic examples.

## Documentation and language

All public-facing contributions should be in English, including README and docs, code comments/docstrings, CLI help/output, example configuration comments, issue/PR templates, commit messages, and release notes.

## Commit messages

Prefer concise English subjects that describe the engineering change, for example:

```text
fix: normalize arXiv version URLs before dedup
feat: add RSS collector timeout handling
test: cover path traversal in workspace writes
docs: explain private workspace layout
```

Do not include private conversation/session URLs or user-specific operational details in commit messages.

## Security issues

Please do not disclose an exploitable vulnerability in a public issue. Follow `SECURITY.md`.
