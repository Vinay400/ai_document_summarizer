import { useState } from 'react'
import Navbar from './components/Navbar.jsx'
import Home from './pages/Home.jsx'

/**
 * Application Shell.
 *
 * Single-page architecture with state machine flow:
 *   idle | uploading | uploaded | processing | completed | error
 */
export default function App() {
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)
  const [backendState, setBackendState] = useState('checking')

  return (
    <div className="flex min-h-screen flex-col bg-slate-50/60 selection:bg-indigo-100 selection:text-indigo-900">
      <Navbar
        backendState={backendState}
        onOpenHistory={() => setIsHistoryOpen(true)}
      />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
        <Home
          isHistoryOpen={isHistoryOpen}
          setIsHistoryOpen={setIsHistoryOpen}
          backendState={backendState}
          setBackendState={setBackendState}
        />
      </main>

      <footer className="border-t border-slate-200/80 bg-white/70 py-6 text-center backdrop-blur-xs">
        <div className="mx-auto max-w-6xl px-4 text-xs text-slate-500 sm:px-6 lg:px-8 space-y-1">
          <p className="font-semibold text-slate-700">
            AI Document Summarization Platform &middot; MCA Major Project
          </p>
          <p className="text-[11px] text-slate-400">
            Extractive TextRank &middot; Abstractive BART Map-Reduce &middot; Hybrid Pipeline &middot; RAG Assistant &middot; ROUGE &amp; BLEU Scoring
          </p>
        </div>
      </footer>
    </div>
  )
}
