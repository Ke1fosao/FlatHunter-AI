# Responsive Search Wizard Modal Design

## Problem

`SearchWizard` is rendered in the production Mini App, but its `.wizard-*` styles are not part of the globally loaded stylesheet bundle. The dialog therefore appears as unstyled form controls at the bottom-left of the page and is effectively unusable.

## Goal

Make the existing search wizard look and behave like a polished Telegram Mini App flow on desktop and mobile without changing the search-profile API contract or the three-step business logic.

## Layout

- Desktop and tablet: centered modal card over a full-screen dimmed and blurred backdrop.
- Mobile and Telegram WebView: bottom sheet spanning the viewport width, with rounded top corners and safe-area padding.
- Maximum dialog height: 90dvh. Only the dialog body scrolls; the page behind remains locked.
- Form fields use two columns when space allows and one column below 680px.
- Header and footer remain visible while the body scrolls.
- The footer contains the existing Back and Continue/Create actions with touch targets of at least 44px.

## Interaction

- The close button closes the wizard.
- Clicking the backdrop outside the sheet closes the wizard.
- Pressing Escape closes the wizard in browser preview and desktop Telegram.
- Clicking inside the sheet never triggers backdrop close.
- Opening the wizard locks document scrolling; closing or unmounting restores the previous overflow value.
- Existing mode switching, step navigation, natural-language parsing, validation, submission, error states and success callback remain unchanged.

## Styling

- Add a dedicated globally imported `search-wizard.css` rather than duplicating wizard styles inside stage-specific CSS.
- Reuse existing design tokens (`--surface`, `--surface-soft`, `--border`, `--text`, `--muted`, `--accent`, `--accent-text`, `--shadow`).
- Add clear focus-visible rings, disabled states, selected option-chip states and readable error styling.
- Inputs, selects and textarea use consistent spacing, typography and contrast in light and dark themes.
- Respect `env(safe-area-inset-bottom)` on mobile.
- Reduce motion when `prefers-reduced-motion: reduce` is active.

## Accessibility

- Keep `role="dialog"`, `aria-modal="true"` and the current labelled title.
- Close button retains an accessible label.
- Keyboard focus indicators must be visible.
- Escape support must not interfere with form controls.
- Backdrop remains presentational and is not focusable.

## Testing

- Regression test verifies the dedicated stylesheet is imported by the root layout.
- Component tests verify backdrop click closes, inside click does not close, Escape closes and body scroll is restored.
- Existing search wizard tests continue to pass.
- Full frontend lint, typecheck, Vitest, production build and audit must pass, followed by the repository CI and container build.

## Scope

In scope: responsive modal layout, global style loading, backdrop/Escape close, scroll locking and regression tests.

Out of scope: changing search fields, API payloads, adding new wizard steps, redesigning unrelated screens or changing the floating create-search button.