# Research Radar Architecture

Research Radar separates reusable software from user-owned research state. A user installs the package, creates a private workspace, and points the system at the researchers, topics, and sources they care about.

## Product loop

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

## Source package vs user workspace

The public source repository should not be a user's research database.

```text
installed research-radar package
          |
          +---- reads ----> WORKSPACE/config
          |
          +---- writes ---> WORKSPACE/data
          |
          +---- writes ---> WORKSPACE/site
```

A minimal workspace is expected to look like:

```text
WORKSPACE/
├── config/
│   ├── people.yaml
│   ├── topics.yaml
│   ├── sources.yaml
│   └── scoring.yaml
├── data/
└── site/
```

The workspace is private user state. It is not meant to be committed back to this repository.

## Core layers

### 1. Configuration

Configuration describes what the user wants to follow and how baseline ranking should behave.

The public repository ships only English synthetic examples. Real watchlists, reading history, feedback, credentials, and private source configuration stay in the workspace or environment-specific secret storage.

### 2. Collection

Collectors retrieve items from supported research sources such as arXiv, RSS feeds, public web pages, or optional authenticated/private adapters.

Collector outputs should preserve provenance and produce normalized item records rather than directly mutating user-facing pages.

External content is untrusted. Collectors must use bounded network behavior and must not execute downloaded content.

### 3. Normalization and identity

Normalization creates stable identities for items and canonicalizes URLs/metadata before ranking or storage.

This layer is responsible for deterministic deduplication across sources and versions where possible.

### 4. Ranking

Baseline ranking should remain inspectable and useful without an LLM.

Signals may include:

- followed researcher/source matches;
- topic matches;
- recency;
- source/venue priors;
- cross-source confirmation;
- explicit user feedback.

Optional personalization may add a local interest model. Optional LLM reranking should operate on a bounded shortlist rather than becoming a prerequisite for the product.

### 5. Research store

Normalized items, application state, reading state, and derived indexes live in the user's workspace.

The storage model must keep writes inside the workspace/output root unless a user explicitly selects another location.

### 6. User surfaces

The first public product contract centers on:

- **Today** — fresh high-value items;
- **Reading** — saved or not-yet-processed high-value items;
- **Search** — search over the user's accumulated research memory;
- **Archive** — time-based browsing of prior discoveries;
- **Following** — the people/topics/sources driving the radar.

### 7. Feedback and personalization

Star, Read, and Not interested are user-owned signals. They should remain useful locally and may feed an optional interest model.

Feedback data is private by default and is not part of this public source repository.

## Automation layer

Automation is optional. A local installation should remain fully usable without GitHub Actions, deployment services, OpenAI, Codex, Claude, or a self-hosted runner.

A safe public automation split is:

```text
Untrusted public PR
       |
       v
GitHub-hosted restricted CI
- read-only repository permission
- synthetic fixtures
- no production secrets

Trusted private deployment
       |
       v
optional privileged automation
- authenticated collectors
- self-hosted resources
- deployment / notification credentials
```

These paths must not be connected so an untrusted public pull request can execute privileged private automation.

## Optional agent / LLM layer

Agents and LLMs are enhancements, not the core execution model.

Useful tasks include semantic reranking, relevance explanations, topic/entity extraction, diagnosing collector schema changes, generating regression tests, and maintaining integrations through reviewed pull requests.

Collected research content remains data even when an agent reads it. Instructions embedded in collected content do not become repository/system instructions.

## Public/private repository direction

The project originated as a private deployment. The open-source extraction removes personal data and production-only state while preserving reusable engineering history where safe.

After v0.1, reusable framework changes should originate in `research-radar`. A private deployment repository should consume stable public releases and hold only deployment-specific configuration, data, credentials, and private automation.

## Security

See `docs/security-model.md` for the detailed threat model and trust boundaries.
