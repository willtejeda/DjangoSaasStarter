# Frontend Module Layout

`src` is organized so product work can move faster without touching one giant file first.

## Entry points

- `main.tsx`: app bootstrap and provider setup.
- `app.tsx`: route composition and page wiring.

## Shared libraries

- `lib/api.ts`: fetch wrappers and API base URL helpers.
- `lib/signals.ts`: app-wide signal state and theme/launch counters.

## Feature modules

- `features/app-shell/types.ts`: shared route/page/view-model types used by the app shell.
- `features/app-shell/ui-utils.ts`: shared UI utility functions and style tokens used across pages.

## Rule for future changes

1. Add reusable types and helpers under `features/` first.
2. Keep `app.tsx` focused on composing screens, not owning every type and helper.
3. When a section grows large, extract it into a feature folder before adding more behavior.
