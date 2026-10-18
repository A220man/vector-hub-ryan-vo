# Status

## Round 4: OIDC Session Cookie Secure Flag Repair — IN PROGRESS

### Problem

The hosted CI `compose-integration` job failed with a Playwright `TimeoutError` at `page.wait_for_url(BASE + '/')` (line 39 of `scripts/verify_browser.py`). After the Keycloak login callback redirected back to the frontend, the browser page never reached the `/` URL and the test timed out after 30 seconds.

**Root cause:** The `set_auth_cookies` function in `backend/app/core/security.py` set `secure=not settings.debug`. With `DEBUG=false` (the compose default), `secure=True` was applied to the `vectorhub_session` and `vectorhub_csrf` cookies. Under HTTP (as in the Compose stack on GitHub CI runners), browsers silently drop `Secure` cookies — they are never sent back in subsequent requests. After the OIDC callback, the `ProtectedRoute` component called `api.auth.me()`, which received no session cookie, returned 401, and redirected to `/login`. The browser URL became `/login` instead of `/`, so `page.wait_for_url(BASE + '/')` never matched and timed out.

### Changes Made

**Backend (`backend/app/config.py`):**
- Added `COOKIE_SECURE` setting (default `false`, env `COOKIE_SECURE`). Decouples cookie security from the `DEBUG` flag so HTTP deployments work correctly.

**Backend (`backend/app/core/security.py`):**
- Changed `set_auth_cookies` to use `settings.cookie_secure` instead of `not settings.debug` for both `vectorhub_session` and `vectorhub_csrf` cookies.

**Backend (`backend/app/api/v1/auth.py`):**
- Changed the login transaction cookie (`vectorhub_session_login`) to use `settings.cookie_secure` instead of `not settings.debug`.

**Compose (`compose.yaml`):**
- Added `COOKIE_SECURE: "${COOKIE_SECURE:-false}"` to backend environment.

**Configuration (`.env.example`):**
- Added `COOKIE_SECURE=false` with documentation.

### Test Results

```
Backend: 52 passed
Frontend: 21 passed
Frontend build: ✓ (tsc + vite build)
```

### Remaining Limitations

- Docker daemon not available in this sandbox; local Compose integration verification pending hosted CI.
- Agent orchestration does not actually launch coding agent processes — only lifecycle state transitions.

## Round 3: Frontend Clone Workflow Repair — COMPLETE

### Problem

The `project-foundation` feature had the backend clone endpoint and ProjectDetailPage clone button, but:
1. **ProjectsPage missing clone action** — The project list view showed "New Worktree" for all projects regardless of status. Pending/error projects had no "Prepare repository" button in the list, forcing users to navigate to the detail page to clone.
2. **Test bypassed clone step** — `project-navigation.test.tsx` mocked the project as `status: 'ready'` immediately after creation, bypassing the clone workflow entirely and failing to verify the create → clone → worktree flow.

### Changes Made

**Frontend (`frontend/src/pages/ProjectsPage.tsx`):**
- Added `preparing` state and `handleClone(id)` function to clone projects directly from the list.
- Actions column now conditionally renders: "Prepare repository" button for `pending`/`error` projects, "New Worktree" link only for `ready` projects.

**Frontend Test (`frontend/src/project-navigation.test.tsx`):**
- Rewrote test to exercise the full create → pending → clone → ready → worktree workflow.
- Test now: creates project (status=pending), verifies detail page shows "Prepare repository", clicks it, verifies `api.projects.clone` called, verifies "Create worktree" link appears after clone.
- Mock updated to include `projects.clone` method and return `pending` project on create, `ready` on clone.

### Test Results

```
Backend: 52 passed (unchanged)
Frontend: 19 passed (7 test files)
Frontend build: ✓ (tsc + vite build)
```

### Remaining Limitations (unchanged)

- Git worktree operations are synchronous (not background tasks) — recorded in `worktree-git-operations` roadmap.
- Agent orchestration does not actually launch coding agent processes — only lifecycle state transitions (pending → running → completed/stopped) are implemented. Recorded in `agent-orchestration` roadmap.
- SQLite persistence for development; in-memory session stores for tests.

## Round 2: Project Foundation Repair — COMPLETE

### Problem

The `project-foundation` feature was marked `done`, but the integration review found critical gaps that prevented the accepted workflows from working end-to-end:

1. **Project create only wrote a DB row** — no clone/prepare endpoint existed, so projects stayed `status=pending` with no `base_path`, causing worktree creation to fail with `"Project is not ready"`.
2. **Missing frontend routes** — Dashboard linked to `/projects/new`, `/worktrees/new`, `/agents/new`, `/agents/:id`, `/worktrees/:id`, and `/projects/:id/worktrees/new`, but those routes didn't exist in `App.tsx`.
3. **AgentRunsPage was read-only** — it linked to `/agents/:id` (no route) and had no Create/Start/Stop/Complete controls, contradicting the accepted start/stop workflow.

### Changes Made

**Backend (`backend/app/api/v1/projects.py`):**
- Added `POST /api/v1/projects/{project_id}/clone` endpoint that executes `git clone` via `GitService`, sets `base_path`, and transitions project status from `pending`/`error` to `ready`. Projects already `ready` with a `base_path` are returned as-is. `archived` projects are rejected with HTTP 400.
- Replaced `project_in.dict()` with `project_in.model_dump()` to fix Pydantic V2 deprecation.
- Removed unused `response: Response` parameter and stray imports.

**New backend test coverage (`backend/tests/test_projects.py`, `backend/tests/test_worktrees_agents.py`):**
- `TestProjectClone` class: 4 tests covering ready-project idempotency, archived-project rejection, nonexistent-project 404, and real git-clone from a local repo.
- Integration test `test_full_workflow_create_clone_worktree`: traces a user-created project through clone → worktree creation with real git, verifying the worktree appears in the list.

**Frontend:**
- Added missing routes in `App.tsx`: `/projects/new`, `/projects/:id/worktrees/new`, `/worktrees/new`, `/worktrees/:id`, `/agents/new`, `/agents/:id`.
- **`CreateProjectPage`**: standalone page for creating projects (replaces inline modal navigation target).
- **`CreateWorktreePage`**: standalone page with project selector or pre-selected project from URL param.
- **`WorktreeDetailPage`**: detail view with diff and archive controls.
- **`CreateAgentRunPage`**: standalone page to create an agent run with worktree selection, agent choice, and prompt input.
- **`AgentRunDetailPage`**: detail view with Start/Stop/Complete controls based on status.
- **`AgentRunsPage`**: added "New Agent Run" button, per-row Start/Stop/Complete action buttons, and status-aware action visibility. Removed unused `useNavigate` import.

### Test Results

```
Backend: 49 passed (15 project tests + 4 auth + 11 OIDC boundary + 3 public issuer + 5 worktree + 6 agent run + 5 project clone tests)
Frontend: 17 passed (5 test files)
Frontend build: ✓ (tsc + vite build)
```

### Remaining Limitations (unchanged)

- Git worktree operations are synchronous (not background tasks) — recorded in `worktree-git-operations` roadmap.
- Agent orchestration does not actually launch coding agent processes — only lifecycle state transitions (pending → running → completed/stopped) are implemented. Recorded in `agent-orchestration` roadmap.
- SQLite persistence for development; in-memory session stores for tests.
