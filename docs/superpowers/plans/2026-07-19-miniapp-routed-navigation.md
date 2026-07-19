# FlatHunter AI Mini App Routed Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-route, local-state Mini App shell with a route-driven Next.js App Router application that has five persistent bottom tabs, structured pages, dedicated listing routes, correct Telegram back navigation, and a documented stacking contract.

**Architecture:** Introduce a shared client-side `MiniAppShell` under one App Router route group. The shell owns Telegram authentication, locale, global modal/toast hosts and exactly one `BottomNavigation`; page components own their own data and render directly from `/search`, `/map`, `/favorites`, `/compare`, `/profile`, and `/listings/[id]`. Existing API functions and domain components are reused, but the old `StageSixShell`, tab state, detail side panel and duplicate primary navigation are removed.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 6, Leaflet, Telegram Mini Apps SDK, Vitest, Testing Library, ESLint.

## Global Constraints

- The five primary tabs are exactly `Пошук`, `Карта`, `Обране`, `Порівняння`, `Профіль`.
- `/` permanently redirects to `/search`.
- `/listings/[id]` is a dedicated route and highlights `Пошук`.
- AI stays inside `/search` and listing details; there is no sixth tab.
- The bottom navigation is the only primary navigation and must stay above ordinary page content.
- Global modals may intentionally appear above navigation.
- Telegram safe-area insets and minimum 44px touch targets are required.
- Existing search, favorite, compare, map, profile, AI and analytics features must not be silently removed.
- Frontend lint, typecheck, tests, production build, Docker build, backend CI and secret scan must remain green.

---

### Task 1: Route shell and redirect

**Files:**
- Create: `miniapp/src/app/(miniapp)/layout.tsx`
- Create: `miniapp/src/components/miniapp-shell.tsx`
- Create: `miniapp/src/components/bottom-navigation.tsx`
- Create: `miniapp/src/components/miniapp-header.tsx`
- Modify: `miniapp/src/app/page.tsx`
- Test: `miniapp/src/components/bottom-navigation.test.tsx`
- Test: `miniapp/src/app/routing-contract.test.ts`

**Interfaces:**
- Produces: `MiniAppShell({ children }: { children: React.ReactNode })`.
- Produces: `BottomNavigation()` using `usePathname()` and real `Link` elements.
- Produces: `MiniAppHeader()` with shared locale and avatar UI.

- [ ] **Step 1: Write failing routing tests**

```tsx
it("maps every primary item to a real route", () => {
  render(<BottomNavigation />);
  expect(screen.getByRole("link", { name: "Пошук" })).toHaveAttribute("href", "/search");
  expect(screen.getByRole("link", { name: "Карта" })).toHaveAttribute("href", "/map");
  expect(screen.getByRole("link", { name: "Обране" })).toHaveAttribute("href", "/favorites");
  expect(screen.getByRole("link", { name: "Порівняння" })).toHaveAttribute("href", "/compare");
  expect(screen.getByRole("link", { name: "Профіль" })).toHaveAttribute("href", "/profile");
});
```

- [ ] **Step 2: Verify RED**

Run: `cd miniapp && npm test -- src/components/bottom-navigation.test.tsx src/app/routing-contract.test.ts`

Expected: FAIL because routed shell files do not exist.

- [ ] **Step 3: Implement route shell**

Use `redirect("/search")` in `miniapp/src/app/page.tsx`. Render `MiniAppHeader`, a `main.miniapp-content`, and one `BottomNavigation` from `MiniAppShell`. Use `aria-current="page"` for the active link and treat `/listings/*` as `/search`.

- [ ] **Step 4: Verify GREEN**

Run: `cd miniapp && npm test -- src/components/bottom-navigation.test.tsx src/app/routing-contract.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add miniapp/src/app miniapp/src/components/miniapp-shell.tsx miniapp/src/components/bottom-navigation.tsx miniapp/src/components/miniapp-header.tsx
git commit -m "refactor: add routed Mini App shell"
```

### Task 2: Stacking contract and route layout styling

**Files:**
- Create: `miniapp/src/app/miniapp-shell.css`
- Modify: `miniapp/src/app/layout.tsx`
- Modify: `miniapp/src/app/globals.css`
- Modify: `miniapp/src/app/search-wizard.css`
- Test: `miniapp/src/app/layering-contract.test.ts`

**Interfaces:**
- Produces CSS variables `--layer-content`, `--layer-sticky`, `--layer-navigation`, `--layer-toast`, `--layer-modal`.
- Bottom navigation uses `var(--layer-navigation)`; search wizard uses `var(--layer-modal)`.

- [ ] **Step 1: Write failing layer tests**

```ts
expect(shellCss).toContain("--layer-navigation");
expect(shellCss).toContain("z-index: var(--layer-navigation)");
expect(shellCss).toContain("padding-bottom: calc(var(--bottom-nav-height)");
```

- [ ] **Step 2: Verify RED**

Run: `cd miniapp && npm test -- src/app/layering-contract.test.ts`

Expected: FAIL because named layer tokens are absent.

- [ ] **Step 3: Implement CSS contract**

Render navigation outside page-local stacking contexts, use `isolation: isolate`, `pointer-events: none` on the navigation wrapper and `pointer-events: auto` on the panel, reserve bottom safe-area space, and keep map/sticky controls below navigation.

- [ ] **Step 4: Verify GREEN**

Run: `cd miniapp && npm test -- src/app/layering-contract.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add miniapp/src/app/miniapp-shell.css miniapp/src/app/layout.tsx miniapp/src/app/globals.css miniapp/src/app/search-wizard.css miniapp/src/app/layering-contract.test.ts
git commit -m "style: define Mini App layer contract"
```

### Task 3: Reusable listing and page-state components

**Files:**
- Create: `miniapp/src/components/page-state.tsx`
- Create: `miniapp/src/components/listing-card.tsx`
- Create: `miniapp/src/components/search-profile-card.tsx`
- Create: `miniapp/src/hooks/use-listing-state.ts`
- Test: `miniapp/src/components/listing-card.test.tsx`
- Test: `miniapp/src/components/page-state.test.tsx`

**Interfaces:**
- Produces `ListingCard({ listing, match, onState })` with detail link `/listings/${listing.id}`.
- Produces `PageState({ kind, title, description, action })` for loading, empty, error and offline states.
- Produces `useListingState()` for favorite, compare and hide mutations with local replacement callbacks.

- [ ] **Step 1: Write failing component tests**

Test that the card links to `/listings/[id]`, exposes favorite/compare actions and never opens a local detail modal.

- [ ] **Step 2: Verify RED**

Run: `cd miniapp && npm test -- src/components/listing-card.test.tsx src/components/page-state.test.tsx`

Expected: FAIL because reusable components do not exist.

- [ ] **Step 3: Implement focused components**

Move formatting, visual placeholder, analysis chips and action controls out of `listing-feed.tsx`. Keep API mutation errors recoverable and visible.

- [ ] **Step 4: Verify GREEN**

Run: `cd miniapp && npm test -- src/components/listing-card.test.tsx src/components/page-state.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add miniapp/src/components/page-state.tsx miniapp/src/components/listing-card.tsx miniapp/src/components/search-profile-card.tsx miniapp/src/hooks/use-listing-state.ts
git commit -m "refactor: extract routed listing components"
```

### Task 4: Search home route

**Files:**
- Create: `miniapp/src/app/(miniapp)/search/page.tsx`
- Create: `miniapp/src/components/search-home.tsx`
- Create: `miniapp/src/app/search-page.css`
- Test: `miniapp/src/components/search-home.test.tsx`

**Interfaces:**
- Consumes: `fetchDashboard`, `fetchSearchProfiles`, `fetchMatches`, `SearchWizard`, `AIAssistantWorkspace`, `ListingCard`, `SearchProfileCard`, `PageState`.
- Produces the structured `/search` page and owns only search-wizard modal state.

- [ ] **Step 1: Write failing search-home tests**

Cover heading, create-search action, active profiles, recent matches, compact stats, AI section, loading, empty and retry states.

- [ ] **Step 2: Verify RED**

Run: `cd miniapp && npm test -- src/components/search-home.test.tsx`

Expected: FAIL because `/search` composition does not exist.

- [ ] **Step 3: Implement `/search`**

Remove the marketing hero, orbit, demo system dashboard and all duplicate primary navigation. Keep a compact header and coherent sections driven by actual API responses.

- [ ] **Step 4: Verify GREEN**

Run: `cd miniapp && npm test -- src/components/search-home.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add miniapp/src/app/'(miniapp)'/search miniapp/src/components/search-home.tsx miniapp/src/app/search-page.css
git commit -m "feat: build routed search home"
```

### Task 5: Map, favorites and compare routes

**Files:**
- Create: `miniapp/src/app/(miniapp)/map/page.tsx`
- Create: `miniapp/src/app/(miniapp)/favorites/page.tsx`
- Create: `miniapp/src/app/(miniapp)/compare/page.tsx`
- Create: `miniapp/src/components/favorites-workspace.tsx`
- Create: `miniapp/src/components/comparison-workspace.tsx`
- Modify: `miniapp/src/components/map-workspace.tsx`
- Test: `miniapp/src/components/favorites-workspace.test.tsx`
- Test: `miniapp/src/components/comparison-workspace.test.tsx`
- Test: `miniapp/src/components/map-workspace.test.tsx`

**Interfaces:**
- Favorites fetches `fetchListings({ favorites: true })` and renders `ListingCard`.
- Compare fetches `fetchListings({ compared: true })`, supports 2–5 items, and renders mobile comparison cards plus AI comparison.
- Map keeps its filters and map context but links selected listings to `/listings/[id]`.

- [ ] **Step 1: Write failing route workspace tests**

Cover success, empty, error, remove action and dedicated detail links.

- [ ] **Step 2: Verify RED**

Run: `cd miniapp && npm test -- src/components/favorites-workspace.test.tsx src/components/comparison-workspace.test.tsx src/components/map-workspace.test.tsx`

Expected: FAIL because routed workspaces do not exist.

- [ ] **Step 3: Implement routes**

Remove `workspace-tabs`, local primary tab state and detail modal behavior. Keep page-specific filters only.

- [ ] **Step 4: Verify GREEN**

Run: `cd miniapp && npm test -- src/components/favorites-workspace.test.tsx src/components/comparison-workspace.test.tsx src/components/map-workspace.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add miniapp/src/app/'(miniapp)'/map miniapp/src/app/'(miniapp)'/favorites miniapp/src/app/'(miniapp)'/compare miniapp/src/components/favorites-workspace.tsx miniapp/src/components/comparison-workspace.tsx miniapp/src/components/map-workspace.tsx
git commit -m "feat: add routed map favorites and compare pages"
```

### Task 6: Profile route and shared app context

**Files:**
- Create: `miniapp/src/app/(miniapp)/profile/page.tsx`
- Create: `miniapp/src/components/miniapp-context.tsx`
- Modify: `miniapp/src/components/profile-workspace.tsx`
- Modify: `miniapp/src/components/miniapp-shell.tsx`
- Modify: `miniapp/src/components/miniapp-header.tsx`
- Test: `miniapp/src/components/profile-workspace.test.tsx`

**Interfaces:**
- Produces `useMiniApp()` with Telegram user, locale, connection state and locale setter.
- Profile consumes shared context and existing search-profile/notification APIs.

- [ ] **Step 1: Write failing profile tests**

Cover Telegram identity, locale, notifications, quiet hours, search-profile management and auth error states.

- [ ] **Step 2: Verify RED**

Run: `cd miniapp && npm test -- src/components/profile-workspace.test.tsx`

Expected: FAIL until context and route integration are complete.

- [ ] **Step 3: Implement profile route**

Remove callback-based primary navigation from `ProfileWorkspace`. Keep user-facing settings and demote developer diagnostics.

- [ ] **Step 4: Verify GREEN**

Run: `cd miniapp && npm test -- src/components/profile-workspace.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add miniapp/src/app/'(miniapp)'/profile miniapp/src/components/miniapp-context.tsx miniapp/src/components/profile-workspace.tsx miniapp/src/components/miniapp-shell.tsx miniapp/src/components/miniapp-header.tsx
git commit -m "feat: add routed profile page"
```

### Task 7: Listing details and Telegram Back Button

**Files:**
- Create: `miniapp/src/app/(miniapp)/listings/[id]/page.tsx`
- Create: `miniapp/src/components/listing-details.tsx`
- Create: `miniapp/src/components/telegram-back-button.tsx`
- Create: `miniapp/src/app/listing-details.css`
- Test: `miniapp/src/components/listing-details.test.tsx`
- Test: `miniapp/src/components/telegram-back-button.test.tsx`

**Interfaces:**
- `ListingDetails({ listingId }: { listingId: string })` fetches listing and analytics independently.
- `TelegramBackButton()` shows only on `/listings/*`, calls router back when possible, otherwise `/search`.

- [ ] **Step 1: Write failing details tests**

Cover loading, not found, recoverable API error, favorite, compare, analytics partial failure, original source link and active search tab.

- [ ] **Step 2: Verify RED**

Run: `cd miniapp && npm test -- src/components/listing-details.test.tsx src/components/telegram-back-button.test.tsx`

Expected: FAIL because dedicated details route is absent.

- [ ] **Step 3: Implement details route**

Reuse `ListingAnalysisPanel`, add robust image placeholder, facts, description, amenities, source information and AI questions. Analytics failures must not block core details.

- [ ] **Step 4: Verify GREEN**

Run: `cd miniapp && npm test -- src/components/listing-details.test.tsx src/components/telegram-back-button.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add miniapp/src/app/'(miniapp)'/listings miniapp/src/components/listing-details.tsx miniapp/src/components/telegram-back-button.tsx miniapp/src/app/listing-details.css
git commit -m "feat: add routed listing details"
```

### Task 8: Remove old shell, migrate styles and verify whole application

**Files:**
- Delete: `miniapp/src/components/stage-six-shell.tsx`
- Retire or simplify: `miniapp/src/components/app-shell.tsx`
- Refactor or delete: `miniapp/src/components/listing-feed.tsx`
- Modify: `miniapp/src/app/stage-six.css`
- Modify: relevant existing tests that assert the old shell
- Create: `miniapp/src/app/not-found.tsx`
- Test: `miniapp/src/app/route-smoke.test.tsx`

**Interfaces:**
- No local state represents the primary route.
- No `stage-six-switch`, `workspace-tabs` or detail modal remains in the production route tree.

- [ ] **Step 1: Write failing migration/smoke test**

Assert six route patterns, one bottom navigation, no old switchers, details links, active states and `/` redirect contract.

- [ ] **Step 2: Verify RED**

Run: `cd miniapp && npm test -- src/app/route-smoke.test.tsx`

Expected: FAIL while legacy production wrappers remain.

- [ ] **Step 3: Remove legacy routing logic and migrate remaining styles**

Delete unused wrappers and stale state-only tests. Keep only components still used by routed pages.

- [ ] **Step 4: Run full verification**

Run:

```bash
cd miniapp
npm run lint
npm run typecheck
npm test
npm run build
npm audit --audit-level=high
```

Expected: all commands exit 0.

Run repository CI and verify backend, frontend, containers and secret scan all succeed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: complete routed Mini App navigation"
```

### Task 9: PR, merge and production deployment

**Files:**
- No product-code changes unless review or CI finds a defect.

- [ ] **Step 1: Review exact diff**

Verify there are no temporary workflows, no duplicate primary navigation and no accidental backend changes.

- [ ] **Step 2: Create PR and wait for clean CI**

PR title: `Rewrite Mini App with routed navigation`.

- [ ] **Step 3: Merge only after all required checks pass**

Use a merge commit and record the SHA.

- [ ] **Step 4: Verify Vercel production deployment**

Check the merged commit until the `Vercel` status is `success`; do not report deployment as complete while it is pending or rate-limited.
