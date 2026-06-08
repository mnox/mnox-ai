# Security Policy

## Scope

`mnox-ai` is a provider-agnostic collection of Agent Skills and local AI-agent
utilities, with Claude Code marketplace files maintained as one provider adapter.
The **skills** are Markdown instructions plus a handful of helper Python scripts
— they ship no network service, no runtime server, and no credential handling, so
their realistic security surface is limited to the local helper scripts under
`plugins/*/skills/*/scripts/`. **Utilities** are a separate package class that may
ship their own runtime (e.g. an MCP server); each documents its own security
considerations and dependencies in its README.

## Reporting a vulnerability

Please **do not** open a public issue for a security report.

Use GitHub's private vulnerability reporting instead:
**Security → Report a vulnerability** on this repository
(<https://github.com/mnox/mnox-ai/security/advisories/new>).

You can expect an initial response within a few days. This is a personal,
best-effort project, so please be patient with any follow-up.

## Supported versions

Only the latest released version receives fixes.
