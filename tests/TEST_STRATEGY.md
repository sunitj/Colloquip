# Colloquip Test Strategy & Guidelines

Reference this document when writing or reviewing tests.

## Coverage Targets

| Category | Target | Rationale |
|---|---|---|
| Core domain logic | 90%+ | Engine, observer, energy, agents, models |
| API route handlers | 80%+ | All HTTP endpoints, error paths, validation |
| Tools & integrations | 75%+ | Mock external APIs; verify parsing, error handling |
| Infrastructure (DB, CLI) | 75%+ | Session persistence, schema migrations |
| Display/UI | 60%+ | Smoke tests for rendering, not pixel-perfect |

Overall target: **75-90%** line coverage.

## Test Organization

```
tests/
├── conftest.py               # Shared fixtures and factory functions
├── TEST_STRATEGY.md          # This file
├── test_<module>.py           # Unit tests per source module
├── test_<feature>_validation.py  # Phase validation / integration
├── test_behavioral.py         # Behavioral / property-based tests
├── test_integration_e2e.py    # Full deliberation loop tests
└── test_deployment.py         # Settings, logging, metrics, file existence
```

### Naming Conventions

- Test files: `test_<module_or_feature>.py`
- Test classes: `Test<Component>` (e.g., `TestExportRoutes`, `TestCitationVerifier`)
- Test methods: `test_<behavior_under_test>` (e.g., `test_export_markdown_returns_attachment`)
- Use descriptive names that explain what is being tested and the expected outcome

## Fixtures & Factories

### Reuse `conftest.py` factories

Always check `tests/conftest.py` first for existing factories before creating new helpers:

- `create_post(...)` — Create a `Post` with sensible defaults
- `create_session(...)` — Create a `DeliberationSession`
- `create_agent_config(...)` — Create an `AgentConfig`
- `create_metrics(...)` — Create `ConversationMetrics`
- Shared fixtures: `energy_config`, `energy_calculator`, `observer_config`, `observer`, `trigger_config`, `session`

### API Test Fixtures

For testing API routes, use the `httpx.AsyncClient` + `ASGITransport` pattern:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from colloquip.api import create_app
from colloquip.api.app import SessionManager

@pytest.fixture
def app():
    manager = SessionManager()
    return create_app(session_manager=manager)

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

For route-specific app state (memory_store, watcher_registry, etc.), attach mocks
to `app.state` before creating the client:

```python
@pytest.fixture
def app_with_memory():
    manager = SessionManager()
    app = create_app(session_manager=manager)
    app.state.memory_store = InMemoryStore()
    return app
```

### Database Test Fixtures

Use in-memory SQLite for all database tests:

```python
@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
```

## Test Patterns

### 1. Happy Path First, Then Edge Cases

Every testable function should have at minimum:
1. One happy-path test with valid input
2. One error/edge-case test (invalid input, empty input, not-found)

### 2. Mock External Dependencies at the Boundary

- **External APIs** (PubMed, Semantic Scholar): Mock `httpx.AsyncClient` responses
- **LLM calls**: Use `MockLLM` (already provided in codebase)
- **File system**: Use `tmp_path` fixture or `unittest.mock.patch`
- **Environment variables**: Use `unittest.mock.patch.dict(os.environ, ...)`

Never call real external services in unit tests. Mark tests requiring real APIs
with `@pytest.mark.slow` or `@pytest.mark.integration`.

### 3. Assert on Behavior, Not Implementation

```python
# Good — tests the output
assert result.status_code == 200
assert "hypothesis" in data

# Bad — tests internal implementation details
assert manager._sessions[sid]._status == "running"
```

### 4. Use Specific Assertions

```python
# Good
assert response.status_code == 404
assert "not found" in response.json()["detail"].lower()

# Bad
assert response.status_code != 200
```

### 5. Test Validation at System Boundaries

Focus validation tests on:
- API request validation (Pydantic models, path params)
- UUID parsing (invalid format → 400)
- Missing/empty required fields → 422
- Service not initialized → 503
- Resource not found → 404

### 6. Async Tests

All async test methods work automatically with `asyncio_mode = "auto"` in `pyproject.toml`.
No need for `@pytest.mark.asyncio` decorators.

```python
class TestSomething:
    async def test_async_operation(self):
        result = await some_async_function()
        assert result is not None
```

### 7. Deterministic Tests

- Use fixed seeds where randomness is involved: `seed=42`
- Use fixed UUIDs for reproducibility: `uuid4()` in fixtures, not in assertions
- Avoid time-dependent assertions; mock `time.monotonic()` if needed

## What NOT to Test

- Third-party library internals (FastAPI routing, SQLAlchemy ORM, Pydantic validation)
- Simple pass-through functions with no logic
- Private helper functions unless they contain non-trivial logic
- Mock implementations (`MockLLM`, `MockWebSearchTool`, etc.) — unless verifying mock fidelity

## Test Markers

```python
@pytest.mark.slow          # Requires real LLM API calls
@pytest.mark.integration   # Full deliberation loop / multi-component
```

Run fast tests only: `pytest -m "not slow and not integration"`
Run all: `pytest`

## Pre-Commit Checks

Before committing, the pre-commit hook runs:
1. `ruff check .` — Lint
2. `ruff format --check .` — Format
3. `pytest tests/ -x -q -m "not slow and not integration"` — Fast tests

## Adding Tests for New Features

When implementing a new feature, follow this checklist:

1. **Read this document** for conventions
2. **Check conftest.py** for existing fixtures/factories
3. **Write unit tests** covering: happy path, validation errors, not-found, service-unavailable
4. **For API routes**: Test each endpoint with valid input, invalid input, and missing resources
5. **For tools**: Mock external APIs, test parsing/extraction logic, test error handling
6. **For DB operations**: Use in-memory SQLite, test save/get/list/update cycles
7. **Run the full suite** before committing: `pytest -x`
8. **Check coverage** on your changes: `pytest --cov=colloquip --cov-report=term-missing`
