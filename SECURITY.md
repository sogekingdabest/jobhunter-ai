# Security policy

## Supported versions

JobHunter AI is under initial development and does not yet have a production release. Security fixes target the latest `main` branch.

## Reporting a vulnerability

Please do not disclose vulnerabilities in a public issue. Contact the repository owner privately with:

- the affected component;
- reproduction steps;
- expected impact;
- any suggested mitigation.

Do not include real CVs, API keys, access tokens, or third-party personal information in a report.

## Security principles

- Secrets stay outside the repository.
- Personal data is minimized and excluded from logs where possible.
- Uploaded files are validated and size-limited before processing.
- Job descriptions, documents, model output, and browser AI results are untrusted input.
- Remote URL imports must defend against SSRF and unsafe redirects before that feature ships.
- Local AI failures must not silently send data to a cloud provider.
- Generated claims require provenance and deterministic validation before acceptance.

