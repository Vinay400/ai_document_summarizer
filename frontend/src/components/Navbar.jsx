/**
 * Top navigation bar.
 *
 * Deliberately minimal: project identity plus a link to the API docs. It takes
 * no props so it can be rendered from anywhere without wiring.
 */
export default function Navbar() {
  return (
    <header className="sticky top-0 z-20 border-b border-edge bg-surface/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <span
            aria-hidden="true"
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-sm font-bold text-white"
          >
            AI
          </span>
          <div className="leading-tight">
            <h1 className="text-sm font-semibold tracking-tight text-ink sm:text-base">
              AI Document Summarization
            </h1>
            <p className="hidden text-xs text-ink-muted sm:block">
              Extractive &middot; Abstractive &middot; Hybrid
            </p>
          </div>
        </div>

        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="rounded-md border border-edge px-3 py-1.5 text-xs font-medium text-ink-muted transition hover:border-edge-strong hover:text-ink"
        >
          API Docs
        </a>
      </div>
    </header>
  )
}
