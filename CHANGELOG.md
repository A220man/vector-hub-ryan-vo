# Changelog

All notable changes to this project will be documented in this file.

## [1.0.2] - 2026-10-18

### Fixed
- **Frontend clone workflow** — Added "Prepare repository" button to ProjectsPage for pending/error projects; "New Worktree" link now only shows for ready projects. ProjectsPage now exposes the clone action directly in the list view.
- **Project navigation test** — Updated `project-navigation.test.tsx` to test the full create → pending → clone → ready → worktree workflow instead of mocking projects as ready immediately after creation. The test now exercises the clone button and verifies the worktree link appears after preparation.

### Tests
- Frontend: 19 passed (2 new tests in project-navigation.test.tsx covering the clone workflow)

## [1.0.1] - 2026-10-18

### Fixed
- **Project clone/prepare endpoint** — Added `POST /api/v1/projects/{project_id}/clone` to clone the git repository via `GitService`, set `base_path`, and transition project from `pending`/`error` to `ready`. Without this, projects stayed `pending` and worktree creation failed with "Project is not ready".
- **Frontend route gaps** — Added missing routes in `App.tsx`: `/projects/new`, `/projects/:id/worktrees/new`, `/worktrees/new`, `/worktrees/:id`, `/agents/new`, `/agents/:id`. Dashboard links and navigation now work end-to-end.
- **Agent run controls** — `AgentRunsPage` now has "New Agent Run" button, per-row Start/Stop/Complete action buttons, and status-aware visibility. `AgentRunDetailPage` provides the detail view with the same controls. Previously the page was read-only and linked to non-existent `/agents/:id`.
- **Pydantic V2 deprecation** — Replaced `project_in.dict()` with `project_in.model_dump()` in `update_project`.
- **Unused imports** — Removed stray `useNavigate` from `AgentRunsPage` and duplicate imports in `projects.py`.

### Added
- **CreateProjectPage** — Standalone page for creating projects with form validation.
- **CreateWorktreePage** — Standalone page with project selector (or pre-selected via URL).
- **WorktreeDetailPage** — Detail view showing diff, status, path, and archive action.
- **CreateAgentRunPage** — Standalone page with worktree selection, agent dropdown, and prompt textarea.
- **AgentRunDetailPage** — Detail view with Start/Stop/Complete controls.
- **Test coverage** — 5 new backend tests (`TestProjectClone` class + integration test `test_full_workflow_create_clone_worktree`) covering the create → clone → worktree workflow with a real git repo.

### Tests
- Backend: 49 passed (+5 from 1.0.0)
- Frontend: 17 passed (unchanged count; new components covered by existing integration test)

## [1.0.0] - 2026-10-18

### Added
- Initial release of Vector Hub
- FastAPI backend with SQLAlchemy + SQLite
- React + TypeScript + Vite frontend
- Project management (CRUD, status lifecycle)
- Git worktree operations (create, list, delete, diff)
- Agent run orchestration (lifecycle, status transitions)
- OIDC/PKCE authentication via Keycloak
- Role-based access control (viewer, operator, admin)
- Docker Compose with Keycloak, PostgreSQL, backend, frontend
- CI/CD workflow with pytest, vitest, Docker builds
- Portfolio.json metadata

### Security
- HttpOnly SameSite cookies with CSRF protection
- Demo mode restricted to localhost
- Redacted LLM error handling
- No token persistence in localStorage

### Tests
- 44 backend tests (models, API, auth, PKCE, sessions, OIDC boundary, public issuer)
- 16 frontend tests (App, API client, login boundary, client boundary)

### Fixed
- frontend/package.json author email (Ryan Vo <ryandtvo@gmail.com>) per contract
- Dockerfile paths moved to backend/Dockerfile and frontend/Dockerfile
- DATABASE_URL uses absolute path (sqlite:////data/vectorhub.db) for container persistence
- OIDC issuer separation: internal (Docker network) vs external (browser-facing) URLs
- Keycloak healthcheck uses bash /dev/tcp instead of curl for image compatibility
- nginx.conf pid directive for non-root user startup (/var/cache/nginx/nginx.pid)
- Keycloak realm audience mapper for vector-hub-api access token validation
- CI workflow adds compose integration test with OIDC login initiation test, authenticated mutations, and database persistence verification
- AgentRun model: fixed column types (Integer for token/cost fields), added created_at/updated_at timestamps
- compose.yaml depends_on.postgres mapping with service_healthy condition
- nginx.conf auth location rewrite to map /auth/ to /api/v1/auth/ backend routes
- CI workflow OIDC_CLIENT_SECRET aligned with Keycloak realm client secret
- README.md author email footer (Ryan Vo <ryandtvo@gmail.com>)
- compose.yaml DEMO_MODE now uses variable interpolation (${DEMO_MODE:-false}) for CI override
- CI workflow tests OIDC login initiation endpoint (real authorization URL generation)