# Mini App Full Functionality Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the deployed Telegram Mini App actually work end-to-end and restore every user-facing capability that was lost during the routed-navigation rewrite.

**Architecture:** The browser will always call a same-origin `/api/v1` gateway implemented as a hardened Next.js route handler. That gateway forwards to the server-only Django backend URL, preserving session and CSRF cookies without cross-site browser cookie failures. Routed pages stay, but they regain cluster-aware listings, sources, notes, complete search-profile CRUD, persisted notification preferences, filters, map tools, AI actions, analysis, and robust auth/error states.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 6, Django 6 + DRF session auth, Telegram Mini Apps SDK, Vitest, Testing Library, GitHub Actions, Vercel, Render.

## Global Constraints

- Keep `/search`, `/map`, `/favorites`, `/compare`, `/profile`, and `/listings/[id]`.
- Keep exactly one persistent bottom navigation.
- Browser code must not depend on cross-site Django cookies.
- All mutating requests must send the CSRF token returned by Telegram auth.
- Search, favorites, comparison, details, map, AI and profile management must be cluster-aware.
- One cluster occupies one comparison slot; comparison maximum is 4.
- Notification settings must persist in Django, never only in localStorage.
- Browser preview must show an explicit Telegram-auth state instead of firing protected requests and reporting generic failures.
- Every production-code change starts with a failing test.
- Final merge requires frontend, backend, containers, secret scan and production deployment success.

---

### Task 1: Production backend reachability diagnostic

**Files:**
- Create temporarily: `.github/workflows/miniapp-production-diagnostic.yml`
- Delete after evidence is recorded: `.github/workflows/miniapp-production-diagnostic.yml`

**Interfaces:**
- Produces evidence for `https://flathunter-ai-backend.onrender.com/health/live/`, `/health/ready/`, and `/api/v1/health/`.

- [ ] Write a diagnostic job that uses `curl --fail-with-body --max-time 90` for all three endpoints and uploads headers/body as an artifact.
- [ ] Run it once and record exact HTTP status, redirects and response body.
- [ ] Remove the workflow before the final PR review.

### Task 2: Same-origin API gateway and CSRF-aware client

**Files:**
- Create: `miniapp/src/lib/api-client.ts`
- Create: `miniapp/src/lib/server-api-proxy.ts`
- Create: `miniapp/src/app/api/v1/[...path]/route.ts`
- Create: `miniapp/src/lib/api-client.test.ts`
- Create: `miniapp/src/lib/server-api-proxy.test.ts`
- Modify: `miniapp/src/lib/api.ts`
- Modify: `miniapp/src/lib/map-api.ts`
- Modify: `miniapp/src/lib/analysis-api.ts`
- Modify: `miniapp/src/lib/cluster-api.ts`
- Modify: `miniapp/next.config.ts`
- Modify: `.env.example`
- Modify: `docs/cloud-hosting.md`

**Interfaces:**
- Produces `apiRequest<T>(endpoint, options)` and `setCsrfToken(token)`.
- Produces `proxyApiRequest(request, path)` for all route methods.
- Browser base is always `/api/v1`; backend target uses `BACKEND_API_URL` server-side.

- [ ] Write failing tests proving browser requests remain same-origin and mutating calls include the auth-provided CSRF token.
- [ ] Write failing tests proving the proxy rejects non-HTTP(S) targets, forwards method/query/body/cookie/CSRF, forwards every `Set-Cookie`, and normalizes backend-unavailable errors to 502.
- [ ] Verify RED in CI.
- [ ] Implement the shared client and route handler.
- [ ] Replace duplicated fetch/CSRF code in all API modules.
- [ ] Verify GREEN and run all frontend tests.

### Task 3: Deterministic Telegram authentication gate

**Files:**
- Modify: `miniapp/src/components/miniapp-context.tsx`
- Modify: `miniapp/src/components/miniapp-shell.tsx`
- Create: `miniapp/src/components/auth-gate.tsx`
- Create: `miniapp/src/components/auth-gate.test.tsx`
- Create: `miniapp/src/components/miniapp-context.test.tsx`
- Modify: routed workspaces to wait for authenticated state.

**Interfaces:**
- Produces `authStatus: "booting" | "preview" | "authenticating" | "authenticated" | "error"`.
- Produces `retryAuthentication()` and `isAuthenticated`.

- [ ] Write failing tests for Telegram auth success, invalid initData, preview mode, offline mode and retry.
- [ ] Verify RED.
- [ ] Store the returned CSRF token before protected requests start.
- [ ] Dispatch the authenticated event only after context state is ready.
- [ ] Prevent all protected page fetches before authentication.
- [ ] Verify GREEN.

### Task 4: Full search-profile CRUD and persisted notification settings

**Files:**
- Modify: `miniapp/src/lib/api.ts`
- Modify: `miniapp/src/components/search-wizard.tsx`
- Create: `miniapp/src/components/search-profile-manager.tsx`
- Create: `miniapp/src/components/search-profile-manager.test.tsx`
- Modify: `miniapp/src/components/search-home.tsx`
- Modify: `miniapp/src/components/profile-workspace.tsx`
- Modify: `miniapp/src/app/routed-pages.css`

**Interfaces:**
- Produces full `SearchProfile` and `NotificationPreference` types.
- Produces `fetchSearchProfile`, `updateSearchProfile`, `deleteSearchProfile`, `activateSearchProfile`, `pauseSearchProfile`.
- SearchWizard accepts `profile?: SearchProfile` and calls create or PATCH.

- [ ] Write failing tests for create, edit, pause, activate, delete confirmation and backend notification persistence.
- [ ] Verify RED.
- [ ] Extend API types/functions.
- [ ] Convert SearchWizard to create/edit mode with all existing profile fields.
- [ ] Replace localStorage notification UI with the selected profile’s backend `notification_preference`.
- [ ] Verify GREEN.

### Task 5: Restore cluster-aware search results, sources and notes

**Files:**
- Create: `miniapp/src/components/cluster-listing-card.tsx`
- Create: `miniapp/src/components/search-results-workspace.tsx`
- Create: `miniapp/src/components/search-results-workspace.test.tsx`
- Modify: `miniapp/src/components/search-home.tsx`
- Modify: `miniapp/src/components/listing-details.tsx`
- Create: `miniapp/src/components/cluster-note-editor.tsx`
- Create: `miniapp/src/components/cluster-note-editor.test.tsx`
- Reuse: `miniapp/src/components/cluster-sources.tsx`
- Reuse: `miniapp/src/lib/cluster-api.ts`

**Interfaces:**
- Search filters: profile, min Match Score, ordering, city, district, rooms, min/max price and text.
- Details load `fetchListingCluster(cluster_id, profile_id)` when clustered.
- Notes persist through `setClusterState(..., { note })`.

- [ ] Write failing tests for one-card-per-cluster, source count, price range, filters, hide/favorite/compare, source list and note persistence.
- [ ] Verify RED.
- [ ] Implement routed cluster-aware cards and results.
- [ ] Add cluster sources and notes to `/listings/[id]`.
- [ ] Verify GREEN.

### Task 6: Favorites and comparison parity

**Files:**
- Modify: `miniapp/src/components/favorites-workspace.tsx`
- Modify: `miniapp/src/components/comparison-workspace.tsx`
- Create/modify tests for both components.

**Interfaces:**
- Favorites supports search, city, district, rooms, price range and ordering.
- Comparison supports 2–4 unique cluster-aware items and optional profile-aware AI comparison.

- [ ] Write failing tests for full filters, cluster state updates, comparison limit 4, AI profile selector and remove behavior.
- [ ] Verify RED.
- [ ] Implement parity.
- [ ] Verify GREEN.

### Task 7: Map and listing-details hardening

**Files:**
- Modify: `miniapp/src/components/map-workspace.tsx`
- Modify: `miniapp/src/components/important-place-panel.tsx`
- Modify: `miniapp/src/components/listing-details.tsx`
- Modify/add tests.

**Interfaces:**
- Map keeps profile, Match filter, favorites, important-place add/geocode/delete and listing route links.
- Listing details retain core data when analysis/AI/source-detail requests fail independently.

- [ ] Write failing tests for map important places, profile-less empty state, marker detail links and partial API failures.
- [ ] Verify RED.
- [ ] Implement independent loading/error boundaries and retry actions.
- [ ] Verify GREEN.

### Task 8: Production smoke suite and clean merge

**Files:**
- Create: `miniapp/src/app/full-route-smoke.test.tsx`
- Create: `miniapp/src/lib/api-contract.test.ts`
- Modify: CI only if a permanent smoke step is justified.
- Delete all temporary diagnostic workflows/files.

**Interfaces:**
- Covers auth → profiles → search → favorite → compare → details → map → AI using deterministic mocked HTTP contracts.

- [ ] Write the end-to-end route contract tests and verify they fail before missing integrations are added.
- [ ] Make them pass without bypassing auth.
- [ ] Run `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, `npm audit --audit-level=high`.
- [ ] Run backend quality gates, both Docker builds and Gitleaks.
- [ ] Review exact diff for temporary workflows, fake local-only persistence and unused legacy shells.
- [ ] Merge only after all checks are green.
- [ ] Verify Vercel production status is `success` and backend health is reachable through the deployed same-origin `/api/v1/health/` route.
