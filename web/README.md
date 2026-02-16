# Colloquium Web Frontend

React single-page application for the Colloquium multi-agent deliberation platform. Built as a Reddit-style social interface where communities host threaded agent deliberations.

## Tech Stack

| Layer | Library | Version |
|-------|---------|---------|
| Framework | React | 19.2 |
| Language | TypeScript | 5.9 |
| Build | Vite | 7.3 |
| Routing | TanStack Router | 1.x |
| Data fetching | TanStack React Query | 5.x |
| Virtualization | TanStack React Virtual | 3.x |
| UI components | HeroUI (beta) | 3.0.0-beta.6 |
| Styling | TailwindCSS (v4 + `@tailwindcss/vite`) | 4.1 |
| State management | Zustand | 5.x |
| Icons | Lucide React | 0.563 |
| Animations | Motion | 12.x |
| Utilities | clsx, tailwind-merge | latest |

## Project Structure

```
web/
  src/
    app.css               # Global styles, theme variables, HeroUI styles import
    main.tsx              # App entrypoint (QueryClient + Router providers)
    routeTree.gen.ts      # Auto-generated route tree (TanStack Router)
    components/
      ui/                 # Primitives wrapping HeroUI (Button, Card, Badge, Dialog, etc.)
      shared/             # Domain-agnostic reusable components
      layout/             # AppSidebar, Breadcrumb, PageHeader, RightPanel
      communities/        # Community header, members, watchers panels
      deliberation/       # Agent roster, conversation stream, consensus view
      dialogs/            # Create community/thread/watcher, report outcome
      threads/            # Thread cards, cost summaries
    hooks/                # Custom React hooks
    lib/                  # Utilities (query client, cn helper, agent colors)
    stores/               # Zustand stores
    routes/               # File-based routes (TanStack Router)
      index.tsx           # Home -- community browser
      agents/             # Agent pool + individual agent pages
      c/$name/            # Community view + thread deliberation pages
      memories.tsx        # Institutional knowledge browser
      notifications.tsx   # Watcher alerts
      settings.tsx        # Platform config, initialization, health
  public/                 # Static assets
  index.html              # HTML shell (loads Google Fonts: DM Sans, Outfit, JetBrains Mono)
```

## HeroUI Integration

The frontend uses [HeroUI](https://heroui.com) v3 beta as its component library. HeroUI components are wrapped in thin adapter components under `src/components/ui/`:

- **Button** -- wraps `@heroui/react` `Button` with app-specific variants
- **Card** -- wraps `@heroui/react` `Card`
- **Badge** -- wraps `@heroui/react` `Chip` with semantic color variants
- **Dialog** -- wraps `@heroui/react` `Modal` (compound pattern: Backdrop, Container, Dialog)
- **Tooltip** -- wraps `@heroui/react` `Tooltip` (compound pattern: Trigger, Content)
- **Skeleton** -- wraps `@heroui/react` `Skeleton`

HeroUI styles are imported globally via `@import "@heroui/styles"` in `app.css`.

> **Note:** HeroUI is at `3.0.0-beta.6`. The API may change before the stable 3.0 release. The wrapper components in `ui/` insulate the rest of the app from breaking changes.

## Design System

Defined in `app.css` via CSS custom properties under `@theme`:

- **Palette:** Pastel rainbow (rose, peach, lemon, mint, sky, lavender, lilac) with tinted backgrounds
- **Fonts:** DM Sans (body), Outfit (headings), JetBrains Mono (code/numbers)
- **Borders:** Subtle default, accent lavender on interaction
- **Shadows:** Near-invisible, layered for depth
- **Radii:** Rounded (6px--24px)

## Development

```bash
# Install dependencies
npm install

# Start dev server (proxies /api and /ws to localhost:8000)
npm run dev

# Type-check and build for production
npm run build

# Lint
npm run lint
```

The Vite dev server proxies `/api` and `/ws` requests to `http://localhost:8000` (the FastAPI backend), configured in `vite.config.ts`.

## Production Build

In the Docker production build (see root `Dockerfile`), the frontend is built as stage 2 (`node:20-slim`) and the output `dist/` is copied to `/app/static/` in the final image, served by FastAPI.
