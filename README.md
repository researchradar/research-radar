# Research Radar

> **v0.1 alpha.** The workspace-first core is implemented and tested.

**Research Radar is a self-hosted research intelligence system for people who follow fast-moving technical fields.** Tell it which researchers, topics, and sources you care about. It collects new material, normalizes and deduplicates it, ranks what is likely to matter to you, and turns it into a searchable personal research feed.

Start locally with no API keys. Add scheduled automation, deployment, LLMs, or coding agents only when you need them.

```text
You provide                  Research Radar gives you

Researchers ----\             Today
Topics ----------+--------->  Reading
Sources --------/             Search
                              Archive
                              Following
```

## What you get

The v0.1 core builds five local static pages:

- **Today** — a ranked view of fresh collected material.
- **Reading** — the full ranked collection for review.
- **Search** — client-side search across collected items.
- **Archive** — items grouped by publication date.
- **Following** — a readable view of the people, topics, sources, and scoring configuration in your private workspace.

Edit the YAML files in your workspace to change what the radar follows. Interactive Star/Read/Not-interested controls and a learned interest model are planned extensions; the current deterministic ranker can already consume feedback entries from `config/feedback.yaml`.

## Quick start

### 1. Install

```bash
git clone https://github.com/researchradar/research-radar.git
cd research-radar
python -m pip install -e .
```

### 2. Create your private workspace

```bash
research-radar init ~/my-radar
```

This creates a user-owned workspace outside the source repository:

```text
~/my-radar/
├── config/
│   ├── people.yaml
│   ├── topics.yaml
│   ├── sources.yaml
│   ├── scoring.yaml
│   └── feedback.yaml
├── data/
└── site/
```

Your workspace contains your interests, feedback, collected content, and generated site. It is **not** part of the Research Radar source repository.

`init` does not overwrite existing configuration files, so it is safe to run again after you have customized a workspace.

### 3. Configure what you care about

Example `~/my-radar/config/people.yaml`:

```yaml
people:
  - name: Example Researcher
    aliases: []
    arxiv_author: true
    priority: 1.0
```

Example `~/my-radar/config/topics.yaml`:

```yaml
topics:
  embodied_ai:
    label: Embodied AI
    keywords:
      - vision-language-action
      - robot manipulation
      - world model
    priority: 1.0
```

Example `~/my-radar/config/sources.yaml`:

```yaml
sources:
  - type: arxiv
    name: arXiv
    enabled: true
    query: all:robotics OR cat:cs.AI

  - type: rss
    name: Example Lab
    enabled: false
    url: https://example.org/feed.xml
```

The repository ships only synthetic/example configuration. Your real watchlists and preferences stay in your workspace.

### 4. Collect and rank

```bash
research-radar collect --workspace ~/my-radar
```

The v0.1 collector supports arXiv queries and RSS/Atom feeds. Configured RSS URLs are checked against private, loopback, link-local, reserved, and multicast destinations before fetching, including redirects.

```text
arXiv / RSS
     |
     v
  collect
     |
     v
normalize identities + URLs
     |
     v
 deduplicate
     |
     v
    rank
     |
     v
workspace/data
```

Collection writes normalized source items and ranked results to the workspace, not to the source checkout.

### 5. Build and open the site

```bash
research-radar build-site --workspace ~/my-radar
research-radar serve --workspace ~/my-radar
```

`serve` binds to `127.0.0.1:8765` by default. Open the printed local URL to browse **Today**, **Reading**, **Search**, **Archive**, and **Following**.

## Fully offline smoke test

A deterministic synthetic fixture set is built in for CI, development, and first-run validation. It does not access the network:

```bash
WORKSPACE="$(mktemp -d)/radar"
research-radar init "$WORKSPACE"
research-radar collect --workspace "$WORKSPACE" --fixture-set synthetic --offline
research-radar build-site --workspace "$WORKSPACE"
test -f "$WORKSPACE/site/index.html"
```

The same flow runs in CI.

## How ranking works

Research Radar separates deterministic discovery from optional personalization.

The current baseline ranker uses transparent signals including followed-person matches, optional institution/question matches, topic matches, recency, source priority, source type, explicit feedback entries, and canonical-identity deduplication. Items matching configured negative topics can be excluded.

The scoring configuration is intentionally inspectable. A learned local interest model is planned, but is not required by the v0.1 core.

## Your data stays yours

The source repository does **not** contain the maintainer's personal research history, watchlists, transcripts, feedback, collected posts, reading activity, or production deployment state.

By default, your own data lives outside the source checkout in a workspace you control.

Research Radar does not require you to publish or push followed researchers, private watchlists, feedback, collected articles, research notes, cookies, tokens, webhooks, notification credentials, or deployment secrets to a public GitHub repository.

## Local first

The basic Research Radar loop does **not** require an OpenAI API key, ChatGPT, Codex, Claude, Cloudflare, a self-hosted GitHub Actions runner, or GitHub Actions at all.

You can run collection, ranking, storage, search, and the local site on your own machine.

## Optional automation

Once the local workflow is useful, you can automate it with scheduled collection, static-site deployment, optional notifications, or trusted private collectors.

Public pull-request CI must never run untrusted contributor code on a private/self-hosted runner that has access to cookies, production credentials, private files, or a private network.

See `docs/security-model.md` before enabling privileged or self-hosted automation.

## Optional AI and agent layer

Agents enhance Research Radar; they are not required to use it.

Possible integrations include Codex, ChatGPT, Claude, or other coding/research agents for semantic reranking, short relevance explanations, topic/entity extraction, collector diagnosis, regression-test generation, and reviewed integration maintenance.

Collected content is data, not instruction. Deterministic tests and review gates remain authoritative.

## Optional OpenAI API usage

If an OpenAI integration is enabled later, a cost-conscious pattern is to use deterministic ranking first and send only a small shortlist to the model.

```text
500 collected items
        |
        v
 deterministic ranking
        |
        v
  20-40 candidates
        |
        v
 optional semantic rerank / explanation
        |
        v
  small high-value shortlist
```

The system remains functional when this layer is disabled.

## Who is Research Radar for?

Research Radar is intended for AI and robotics researchers, PhD students, research engineers, open-source maintainers, and anyone building a long-term searchable personal research memory.

## Architecture

```text
People / Topics / Sources
          |
          v
      Collection
          |
          v
 Normalize + Deduplicate
          |
          v
        Ranking
          |
          v
Today / Reading / Search / Archive / Following
```

See `docs/architecture.md`, `SECURITY.md`, and `docs/security-model.md`.

## Security

Research Radar processes untrusted external content and may be connected to automation, repository write permissions, deployment hooks, and optional agents. Key threat classes include malicious source content, prompt injection, unsafe URL/network fetching, command/path injection, credential leakage, unsafe repository writes, compromised dependencies or GitHub Actions, self-hosted runner compromise, and malicious contributor changes targeting privileged automation.

The v0.1 core includes URL safety checks for user-configured RSS sources, bounded redirects/timeouts, escaped static-site rendering, offline adversarial fixtures, and GitHub-hosted read-only pull-request CI.

See `SECURITY.md` and `docs/security-model.md`.

## Development

Development uses synthetic fixtures and public-safe configuration only.

```bash
python -m pip install -e . pytest
pytest -q
```

Before contributing, read `CONTRIBUTING.md`.

## Project status

The v0.1 alpha focuses on a small, auditable loop:

```text
configure -> collect -> normalize -> rank -> build/search/browse
```

The current v0.1 alpha supports the local workspace, arXiv/RSS collection, deterministic ranking, five static browsing surfaces, an offline synthetic acceptance path, and security-focused network validation. Additional capabilities will be added incrementally while keeping the core small, local-first, and auditable.

## License

Research Radar is released under the MIT License. See `LICENSE`.

Runtime dependencies remain under their own licenses; see `THIRD_PARTY_NOTICES.md`.
