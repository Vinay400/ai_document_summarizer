import { useState } from 'react'
import { chatWithDocument } from '../services/api.js'

const SUGGESTED_QUESTIONS = [
  'What is the primary conclusion or takeaway?',
  'What are the key findings or results?',
  'What methodology or approach is used?',
  'What challenges or limitations are discussed?',
]

export default function DocumentChat({ documentId, filename }) {
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(true)
  const [expandedSources, setExpandedSources] = useState({})

  if (!documentId) return null

  const handleAsk = async (queryText) => {
    const q = queryText || question
    if (!q.trim() || isLoading) return

    const userMsg = { sender: 'user', text: q.trim(), timestamp: new Date() }
    setMessages((prev) => [...prev, userMsg])
    setQuestion('')
    setIsLoading(true)

    try {
      const res = await chatWithDocument({
        document_id: documentId,
        question: q.trim(),
      })

      const botMsg = {
        sender: 'assistant',
        text: res.answer,
        confidence: res.confidence,
        sources: res.sources,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, botMsg])
    } catch (err) {
      const errorMsg = {
        sender: 'assistant',
        text: `Error: ${err.message || 'Unable to retrieve answer.'}`,
        isError: true,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  const toggleSources = (index) => {
    setExpandedSources((prev) => ({
      ...prev,
      [index]: !prev[index],
    }))
  }

  return (
    <section className="rounded-xl border border-edge bg-surface shadow-sm">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between p-6 text-left transition hover:bg-surface-sunken/40"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400">
            💬
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-ink">
                Ask Document (Interactive RAG Assistant)
              </h3>
              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                Retrieval-Augmented
              </span>
            </div>
            <p className="mt-0.5 text-xs text-ink-muted">
              Verify facts and ask custom questions directly grounded in {filename || 'the document'}
            </p>
          </div>
        </div>
        <span className="text-xs font-semibold text-accent">
          {isOpen ? '▲ Collapse' : '▼ Expand'}
        </span>
      </button>

      {isOpen && (
        <div className="space-y-4 border-t border-edge p-6">
          {/* Suggested Quick Questions */}
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-subtle">
              Suggested Questions
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((sq, i) => (
                <button
                  key={i}
                  type="button"
                  disabled={isLoading}
                  onClick={() => handleAsk(sq)}
                  className="rounded-lg border border-edge bg-surface-sunken px-2.5 py-1 text-xs text-ink transition hover:border-accent hover:text-accent disabled:opacity-50"
                >
                  {sq}
                </button>
              ))}
            </div>
          </div>

          {/* Conversation History */}
          {messages.length > 0 && (
            <div className="max-h-80 space-y-3 overflow-y-auto rounded-lg border border-edge bg-surface-sunken p-4">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col ${
                    msg.sender === 'user' ? 'items-end' : 'items-start'
                  }`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg p-3 text-sm shadow-xs ${
                      msg.sender === 'user'
                        ? 'bg-accent text-white'
                        : msg.isError
                        ? 'border border-red-200 bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300'
                        : 'border border-edge bg-surface text-ink'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.text}</p>

                    {/* Metadata & Confidence for Bot Responses */}
                    {msg.sender === 'assistant' && !msg.isError && (
                      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 border-t border-edge/60 pt-2 text-[11px] text-ink-muted">
                        <span className="flex items-center gap-1 font-mono font-medium text-emerald-600 dark:text-emerald-400">
                          ✓ {msg.confidence}% Relevance
                        </span>
                        {msg.sources && msg.sources.length > 0 && (
                          <button
                            type="button"
                            onClick={() => toggleSources(idx)}
                            className="font-medium text-accent hover:underline"
                          >
                            {expandedSources[idx]
                              ? 'Hide Citations ▲'
                              : `View Citations (${msg.sources.length}) ▼`}
                          </button>
                        )}
                      </div>
                    )}

                    {/* Expandable Citations */}
                    {expandedSources[idx] && msg.sources && (
                      <div className="mt-2 space-y-1.5 border-t border-edge/60 pt-2">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-ink-subtle">
                          Retrieved Source Evidence:
                        </p>
                        {msg.sources.map((src, sIdx) => (
                          <blockquote
                            key={sIdx}
                            className="rounded border-l-2 border-accent bg-surface-sunken p-2 text-xs italic text-ink-muted"
                          >
                            &ldquo;{src}&rdquo;
                          </blockquote>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex items-center gap-2 text-xs text-ink-muted">
                  <div className="h-2 w-2 animate-bounce rounded-full bg-accent" />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-accent delay-100" />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-accent delay-200" />
                  <span>Searching document context and formulating answer…</span>
                </div>
              )}
            </div>
          )}

          {/* Question Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleAsk()
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask anything about this document..."
              disabled={isLoading}
              className="flex-1 rounded-lg border border-edge bg-surface-sunken px-3.5 py-2 text-sm text-ink placeholder:text-ink-subtle focus:border-accent focus:bg-surface focus:outline-none"
            />
            <button
              type="submit"
              disabled={isLoading || !question.trim()}
              className="rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-accent-strong disabled:opacity-50"
            >
              {isLoading ? 'Searching…' : 'Ask'}
            </button>
            {messages.length > 0 && (
              <button
                type="button"
                onClick={() => setMessages([])}
                className="rounded-lg border border-edge bg-surface px-3 py-2 text-xs font-medium text-ink-muted transition hover:bg-surface-sunken hover:text-ink"
                title="Clear conversation"
              >
                Clear
              </button>
            )}
          </form>
        </div>
      )}
    </section>
  )
}

