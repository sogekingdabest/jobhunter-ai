# JobHunter AI

JobHunter AI is an open-source application for structuring a master CV, evaluating job opportunities, and tailoring resumes without inventing experience, skills, certifications, or achievements.

> [!NOTE]
> The project is in its foundation phase. Product workflows are not implemented yet.

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
- linting, formatting, static typing, production builds, and CI.

PostgreSQL, Docker, API integration, and product domains are intentionally outside this foundation.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js 24 LTS
- pnpm 11

## Setup

```bash
uv sync --directory backend --all-groups
pnpm --dir frontend install
```

Copy `.env.example` to `.env` if you want to override local settings. Never commit `.env` files.

## Run the API

```bash
uv run --directory backend uvicorn jobhunter.main:app --reload
```

The API is then available at `http://127.0.0.1:8000`; its health endpoint is `GET /health`.

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

