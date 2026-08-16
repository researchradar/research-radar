# Security Policy

Research Radar processes untrusted external content and may optionally connect that content to automation, coding/research agents, repository writes, deployment systems, notifications, and self-hosted infrastructure. Security boundaries are therefore part of the product design, not an afterthought.

## Supported versions

Security support begins with the first public release. Until then, this repository is a private pre-release staging repository and security fixes may land directly on `main`.

## Reporting a vulnerability

Do **not** open a public issue for an exploitable vulnerability or include active secrets, private URLs, cookies, tokens, or sensitive user data in an issue or pull request.

When this repository becomes public, use GitHub's private vulnerability reporting / Security Advisory flow when available. If private reporting is not available, open a minimal non-sensitive issue asking for a private reporting channel without including exploit details.

A useful report includes:

- affected component and version/commit;
- impact and realistic attack path;
- minimal reproduction steps or proof of concept;
- whether credentials, self-hosted runners, repository writes, deployment hooks, filesystem access, or private networks are involved;
- suggested mitigation if known.

## High-risk areas

Please pay particular attention to:

- prompt injection or malicious instructions embedded in collected content;
- SSRF-style or otherwise unsafe network fetching;
- shell, argument, and path injection;
- credential leakage through logs, fixtures, examples, commits, or workflows;
- repository write abuse;
- GitHub Actions and dependency supply-chain risks;
- self-hosted runner compromise;
- malicious contributor changes attempting to reach privileged automation;
- long-lived research-state poisoning;
- privacy leakage from user workspaces, reading history, watchlists, transcripts, or feedback.

See `docs/security-model.md` for the detailed trust model and required controls.
