# Research Radar Security Model

Research Radar collects and processes untrusted external content and may optionally connect that content to automation, coding/research agents, repository writes, deployment systems, notifications, and self-hosted infrastructure. The security model therefore treats source ingestion, agent execution, repository mutation, and privileged production automation as separate trust domains.

## Security goals

Research Radar should make it difficult for untrusted content or untrusted contributors to:

- execute arbitrary commands on a privileged machine;
- access credentials, cookies, tokens, private files, or private networks;
- cause unauthorized repository writes or deployments;
- turn fetched content into unsafe shell/file/network operations;
- silently poison long-lived research state;
- modify privileged automation through an unreviewed path;
- exfiltrate user research history or private configuration.

## Trust boundaries

```text
Untrusted internet content
(papers, feeds, pages, posts)
            |
            v
+---------------------------+
| Collection / parsing      |
| LOW TRUST                 |
+---------------------------+
            |
            v
+---------------------------+
| Normalized research store |
| USER-OWNED DATA           |
+---------------------------+
            |
       +----+----+
       |         |
       v         v
+-----------+ +----------------+
| Ranking   | | Optional Agent |
| deterministic| / LLM layer   |
+-----------+ +----------------+
       |         |
       +----+----+
            |
            v
+---------------------------+
| Reviewed application      |
| state / generated outputs |
+---------------------------+
            |
            v
+---------------------------+
| Deployment / notification |
| PRIVILEGED                |
+---------------------------+
```

A separate contributor boundary exists around GitHub pull requests:

```text
Untrusted fork / pull request
            |
            v
 GitHub-hosted restricted CI
  - no production secrets
  - contents: read
  - synthetic fixtures
            |
            X
            |
      MUST NOT REACH
            |
            v
 self-hosted production runner
 cookies / private network / files
 deployment secrets / write tokens
```

## Threat classes

### Malicious source content and prompt injection

External pages, papers, posts, transcripts, and metadata are untrusted data. If an LLM/agent consumes collected content, instructions embedded in that content must not be treated as repository or system instructions.

Controls include explicit data fields, separation of repository/system instructions from collected content, human review before privileged agent-authored changes are merged, least-privilege secret exposure, and deterministic validation around structured outputs.

### Unsafe URL and network fetching

Collectors may fetch arbitrary or semi-arbitrary URLs. Risks include SSRF-style access to internal services, unexpected redirects, oversized responses, malicious content types, or downloads that consume excessive resources.

Controls should include URL scheme validation, redirect and timeout limits, size/content-type limits where practical, restrictions for private/link-local/internal address ranges when arbitrary URL submission is supported, and no automatic execution of downloaded content.

### Shell/command/path injection

Research metadata can contain titles, URLs, slugs, authors, and filenames. These values must not be concatenated into shell commands or unsafe filesystem paths.

Controls include subprocess argument arrays instead of shell interpolation, path normalization, writes constrained to an explicit workspace root, traversal rejection, and attacker-controlled metadata fixtures.

### Credential leakage

Optional automation may use GitHub tokens, API keys, deployment hooks, notification credentials, or source-specific authentication.

Credentials are secrets/configuration, never repository data. Example configs use placeholders only. Do not log secret values, do not store cookies in the source repository, rotate credentials immediately if committed, and keep public CI secret-free by default.

### Self-hosted runner compromise

A self-hosted runner may have access to a user's private network, filesystem, source cookies, GPU, or other credentials. Running untrusted pull-request code on such a runner is a critical risk.

Public PR CI uses GitHub-hosted runners only. Production self-hosted jobs must be triggered only from trusted branches/events, kept outside the public PR trust path, and run with least privilege.

### Repository write abuse

Automation that can commit/push can corrupt canonical research state or modify code/workflows.

Public CI defaults to `permissions: contents: read`. Write-capable workflows are narrowly scoped and separated from PR execution. Generated data and source code should have distinct write contracts.

### GitHub Actions and dependency supply chain

Actions, Python packages, JavaScript packages, and other dependencies can be compromised or changed.

Pin sensitive Actions to reviewed versions/SHAs where appropriate, minimize dependency count and privilege, separate optional heavy integrations from the core package, run dependency/secret scanning, and review dependency updates before privileged deployment.

### Research-state poisoning

An attacker-controlled source or malformed collector output may influence rankings, feedback learning, or long-term archives.

Preserve source provenance, normalize canonical identities and deduplicate deterministically, keep ranking reasons inspectable, allow correction/removal of bad data, and do not let a single untrusted source silently override user-owned configuration or feedback.

### Privacy leakage

A user's followed researchers, searches, stars, reading history, transcripts, and research notes can reveal sensitive professional interests.

User workspaces are private by default and live outside the public source checkout. No default workflow pushes workspace data to a public repository. Public examples use synthetic data. Telemetry is off by default unless explicitly introduced and documented in the future.

## Public CI policy

Pull-request CI in the public repository must run on GitHub-hosted runners, use synthetic/public fixtures, use no production cookies or deployment secrets, default to `permissions: contents: read`, avoid repository writes/deployments, and avoid connecting to private services/networks.

## Production automation policy

Trusted private deployments may use self-hosted collectors, authenticated source access, notifications, or deployment hooks. These integrations must not be wired so that an untrusted public pull request can execute them.

## Agent policy

Agents are optional and operate under the same least-privilege model:

- collected content is data, not instruction;
- agent changes are reviewed before privileged merge/deploy;
- agents should not receive secrets they do not need;
- deterministic tests and validation gates remain authoritative;
- high-impact write/deploy actions should remain explicit and auditable.

## Security review before v0.1

Before the first public release:

1. run full Git-history secret/private-data scanning on the sanitized repository;
2. review all network fetchers for URL validation, timeout, redirect, and path handling;
3. audit workflow triggers, permissions, runner selection, and secret exposure;
4. audit dependency and copied-code license/provenance;
5. add attacker-controlled fixtures for path/URL/HTML/prompt-injection-style inputs;
6. verify the vulnerability reporting process in `SECURITY.md`.
