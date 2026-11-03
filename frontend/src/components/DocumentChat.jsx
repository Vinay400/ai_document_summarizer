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
    <section className="rounded-2xl border border-slate-200/90 bg-white shadow-xs overflow-hidden">
      {/* Header Accordion */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between p-5 sm:p-6 text-left transition hover:bg-slate-50/70"
      >
        <div className="flex items-center gap-3.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-xs">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-slate-900">
                Ask Document (Interactive RAG Assistant)
              </h3>
              <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-blue-700 ring-1 ring-inset ring-blue-700/20">
                Retrieval-Augmented
              </span>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              Verify facts and query {filename || 'the document'} with exact source evidence
            </p>
          </div>
        </div>
        <span className="text-xs font-bold text-indigo-600">
          {isOpen ? '▲ Collapse' : '▼ Expand'}
        </span>
      </button>

      {isOpen && (
        <div className="space-y-4 border-t border-slate-100 p-5 sm:p-6 bg-slate-50/30">
          {/* Quick Prompts */}
          <div>
            <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Suggested Questions
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((sq, i) => (
                <button
                  key={i}
                  type="button"
                  disabled={isLoading}
                  onClick={() => handleAsk(sq)}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-2xs transition hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50/30 disabled:opacity-50 active:scale-95"
                >
                  {sq}
                </button>
              ))}
            </div>
          </div>

          {/* Conversation History Area */}
          {messages.length > 0 && (
            <div className="max-h-96 space-y-3.5 overflow-y-auto rounded-xl border border-slate-200 bg-white p-4 shadow-inner">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col ${
                    msg.sender === 'user' ? 'items-end' : 'items-start'
                  }`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl p-3.5 text-sm ${
                      msg.sender === 'user'
                        ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-br-none shadow-xs'
                        : msg.isError
                        ? 'border border-rose-200 bg-rose-50 text-rose-700 rounded-bl-none'
                        : 'border border-slate-200 bg-slate-50/80 text-slate-800 rounded-bl-none shadow-2xs'
                    }`}
                  >
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>

                    {/* Metadata & Relevance Score for Bot */}
                    {msg.sender === 'assistant' && !msg.isError && (
                      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200/80 pt-2 text-[11px] text-slate-500">
                        <span className="font-mono font-bold text-emerald-600">
                          ✓ {msg.confidence}% Relevance
                        </span>
                        {msg.sources && msg.sources.length > 0 && (
                          <button
                            type="button"
                            onClick={() => toggleSources(idx)}
                            className="font-bold text-indigo-600 hover:text-indigo-800 transition"
                          >
                            {expandedSources[idx]
                              ? 'Hide Evidence ▲'
                              : `View Retrieved Evidence (${msg.sources.length}) ▼`}
                          </button>
                        )}
                      </div>
                    )}

                    {/* Expandable Evidence Snippets */}
                    {expandedSources[idx] && msg.sources && (
                      <div className="mt-2.5 space-y-1.5 border-t border-slate-200 pt-2">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                          Context Passages from Source:
                        </p>
                        {msg.sources.map((src, sIdx) => (
                          <blockquote
                            key={sIdx}
                            className="rounded-lg border-l-2 border-indigo-500 bg-white p-2.5 text-xs italic text-slate-600 shadow-2xs"
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
                <div className="flex items-center gap-2.5 text-xs text-slate-500 py-1">
                  <div className="flex gap-1">
                    <span className="h-2 w-2 rounded-full bg-indigo-600 animate-bounce" />
                    <span className="h-2 w-2 rounded-full bg-indigo-600 animate-bounce delay-100" />
                    <span className="h-2 w-2 rounded-full bg-indigo-600 animate-bounce delay-200" />
                  </div>
                  <span>Searching document context and formulating answer&hellip;</span>
                </div>
              )}
            </div>
          )}

          {/* Input Form */}
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
              className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <button
              type="submit"
              disabled={isLoading || !question.trim()}
              className="rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-xs transition hover:bg-indigo-700 disabled:opacity-50 active:scale-95"
            >
              {isLoading ? 'Searching…' : 'Ask'}
            </button>
            {messages.length > 0 && (
              <button
                type="button"
                onClick={() => setMessages([])}
                className="rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs font-semibold text-slate-500 shadow-2xs transition hover:bg-slate-50 hover:text-slate-700"
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
