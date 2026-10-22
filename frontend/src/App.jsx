import Navbar from './components/Navbar.jsx'
import Home from './pages/Home.jsx'

/**
 * Application shell.
 *
 * The project is intentionally a single-page flow (upload -> configure ->
 * summarize -> evaluate), so there is no router. `Home` owns the page state
 * machine described in the requirements:
 *
 *   idle | uploading | uploaded | processing | completed | error
 */
export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
        <Home />
      </main>
      <footer className="border-t border-edge bg-surface">
        <div className="mx-auto max-w-5xl px-4 py-4 text-xs text-ink-muted sm:px-6 lg:px-8">
          MCA Minor Project &middot; Extractive &middot; Abstractive &middot; Hybrid
          summarization with ROUGE and BLEU evaluation
        </div>
      </footer>
    </div>
  )
}
