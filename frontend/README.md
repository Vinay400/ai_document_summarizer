# Frontend — AI Document Summarization

React 19 + Vite + Tailwind CSS v4 single-page interface for the summarization
platform.

## Setup

```bash
cd frontend
npm install
cp .env.example .env     # optional; defaults to http://localhost:8000
```

## Run

```bash
npm run dev      # http://localhost:5173
npm run build    # production bundle into dist/
npm run preview  # serve the production build locally
```

## Layout

| Path | Responsibility |
|---|---|
| `src/App.jsx` | Page shell (navbar, main, footer) |
| `src/pages/Home.jsx` | Owns the page state machine |
| `src/components/` | Presentational components |
| `src/services/api.js` | All HTTP calls and error normalisation |

## Notes

* Tailwind v4 is wired through the `@tailwindcss/vite` plugin and imported with
  `@import "tailwindcss";` in `src/index.css`. There is no `tailwind.config.js`.
* Design tokens (`--color-ink`, `--color-accent`, …) are declared in the
  `@theme` block of `src/index.css`, which is what makes utilities such as
  `bg-surface`, `text-ink-muted` and `border-edge` available.
* The app calls FastAPI **cross-origin** rather than through a Vite proxy, so
  the backend CORS configuration is exercised for real.

## Phase status

- [x] **Phase 1** — Vite + React + Tailwind shell, axios API layer, backend
      health probe proving the front-end/back-end link
- [ ] Phase 9 — upload, mode/length selection, progress, summary, evaluation UI
