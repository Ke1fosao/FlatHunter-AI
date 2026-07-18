# Responsive Search Wizard Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the unstyled `SearchWizard` into a polished, accessible responsive modal on desktop and a safe-area-aware bottom sheet on mobile.

**Architecture:** Keep the existing API payload and three-step wizard logic unchanged. Add one globally imported stylesheet dedicated to the wizard, and extend the component only with modal lifecycle behavior: backdrop close, Escape close, inside-click isolation, and body scroll locking with cleanup.

**Tech Stack:** Next.js 16, React 19, TypeScript 6, CSS, Vitest, Testing Library, jsdom.

## Global Constraints

- Do not change search-profile fields, payloads, API calls, wizard steps, or success behavior.
- Desktop/tablet uses a centered modal; screens below 680px use a bottom sheet.
- Dialog maximum height is `90dvh`; header and footer remain visible while content scrolls.
- Mobile bottom padding must include `env(safe-area-inset-bottom)`.
- Backdrop click and Escape close the wizard; clicks inside never close it.
- Opening locks body scrolling and unmount restores the exact previous `document.body.style.overflow` value.
- Touch targets are at least 44px and focus-visible rings remain visible.
- Full frontend lint, typecheck, Vitest, production build, audit, repository CI, container build and secret scan must pass.

---

### Task 1: Modal lifecycle regression tests

**Files:**
- Create: `miniapp/src/components/search-wizard.test.tsx`
- Modify: `miniapp/src/components/search-wizard.tsx`

**Interfaces:**
- Consumes: `SearchWizard({ onClose, onCreated })`.
- Produces: backdrop click, Escape close, inside-click isolation, and scroll-lock cleanup behavior.

- [ ] **Step 1: Write failing component tests**

Create tests that mock `@/lib/api`, render `SearchWizard`, then assert:

```tsx
fireEvent.click(screen.getByTestId("wizard-backdrop"));
expect(onClose).toHaveBeenCalledTimes(1);

fireEvent.click(screen.getByRole("dialog"));
expect(onClose).not.toHaveBeenCalled();

fireEvent.keyDown(document, { key: "Escape" });
expect(onClose).toHaveBeenCalledTimes(1);

expect(document.body.style.overflow).toBe("hidden");
unmount();
expect(document.body.style.overflow).toBe(previousOverflow);
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `cd miniapp && npm test -- src/components/search-wizard.test.tsx`

Expected: FAIL because the backdrop lacks a test id/click handler, Escape is not handled, and body overflow is unchanged.

- [ ] **Step 3: Implement modal lifecycle behavior**

In `search-wizard.tsx`:

```tsx
useEffect(() => {
  const previousOverflow = document.body.style.overflow;
  document.body.style.overflow = "hidden";
  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape") onClose();
  };
  document.addEventListener("keydown", handleKeyDown);
  return () => {
    document.removeEventListener("keydown", handleKeyDown);
    document.body.style.overflow = previousOverflow;
  };
}, [onClose]);
```

Add `data-testid="wizard-backdrop"` and close only when `event.target === event.currentTarget`; stop propagation inside the dialog.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run: `cd miniapp && npm test -- src/components/search-wizard.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add miniapp/src/components/search-wizard.tsx miniapp/src/components/search-wizard.test.tsx
git commit -m "fix: add search wizard modal lifecycle"
```

### Task 2: Dedicated responsive wizard stylesheet

**Files:**
- Create: `miniapp/src/app/search-wizard.css`
- Modify: `miniapp/src/app/layout.tsx`
- Create: `miniapp/src/app/layout-styles.test.ts`

**Interfaces:**
- Consumes: existing `.wizard-*`, `.button`, and token classes.
- Produces: globally loaded desktop modal and mobile bottom-sheet presentation.

- [ ] **Step 1: Write failing global-style import test**

Read `layout.tsx` in a Vitest node test and assert:

```ts
expect(layoutSource).toContain('import "./search-wizard.css";');
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `cd miniapp && npm test -- src/app/layout-styles.test.ts`

Expected: FAIL because `search-wizard.css` is not imported.

- [ ] **Step 3: Add the stylesheet and import**

Implement:

- fixed full-screen backdrop with dimming and blur;
- centered desktop sheet, `width: min(720px, calc(100vw - 32px))`, `max-height: 90dvh`;
- sticky header/footer and scrollable form body;
- two-column `.wizard-grid`, collapsing below 680px;
- consistent inputs/select/textarea, option chips, progress, review cards, errors, disabled and focus-visible states;
- mobile bottom sheet with rounded top corners, `width: 100%`, safe-area footer padding and entry animation;
- `prefers-reduced-motion` override.

Import it after `stage-six.css` in `layout.tsx` so wizard rules are globally available.

- [ ] **Step 4: Run focused tests and frontend quality gates**

Run:

```bash
cd miniapp
npm test -- src/app/layout-styles.test.ts src/components/search-wizard.test.tsx
npm run lint
npm run typecheck
npm test
npm run build
npm audit --audit-level=high
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add miniapp/src/app/search-wizard.css miniapp/src/app/layout.tsx miniapp/src/app/layout-styles.test.ts
git commit -m "style: add responsive search wizard modal"
```

### Task 3: Repository verification and delivery

**Files:**
- Review: all files changed on `fix/search-wizard-responsive-modal`

**Interfaces:**
- Produces: merge-ready PR with no temporary workflows or unrelated changes.

- [ ] **Step 1: Review exact diff against the approved specification**

Verify the diff changes only the design spec, implementation plan, wizard component/tests, dedicated stylesheet, and root layout import.

- [ ] **Step 2: Run standard GitHub CI on a pull request**

Expected checks:

- `CI / backend`
- `CI / frontend`
- `CI / containers`
- `CI / secret-scan`

All must conclude `success`.

- [ ] **Step 3: Merge only after green CI**

Merge with expected head SHA to prevent merging a moved branch.

- [ ] **Step 4: Verify Vercel status honestly**

Check the merge commit status. Report deployment as successful only if Vercel returns `success`; otherwise report the exact platform limitation and available preview state.
