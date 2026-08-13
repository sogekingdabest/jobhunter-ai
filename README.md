# JobHunter AI

JobHunter AI is an open-source application for structuring a master CV, evaluating job opportunities, and tailoring resumes without inventing experience, skills, certifications, or achievements.

> [!NOTE]
> The project is being built incrementally. Candidate profiles can now be managed through the API;
> document parsing, matching, and resume generation are not implemented yet.

## Product principles

- The master CV is the candidate's single source of truth.
- Every generated claim must be traceable to verified candidate information.
- Matching is hybrid, explainable, and versioned instead of being delegated to a single LLM score.
- Job descriptions and uploaded documents are treated as untrusted input.
- Local and in-browser AI are first-class execution options; cloud processing requires explicit configuration and consent.
- The application starts as a modular monolith and evolves only when operational needs justify it.

## Planned stack

- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic
- **Database:** PostgreSQL and pgvector when semantic matching is introduced
- **Frontend:** React, TypeScript, Vite
- **AI:** provider-neutral contracts, browser-local models, local servers, and optional cloud providers
- **Quality:** pytest, Ruff, mypy, pre-commit, and GitHub Actions
- **Infrastructure:** Docker and Docker Compose in a later pull request

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

Document upload endpoints, structured CV extraction, matching, and AI workflows are not
implemented yet.

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
Real model providers, production prompts, automatic CV extraction, and browser inference remain
separate future increments.

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

`PUT` replaces the full profile. On updates, nested entries accept only IDs already owned by that
profile so clients can retain stable identities; omitted IDs are generated by the server. Every
manual submission creates a `user_statement` evidence source, and returned facts expose that
provenance identifier. The API documentation and request schemas are available at
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

