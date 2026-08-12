# Contributing to JobHunter AI

Thank you for helping build JobHunter AI. The project favors small, reviewable changes and explicit trade-offs.

## Workflow

1. Start from `main`.
2. Create a short-lived `feature/...` or `fix/...` branch.
3. Keep the pull request focused on one coherent outcome.
4. Add or update tests with behavioral changes.
5. Run the local quality checks.
6. Explain architectural decisions and privacy implications in the pull request.

Use Conventional Commits when practical:

```text
feat: add candidate profile endpoint
fix: reject unsupported document media types
test: cover mandatory requirement penalties
docs: explain browser AI privacy model
chore: update development tooling
```

## Local development

Install dependencies:

```bash
uv sync --directory backend --all-groups
pnpm --dir frontend install
pnpm --dir frontend exec playwright install chromium
```

Start PostgreSQL and apply migrations before running integration tests:

```bash
docker compose up -d --wait database
uv run --directory backend alembic upgrade head
```

Set `JOBHUNTER_TEST_DATABASE_URL` to a disposable PostgreSQL database when you want the local
pytest run to include destructive migration round-trip tests. Never point it at shared data.

Run checks:

```bash
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
uv run --directory backend mypy src tests
uv run --directory backend pytest
pnpm --dir frontend check
```

Develop shared UI components in Storybook:

```bash
pnpm --dir frontend storybook
```

## Pull request checklist

- The change is inside the agreed scope.
- Tests cover meaningful success and failure paths.
- Ruff, mypy, pytest, ESLint, TypeScript, Vitest, and the production build pass.
- No secret, CV, job application, or personal information is committed.
- External content is treated as untrusted.
- New dependencies have a concrete need and documented trade-off.
- Public documentation is updated when behavior changes.

## Data and AI fixtures

Use fictional or irreversibly anonymized fixtures. Generated CV text must be backed by fixture facts, and evaluations must never depend on undocumented provider behavior.

