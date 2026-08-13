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
- DOCX parsing limits expanded archive size and uses hardened XML parsing; PDF parsing limits pages
  and extracted text output.
- Job descriptions, documents, model output, and browser AI results are untrusted input.
- Remote URL imports reject non-public destinations at every redirect, pin connections to the
  validated address, disable proxy/environment trust, and enforce strict redirect, size, and time
  limits.
- Local AI failures must not silently send data to a cloud provider.
- Cloud processing, provider retention, and provider training require separate explicit consent.
- AI invocation telemetry must exclude instructions, input content, source documents, and model
  output; only non-sensitive operational metadata and categorical error codes may be recorded.
- Browser model downloads require explicit size/license consent, use pinned artifact revisions,
  run outside the UI thread, and expose cancellation and cache cleanup controls.
- Browser runtime errors remain categorical; source prompts and generated text must not be copied
  into error messages or telemetry.
- Generated claims require provenance and deterministic validation before acceptance.

