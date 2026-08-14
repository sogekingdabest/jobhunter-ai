# JobHunter AI

JobHunter AI is an open-source application for structuring a master CV, evaluating job opportunities, and tailoring resumes without inventing experience, skills, certifications, or achievements.

> [!NOTE]
> The project is being built incrementally. Candidate profiles can now be managed through the API;
> deterministic document parsing and grounded CV fact review are available as backend foundations;
> grounded manual and public-URL job offer imports and explainable structured matching are also
> available; semantic/hybrid matching and traceable tailored-resume drafts are now implemented.

## Product principles

- The master CV is the candidate's single source of truth.
- Every generated claim must be traceable to verified candidate information.
- Matching is hybrid, explainable, and versioned instead of being delegated to a single LLM score.
- Job descriptions and uploaded documents are treated as untrusted input.
- Local and in-browser AI are first-class execution options; cloud processing requires explicit configuration and consent.
- The application starts as a modular monolith and evolves only when operational needs justify it.

## Planned stack

- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic
- **Database:** PostgreSQL 18 and pgvector 0.8.6
- **Frontend:** React, TypeScript, Vite
- **AI:** provider-neutral contracts, browser-local models, local servers, and optional cloud providers
- **Quality:** pytest, Ruff, mypy, pre-commit, and GitHub Actions
- **Infrastructure:** Docker and Docker Compose

## Current repository

The repository currently contains the backend and frontend foundations:

- a minimal FastAPI application;
- typed environment configuration;
- `GET /health`;
- a responsive React application shell with light, dark, and system themes;
- unit and component tests;
- PostgreSQL persistence infrastructure and versioned migrations;
- document provenance models and root-confined local document storage;
- deterministic text extraction for UTF-8 TXT, text-layer PDF, and DOCX;
- a provenance-aware candidate profile aggregate and manual CRUD API;
- linting, formatting, static typing, production builds, and CI.
- provider-neutral structured AI contracts, privacy gates, content-free invocation metadata, and
  a deterministic evaluation harness.
- grounded structured CV fact proposals with exact evidence spans and explicit human review.
- grounded manual job offer imports with normalized fields, classified requirements, and
  deterministic content deduplication.
- SSRF-resistant public-URL previews and imports with bounded deterministic text extraction.
- versioned structured matching with controlled skill aliases, weighted dimensions, mandatory
  requirement gates, and persisted evidence snapshots.
- provider-neutral semantic matching, pgvector caching, and a reproducible hybrid score.
- deterministic tailored-resume selection, optional guarded reformulation, fragment-level
  provenance, optimistic review, and persisted immutable source snapshots.
- an opt-in browser AI laboratory with capability detection, isolated Workers, cancellable model
  loading, and bilingual structured-output benchmarks.

Document upload orchestration, production model adapters, rendered resume exports, and the complete
end-to-end frontend workflow are not implemented yet.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js 24 LTS
- pnpm 11
- Docker Desktop or another Docker Engine with Compose

## Setup

```bash
uv sync --directory backend --all-groups
pnpm --dir frontend install
```

Copy `.env.example` to `.env` if you want to override local settings. Never commit `.env` files.

## Run PostgreSQL

Start the local database and wait for its healthcheck:

```bash
docker compose up -d --wait database
```

Apply every pending schema migration:

```bash
uv run --directory backend alembic upgrade head
```

The default development database is available on `localhost:5432`. The credentials in
`.env.example` are local-only defaults and must not be reused in deployed environments.

## Document storage

Source document bytes are stored outside PostgreSQL under the configurable
`JOBHUNTER_DOCUMENT_STORAGE_PATH`; the default is `storage/documents`. Database records retain
only opaque storage keys, content-derived MIME types, sizes, SHA-256 hashes, processing state, and
provenance metadata. User filenames and local source paths are not retained.

Supported source formats are currently UTF-8 text, PDF, and DOCX, with a configurable default
limit of 10 MiB. Format validation uses file signatures or container structure instead of trusting
an extension or client-provided MIME type.

## Deterministic document parsing

Validated documents can be parsed through `create_document_parsing_service`. Every parser returns
the same in-memory contract: normalized text, non-overlapping offsets, optional PDF page numbers,
and an explicit parser version. Parsed text is not persisted as another full copy of the CV.

- TXT accepts UTF-8 with an optional BOM and normalizes line endings.
- PDF extracts existing text layers page by page with `pypdf`; scanned/image-only and encrypted
  files are reported as unsupported for extraction. OCR is intentionally out of scope.
- DOCX reads only the main WordprocessingML document and applies limits to archive members,
  expanded size, compression ratio, internal paths, and XML parsing.

Documents remain untrusted input. Validation must run before parsing, and parser failures are
returned as domain errors without attempting repairs through an LLM. Upload and processing
endpoints will be added separately.

## AI contracts and evaluation

AI integrations use a provider-neutral structured-generation port. Trusted application
instructions and named input data are separate, and each input declares whether it is supplied by
the user or comes from an untrusted external source. Provider responses must match a JSON Schema
and the request/provider/model identity before application code can consume them.

The privacy policy blocks cloud execution, provider retention, and provider training unless each
capability has explicit consent. Local and browser execution do not silently fall back to cloud.
Invocation events contain only operational metadata such as task, provider, model, duration,
outcome, and optional token counts; prompts, source text, and generated output are excluded.

The current adapter is a deterministic offline fake for tests. Fictional golden fixtures measure
schema validity, canonical exact match, and whether evidence quotes occur in their source text.
Server/cloud provider adapters remain separate future increments; browser inference is currently
isolated in the experimental laboratory below.

## Structured CV fact extraction

The candidate application layer can request provider-neutral structured extraction from an
already parsed CV. Source text is supplied as untrusted data, inference uses temperature zero, and
every returned quote is checked character-for-character against its offsets and parsed block. A
single invalid quote, out-of-range offset, cross-block span, or page mismatch rejects the complete
result before any proposal is stored.

Validated proposals are persisted as `needs_review` with their `EvidenceSource`, `EvidenceSpan`,
provider, model, contract version, confidence, and warnings. Accepting or rejecting a proposal is
an explicit, irreversible audit decision; optimistic revision checks prevent concurrent reviews
from overwriting each other. Acceptance does not silently write incomplete model output into the
master profile. The current fake adapter makes the workflow testable offline. A document-processing
endpoint and real provider selection will be composed in a later increment.

## Grounded job offer imports

Pasted offers are stored with their original text and a canonical SHA-256 fingerprint. The API
accepts the same versioned normalization contract from a browser, local, or future cloud runtime;
provider output and client-supplied output are treated identically as untrusted. Every normalized
field and requirement must cite an exact quote and offsets in the original text before anything is
persisted.

The backend can also run this contract through the provider-neutral structured-generation service.
Trusted instructions remain separate from `job_offer_text`, which is explicitly labeled as
untrusted external input. The prompt tells models to ignore embedded role changes, commands, links,
and output-format overrides, and the provider receives no tools. Schema validation and exact
evidence checks provide the enforceable boundary; prompt wording alone is not treated as a security
control.

Formatting- and case-equivalent content resolves to the same fingerprint. PostgreSQL also
enforces uniqueness, so concurrent imports cannot create duplicates. Richer salary normalization
and production provider orchestration remain separate increments.

Public URL imports use a two-step workflow. `POST /job-offers/url/preview` retrieves and extracts
the page for local or provider-neutral normalization. `POST /job-offers/url` refetches it and
requires the preview fingerprint, so changed content is rejected before persistence. The stored
offer retains both the requested URL and a same-origin canonical URL.

Only HTTP(S) on standard ports is accepted. Every hostname and redirect is resolved before use;
all returned addresses must be globally routable, and the connection is pinned to a validated IP
to prevent DNS rebinding. HTTPS downgrades, credentials, fragments, proxies, environment trust,
cookies across redirects, non-text responses, oversized bodies, excessive redirects, and slow
responses are rejected. HTML extraction ignores executable and non-visible elements. This is a
user-directed single-page fetcher, not a crawler, browser automation system, or anti-bot bypass.

## Structured matching

`POST /match-assessments` compares one persisted candidate profile with one normalized job offer.
Policy `structured-v1` scores only explicit facts across skills, experience, seniority, education,
languages, and location. Active dimension weights are renormalized when an offer does not contain
a dimension. Controlled aliases such as `JS`/`JavaScript` are versioned; unknown terms receive no
invented equivalence.

Every explicitly required job requirement produces a separate gate. A deterministic mismatch
blocks the recommendation without hiding the numeric score, while an ambiguous or unsupported
mandatory requirement yields `needs_review` rather than being guessed as present or absent. The
LLM never calculates this score.

Assessments are immutable snapshots. They retain the policy and taxonomy versions, candidate
revision timestamp, job fingerprint and normalization version, compared values, candidate fact
IDs, job fact IDs, outcomes, and stable explanation codes. This keeps results inspectable even if
the candidate profile is edited later. Deleting the candidate or job also deletes its assessments
to honor local data deletion.

## Semantic and hybrid matching

Semantic matching is isolated behind a provider-neutral `EmbeddingProvider`; application and
domain code do not depend on Google, a cloud API, or a Python model runtime. Candidate summaries,
work experience, and projects are compared with the offer description and responsibilities. Each
semantic result points to the exact candidate and job source IDs used, while contact details are
excluded from embedding inputs.

Policy `hybrid-v1` combines the reproducible structured score (75%) with semantic similarity
(25%). Required-requirement gates remain authoritative: semantic similarity can improve ranking
and surface transferable experience, but it cannot turn a missing mandatory fact into a pass. If
no embedding provider is configured, `structured-v1` remains fully operational.

Embeddings are cached in PostgreSQL with pgvector using content hash, provider, model, revision,
and dimensions as their identity. The MVP uses exact cosine calculations; an approximate HNSW
index is deferred until corpus size and measured latency justify its recall and memory trade-offs.
The current candidate model is
[`google/embeddinggemma-300M`](https://ai.google.dev/gemma/docs/embeddinggemma): multilingual,
2K context, and 768 dimensions by default. Its heavyweight runtime is not installed in the API;
the included bilingual ranking harness must be run against any future adapter before enabling a
specific model revision.

## Traceable tailored resumes

`POST /tailored-resumes` creates a `needs_review` draft from a current candidate, job offer, and
matching snapshot. Policy `tailored-resume-v1` selects facts deterministically, prioritizes facts
already supported by structured or semantic matching evidence, limits section sizes, and excludes
email and phone data from model inputs. Stale or mismatched assessments cannot generate a draft.

The safe default is extractive and requires no model. Every fragment stores its displayed text,
section, generation method, and immutable snapshots of the master-profile fact IDs, evidence-source
IDs, and source text that support it. An optional provider-neutral structured-generation path can
reorder or shorten selected content, but it cannot choose new facts. A conservative validator
rejects missing/extra selection IDs, empty rewrites, and content terms not present in that fragment's
source text, preventing skills copied only from the job description from becoming candidate claims.

Automated grounding is intentionally conservative and does not claim to prove semantic equivalence.
All drafts therefore require an explicit, one-way `approved` or `rejected` user decision, protected
by optimistic revision checks. PDF/DOCX rendering and editable presentation templates remain outside
this increment.

## Browser AI laboratory

The frontend includes an experimental, local-only runtime comparison. It detects WebGPU, WASM,
secure-context, memory, and storage hints before enabling a model download. Each model entry pins
its runtime, revision, license, expected size, language support, and structured-output capability.
Downloads require an explicit checkbox and never fall back to cloud.

- LiteRT-LM 0.15 runs the web-specific Gemma 4 E2B/E4B artifacts inside a dedicated Worker.
- WebLLM 0.2.84 provides the reference JSON-Schema path with Llama 3.2 1B because Gemma 4 is not a
  built-in WebLLM model yet.
- English and Spanish fictional fixtures measure JSON parsing, schema adherence, time to first
  token, total time, and reported throughput.

The laboratory is a hardware benchmark, not a production CV workflow. Models are multi-gigabyte
downloads and may exceed browser or GPU limits. LiteRT-LM's web API remains an early preview, and
its npm version is deliberately pinned because the 0.16.0 publication did not contain its declared
`dist`/`wasm` artifacts when this spike was completed. Cancellation during WebLLM initialization is
best effort because its factory does not expose an initialized engine until loading finishes.

## Run the API

```bash
uv run --directory backend uvicorn jobhunter.main:app --reload
```

The API is then available at `http://127.0.0.1:8000`; its health endpoint is `GET /health`.

Candidate profiles are managed as complete aggregates:

- `POST /candidate-profiles`
- `GET /candidate-profiles/{profile_id}`
- `PUT /candidate-profiles/{profile_id}`
- `DELETE /candidate-profiles/{profile_id}`

Grounded extraction review records expose:

- `GET /candidate-fact-extractions/{extraction_id}`
- `PATCH /candidate-fact-extractions/{extraction_id}/proposals/{proposal_id}`

Grounded job offers expose:

- `POST /job-offers/manual`
- `POST /job-offers/url/preview`
- `POST /job-offers/url`
- `GET /job-offers/{offer_id}`

Structured matching exposes:

- `POST /match-assessments`
- `GET /match-assessments/{assessment_id}`

Traceable tailored resumes expose:

- `POST /tailored-resumes`
- `GET /tailored-resumes/{resume_id}`
- `PATCH /tailored-resumes/{resume_id}/review`

`PUT` replaces the full profile. On updates, nested entries accept only IDs already owned by that
profile so clients can retain stable identities; omitted IDs are generated by the server. Every
manual candidate-profile submission creates a `user_statement` evidence source, and returned facts
expose that provenance identifier. The API documentation and request schemas are available at
`http://127.0.0.1:8000/docs`.

Authentication is not implemented yet. Treat the current API as local-development software and do
not expose it to an untrusted network or store real personal data in a shared environment.

## Run the frontend

```bash
pnpm --dir frontend dev
```

The web application is then available at `http://127.0.0.1:5173`.

## Explore the design system

```bash
pnpm --dir frontend storybook
```

Storybook is available at `http://127.0.0.1:6006`. It documents accessible UI primitives, themes, interaction tests, and mocked network states without requiring the backend.

## Quality checks

```bash
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
uv run --directory backend mypy src tests
uv run --directory backend pytest
pnpm --dir frontend check
```

PostgreSQL integration tests run when `JOBHUNTER_TEST_DATABASE_URL` is set. CI always runs them
against the same PostgreSQL major version used by the local Compose service.

Storybook interaction and accessibility tests run in Chromium. Install its managed test browser locally with:

```bash
pnpm --dir frontend exec playwright install chromium
```

Run every configured hook with:

```bash
uv run --directory backend pre-commit run --all-files
```

## Contributing

Use short-lived `feature/...` or `fix/...` branches and open a pull request into `main`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow.

## Security and privacy

Do not use real CVs, credentials, or personal data in fixtures, issues, or commits. Report vulnerabilities according to [SECURITY.md](SECURITY.md).

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).

