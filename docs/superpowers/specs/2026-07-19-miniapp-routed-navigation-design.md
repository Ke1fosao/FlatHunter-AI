# FlatHunter AI Mini App routed navigation redesign

## Status

Approved design direction for replacing the current single-page state-driven Mini App with a route-driven application shell.

## Problem

The current Mini App renders most product surfaces from a single `/` route and switches between them with local React state. This creates several structural problems:

- the bottom navigation is not the only navigation mechanism;
- a second switcher duplicates the same sections;
- browser history and Telegram Back Button cannot represent user movement correctly;
- deep links to a map, favorites, comparison, profile or a listing do not exist;
- active navigation depends on manually synchronized component state;
- page-specific loading, error and empty states are mixed together;
- the bottom navigation can appear below maps, modals or other stacking contexts.

The redesign must remove the old state-based shell instead of layering new routes on top of it.

## Product decisions

The five bottom-navigation items are the only primary navigation controls:

1. `Пошук`
2. `Карта`
3. `Обране`
4. `Порівняння`
5. `Профіль`

The `Пошук` item is the application home. AI is not a sixth navigation item; it appears as a structured section inside the search home and inside listing details where relevant.

Listing details open on their own route rather than in a modal or local state panel.

## Route map

| Route | Purpose |
| --- | --- |
| `/` | Permanent redirect to `/search` |
| `/search` | Search home, search profiles, recent matches, compact statistics, AI assistant section and create-search action |
| `/map` | Full map workspace with filters and a selected-listing preview |
| `/favorites` | Saved listings, sorting, filtering and empty state |
| `/compare` | Comparison workspace for selected listings |
| `/profile` | Telegram user profile, language, notification settings, search-profile management and app settings |
| `/listings/[id]` | Dedicated listing details page |

Unsupported routes use the standard Next.js not-found surface and provide a clear action back to `/search`.

## Application architecture

### Route group and shared layout

The five primary pages and listing details live under one App Router route group with a shared layout. The shared layout owns:

- Telegram initialization;
- authenticated-user context;
- locale state;
- global connection state;
- global modal host;
- toast host;
- page content frame;
- one persistent bottom navigation.

Pages do not render their own bottom navigation and do not create competing primary navigation bars.

### Navigation implementation

Bottom-navigation buttons use real Next.js links. The active item is derived from `usePathname()`:

- `/search` and `/listings/*` highlight `Пошук`;
- `/map` highlights `Карта`;
- `/favorites` highlights `Обране`;
- `/compare` highlights `Порівняння`;
- `/profile` highlights `Профіль`.

Client-side transitions must preserve normal browser history. Telegram Back Button is shown on secondary routes such as `/listings/[id]` and hidden on the five primary routes. When a prior in-app history entry exists it navigates back; otherwise it falls back to `/search`.

### Bottom navigation layering

The bottom navigation must be visually and interactively above all normal page content:

- it is rendered by the root application shell, outside page-local stacking contexts;
- it uses `position: fixed`;
- it receives a documented navigation-layer z-index token;
- page content reserves bottom space equal to navigation height plus Telegram safe-area inset;
- maps, cards, sticky filters and page-local overlays cannot exceed the navigation layer;
- true global modals may appear above it and must block background interaction intentionally;
- navigation buttons use an isolated pointer-events-safe container.

The stacking contract will use named CSS custom properties instead of unrelated magic numbers, for example content, sticky, navigation, toast and modal layers.

## Page designs

### `/search`

The search home is a structured dashboard, not the old marketing landing page.

Sections:

1. compact header with brand, user avatar and language control;
2. primary search summary with a prominent `Створити пошук` action;
3. active search profiles with status and quick management actions;
4. recent matching listings using reusable listing cards;
5. compact statistics derived from actual available data;
6. AI assistant block for summarizing current search results and suggesting owner questions;
7. clear loading, empty, offline and error states.

The old hero orbit, duplicated mode switcher and demo-only navigation controls are removed.

### `/map`

The map page prioritizes the map viewport. It contains:

- route-owned map workspace;
- compact filter button or filter sheet;
- visible result count;
- selected-listing preview card;
- safe top and bottom paddings;
- deterministic empty and geolocation-error states.

Map controls remain below the global navigation and below global modals.

### `/favorites`

The favorites page contains:

- title and count;
- sort and filter controls;
- reusable saved-listing cards;
- remove-from-favorites action;
- open-listing action to `/listings/[id]`;
- a purposeful empty state linking back to `/search`.

### `/compare`

The comparison page contains:

- 2–5 selected listings;
- a mobile-friendly comparison layout rather than a desktop-only wide table;
- price, area, price per square metre, match score, market assessment and risk assessment;
- remove and open-detail actions;
- an empty state explaining how to add listings;
- AI comparison as a section within the page, not a separate route.

### `/profile`

The profile page contains:

- Telegram identity summary;
- locale control;
- notification preferences;
- quiet hours;
- active search-profile management;
- app and connection information;
- safe sign-in/authentication error states.

Developer/system diagnostics are not displayed as prominent user-facing dashboard content.

### `/listings/[id]`

The details page contains:

- image gallery or robust placeholder;
- title, location, price and primary facts;
- favorite and compare actions;
- description and amenities;
- source information and original-listing action when available;
- market assessment;
- price history;
- Risk Score explanation;
- AI summary and suggested owner questions;
- loading, not-found and recoverable API-error states.

The bottom navigation remains visible and highlights `Пошук`. Telegram Back Button returns to the previous route.

## Component boundaries

The refactor creates small reusable units with clear responsibilities:

- `MiniAppShell` — shared providers, content frame and global UI hosts;
- `BottomNavigation` — route links and active-state logic only;
- `MiniAppHeader` — brand, locale and avatar;
- `SearchHome` — composition for `/search`;
- `ListingCard` — reusable listing presentation and actions;
- `SearchProfileCard` — reusable search-profile summary;
- `PageState` components — loading, error, empty and offline states;
- page-specific workspaces for map, favorites, comparison, profile and listing details.

Existing data-fetching functions are reused where they already match the page requirements. Route composition must not duplicate API logic in multiple pages.

## Data flow

Each route owns only the data it needs. Shared authentication, locale and Telegram information come from the application shell context. Page data is fetched through the existing API layer with abortable requests and explicit loading/error states.

Navigation state must never be stored separately from the URL. Search-wizard visibility may remain modal state because it is an action within `/search`, but opening or closing it must not change the active primary route.

## Removal and migration

The implementation removes or retires:

- `StageSixShell` as the application router;
- local `view`, `workspaceTab` and primary-navigation state;
- the `stage-six-switch` navigation bar;
- duplicated navigation buttons inside page compositions;
- route-like scrolling between workspaces;
- primary navigation callbacks passed deeply through components when a route link is sufficient.

Existing feature components may be adapted into route pages, but old wrappers must not remain mounted invisibly.

## Responsive behaviour

- The layout is mobile-first for Telegram Mini App sizes.
- The bottom navigation respects `env(safe-area-inset-bottom)`.
- Each page reserves enough bottom padding that the last action is not hidden.
- Desktop preview uses a centered maximum-width content frame except the map, which may use a wider viewport.
- No horizontal scrolling is permitted except an intentional, accessible comparison region when unavoidable.
- Touch targets are at least 44 by 44 CSS pixels.

## Accessibility

- Navigation uses semantic links within a labelled `nav`.
- The active route exposes `aria-current="page"`.
- All icon-only actions have labels.
- Focus states remain visible.
- Route changes move focus or announce the new page heading appropriately.
- Reduced-motion preferences are respected.
- Empty, loading and error messages are readable without relying on colour alone.

## Error handling

Every route has explicit handling for:

- initial loading;
- empty data;
- backend unavailable;
- authentication unavailable outside Telegram preview;
- request failure with retry;
- missing listing;
- partial analytics data.

A failure in AI, market analytics or risk analytics must not make the listing page unusable.

## Testing strategy

### Routing tests

- `/` redirects to `/search`;
- every primary button targets the correct route;
- the active item follows the pathname;
- `/listings/[id]` highlights `Пошук`;
- old state-only navigation and `stage-six-switch` are absent.

### Layering and layout tests

- the shared layout renders exactly one bottom navigation;
- page content includes the required bottom inset;
- navigation uses the named navigation z-index token;
- map and sticky page controls remain below the navigation layer;
- global modals remain above navigation intentionally.

### Page tests

Each route receives component tests for successful, loading, empty and error states. Listing detail tests cover favorite, compare, back navigation and partial analytics.

### End-to-end acceptance

A browser smoke test must navigate through all five buttons, open a listing route, use back navigation and verify that the bottom navigation remains clickable and visually above page content.

## Acceptance criteria

The redesign is complete only when:

1. all six user-facing route patterns render directly by URL;
2. `/` redirects to `/search`;
3. the five bottom buttons are the only primary navigation;
4. the old secondary switcher is removed;
5. active states derive solely from the URL;
6. the bottom navigation stays above ordinary content on Telegram and desktop;
7. each page has a coherent structure and its own loading, empty and error states;
8. listing details use `/listings/[id]`;
9. Telegram Back Button works for details and secondary navigation;
10. no existing search, favorite, comparison, map, profile, AI or analytics capability is silently lost;
11. frontend lint, typecheck, tests, production build and Docker build pass;
12. backend and secret-scan CI remain green;
13. production Vercel deployment completes successfully.

## Out of scope

- redesigning backend domain models;
- adding a sixth bottom-navigation item;
- introducing a new external map or AI provider;
- replacing the existing visual brand entirely;
- adding unrelated administrative functionality.
