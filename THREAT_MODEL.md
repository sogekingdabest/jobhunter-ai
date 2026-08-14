# MVP threat model

This document describes the local, single-user MVP. It is a design baseline, not a claim that the
application is suitable for public internet exposure.

## Assets and trust boundaries

The primary assets are candidate personal data, source documents, job-offer text, provenance
records, generated resume drafts, database credentials, and any future model-provider secrets.

Data crosses four explicit boundaries:

1. The browser sends user-authored candidate facts to the local FastAPI API.
2. Job pages and pasted descriptions enter as untrusted external content.
3. The API persists structured facts and immutable evidence in PostgreSQL.
4. Optional model runtimes receive only task-scoped inputs after the applicable consent policy.

The browser AI laboratory is a separate experimental boundary. It does not receive candidate or job
workspace data automatically.

## Threats and current controls

| Threat | Current controls | Residual risk |
| --- | --- | --- |
| Prompt injection in offers or CVs | External text is labelled untrusted, separated from system instructions, validated against strict schemas, and grounded to exact source spans. | A future provider adapter still requires adversarial evaluation and output validation. |
| Fabricated candidate claims | Candidate profile is the source of truth; matching stores fact IDs; every resume fragment stores immutable source snapshots; approval is explicit. | Lexical grounding is conservative and does not prove semantic equivalence. Human review remains mandatory. |
| SSRF through job URLs | Public-address validation, redirect revalidation, DNS/IP pinning, disabled proxy trust, response limits, and timeouts. | Public endpoints can still serve malicious or misleading content, which remains untrusted. |
| Malicious or oversized documents | Signature/container validation, size and expansion limits, hardened XML, bounded PDF parsing, and root-confined storage keys. | Upload orchestration and malware scanning are not part of this MVP. |
| Personal data leakage in telemetry | HTTP and AI events omit bodies, source text, prompts, output, and direct identifiers; request IDs are bounded. | Operators can still mishandle database backups or manually increase logging verbosity. |
| Secret disclosure | `.env` and key formats are ignored; no provider credential is required for the default workflow. | There is no managed secret store in local development. |
| Unauthorised API access | The API binds to loopback in the supported launcher and the README explicitly limits it to local use. | Authentication, authorisation, CSRF protection, and multi-tenancy are absent. Public exposure is unsafe. |
| Browser storage disclosure | Only the active workflow snapshot is stored; export is user initiated; deletion clears browser state and server resources. | Any script running on the same origin can read local storage. No at-rest browser encryption is provided. |
| Denial of service | Input sizes, URL fetches, model downloads, and document parsing are bounded; model work runs outside the UI thread. | No per-user rate limiting exists because the MVP is local and single-user. |
| Supply-chain compromise | Locked Python and pnpm dependencies, pinned runtime/model revisions, CI, and automated quality checks. | Dependency updates still require human review and vulnerability monitoring. |

## Privacy operations

The UI exports the active workspace as versioned JSON. Deleting the workspace removes the current
job first, then the candidate profile; database cascades remove assessments, embeddings, and resume
drafts. Job evidence spans are removed with their evidence source. Candidate evidence-source rows
contain identifiers and timestamps but no copied candidate text; historical orphan cleanup is a
known maintenance concern before any multi-user or hosted release.

## Security assumptions for the MVP

- The host computer, browser profile, PostgreSQL instance, and local filesystem are controlled by
  one trusted user.
- The API is reachable only through loopback or another trusted development network.
- Real provider credentials and production personal data are not used.
- Generated resumes are reviewed before they are copied, rendered, or submitted.

Before a hosted release, add authentication and authorisation, encrypted transport, CSRF and origin
controls, rate limiting, encrypted backups, retention policies, audit-log governance, secret
management, dependency scanning, and a new multi-user data-isolation review.
