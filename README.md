# Research Radar

> **Pre-release staging repository.** The quick-start commands below define the v0.1 product contract and must be implemented before public release.

**Research Radar is a self-hosted research intelligence system for people who follow fast-moving technical fields.** Tell it which researchers, topics, and sources you care about. It continuously collects new material, normalizes and deduplicates it, ranks what is likely to matter to you, and turns it into a searchable personal research feed.

Start locally with no API keys. Add scheduled automation, deployment, LLMs, or coding agents only when you need them.

```text
You provide                  Research Radar gives you

Researchers ----\             Today
Topics ----------+--------->  Reading queue
Sources --------/             Search
                              Archive
                              Interest learning
```

## What you get

Research Radar is designed around five user-facing surfaces:

- **Today** — a concise view of fresh material from researchers, labs, feeds, and field-wide discovery sources.
- **Reading** — high-value items you have not processed yet, plus anything you explicitly saved.
- **Search** — search across everything your radar has collected.
- **Archive** — revisit what the system discovered on a specific day.
- **Following** — inspect and edit the researchers, topics, and sources that drive your radar.

Feedback such as **Star**, **Read**, and **Not interested** can be used to improve an optional local interest model over time.

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
│   └── scoring.yaml
├── data/
└── site/
```

Your workspace contains your interests, reading history, collected content, and generated site. It is **not** part of the Research Radar source repository.

### 3. Configure what you care about

Example `~/my-radar/config/people.yaml`:

```yaml
people:
  - name: Example Researcher
    arxiv_author: true
```

Example `~/my-radar/config/topics.yaml`:

```yaml
topics:
  embodied_ai:
    keywords:
      - vision-language-action
      - robot manipulation
      - world model
```

Example `~/my-radar/config/sources.yaml`:

```yaml
sources:
  - type: arxiv
    enabled: true

  - type: rss
    name: Example Lab
    url: https://example.org/feed.xml
```

The repository ships only synthetic/example configuration. Your real watchlists and preferences stay in your workspace.

### 4. Collect and rank

```bash
research-radar collect --workspace ~/my-radar
```

The collector pipeline:

```text
arXiv / RSS / web pages / supported sources
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
              extract metadata
                    |
                    v
                 rank
                    |
                    v
             workspace/data
```

### 5. Build and open the site

```bash
research-radar build-site --workspace ~/my-radar
research-radar serve --workspace ~/my-radar
```

Open the local URL printed by the command to browse **Today**, **Reading**, **Search**, **Archive**, and **Following**.

## How ranking works

Research Radar separates deterministic discovery from optional personalization.

A baseline installation can rank using transparent signals such as followed researcher/source matches, topic matches, recency, source/venue priors, cross-source confirmation, and explicit user feedback.

An optional local interest model can learn from your feedback without sending your reading history to an external API.

## Your data stays yours

The source repository does **not** contain the maintainer's personal research history, watchlists, transcripts, feedback, collected posts, reading activity, or production deployment state.

By default, your own data should live outside the source checkout in a workspace you control.

Research Radar should not require you to publish or push followed researchers, private watchlists, Star/Read/Not-interested feedback, collected articles or transcripts, research notes, cookies, tokens, webhooks, notification credentials, or deployment secrets to a public GitHub repository.

## Local first

The basic Research Radar loop does **not** require an OpenAI API key, ChatGPT, Codex, Claude, Cloudflare, a self-hosted GitHub Actions runner, or GitHub Actions at all.

You can run collection, ranking, storage, search, and the local site entirely on your own machine.

## Optional automation

Once the local workflow is useful, you can automate it with scheduled collection, static-site deployment, optional notifications, or trusted private collectors.

Public pull-request CI must never run untrusted contributor code on a private/self-hosted runner that has access to cookies, production credentials, private files, or a private network.

See `docs/security-model.md` before enabling self-hosted automation.

## Optional AI and agent layer

Agents enhance Research Radar; they are not required to use it.

Possible integrations include Codex, ChatGPT, Claude, or other coding/research agents for semantic reranking, short relevance explanations, topic/entity extraction, collector diagnosis, regression-test generation, and reviewed integration maintenance.

Collected content is data, not instruction. Deterministic tests and review gates remain authoritative.

## Optional OpenAI API usage

If an OpenAI integration is enabled, a cost-conscious pattern is to use deterministic ranking first and send only a small shortlist to the model.

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

The system should remain functional when this layer is disabled.

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
Today / Reading / Search / Archive
          |
          v
  User Feedback / Interest Model
          +-----------------------> repeat
```

See `docs/security-model.md` and the maintainer migration notes under `docs/maintainers/`.

## Security

Research Radar processes untrusted external content and may be connected to automation, repository write permissions, deployment hooks, and optional agents. Key threat classes include malicious source content, prompt injection, unsafe URL/network fetching, command/path injection, credential leakage, unsafe repository writes, compromised dependencies or GitHub Actions, self-hosted runner compromise, and malicious contributor changes targeting privileged automation.

See `SECURITY.md` and `docs/security-model.md`.

## Development

Public development should use synthetic fixtures and public-safe configuration only.

```bash
python -m unittest discover -s tests
```

Before contributing, read `CONTRIBUTING.md`.

## Project status

Research Radar is being extracted from a real private research workflow into a reusable open-source system. This repository intentionally excludes the maintainer's personal data and production-only infrastructure.

The first public release will focus on:

```text
configure -> collect -> normalize -> rank -> browse/search -> feedback
```

The repository remains private until the history, dependency, provenance, security, CLI, and fresh-clone release gates pass.

## License

License selection is pending a dependency/data/provenance audit before the first public release.
