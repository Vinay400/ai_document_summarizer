/**
 * Thin wrapper around the FastAPI backend.
 *
 * Keeping every HTTP detail in this one module means:
 *   - components never build URLs or touch axios directly;
 *   - error shapes are normalised once, in one place, so the UI can always
 *     render `error.message` without defensive checks;
 *   - swapping axios for fetch (or changing the base URL) touches one file.
 */
import axios from 'axios'

/** Base URL of the FastAPI server. Override with VITE_API_BASE_URL in `.env`. */
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  // Summarizing a long document on CPU is genuinely slow (map-reduce over many
  // chunks can take minutes), so the client timeout must be generous.
  timeout: 300_000,
})

/**
 * Collapse every possible failure mode into a single Error with a readable
 * `message` and an optional `status`.
 *
 * Handled cases: HTTP error responses (400/413/422/500), timeouts, the server
 * being unreachable, and anything unexpected.
 */
function normaliseError(error) {
  if (error.response) {
    const { status, data } = error.response
    let detail = data?.detail

    // FastAPI validation errors arrive as a list of objects; our backend
    // flattens them to a string, but stay defensive in case one slips through.
    if (Array.isArray(detail)) {
      detail = detail.map((item) => item?.msg ?? String(item)).join('; ')
    }
    if (typeof detail !== 'string' || !detail.trim()) {
      detail = `Request failed with status ${status}.`
    }

    const wrapped = new Error(detail)
    wrapped.status = status
    return wrapped
  }

  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
    return new Error(
      'The request timed out. Very long documents can take several minutes on CPU — try a shorter document or the Extractive mode.',
    )
  }

  if (error.request) {
    return new Error(
      `Cannot reach the backend at ${API_BASE_URL}. Make sure the FastAPI server is running.`,
    )
  }

  return new Error(error.message || 'An unexpected error occurred.')
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(normaliseError(error)),
)

/**
 * Check that the backend is alive and how it is configured.
 *
 * @returns {Promise<{status: string, service: string, version: string, python_version: string}>}
 */
export async function checkHealth() {
  const { data } = await apiClient.get('/api/health')
  return data
}

/**
 * Upload a document file (PDF, DOCX, or TXT).
 *
 * @param {File} file
 * @returns {Promise<UploadResponse>}
 */
export async function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return data
}

/**
 * Request a summary for an uploaded document.
 *
 * @param {Object} params
 * @param {string} params.document_id
 * @param {string} [params.mode='extractive']
 * @param {string} [params.length='medium']
 * @returns {Promise<SummarizeResponse>}
 */
export async function summarizeDocument({ document_id, mode = 'extractive', length = 'medium' }) {
  const { data } = await apiClient.post('/api/summarize', {
    document_id,
    mode,
    length,
  })
  return data
}

/**
 * Request an evaluation of a summary against a reference text.
 *
 * @param {Object} params
 * @param {string} params.document_id
 * @param {string} params.reference
 * @param {string} [params.mode='extractive']
 * @param {string} [params.length='medium']
 * @returns {Promise<EvaluateResponse>}
 */
export async function evaluateDocument({ document_id, reference, mode = 'extractive', length = 'medium' }) {
  const { data } = await apiClient.post('/api/evaluate', {
    document_id,
    reference,
    mode,
    length,
  })
  return data
}

/**
 * Request summaries for all 3 modes (extractive, abstractive, hybrid) simultaneously.
 *
 * @param {Object} params
 * @param {string} params.document_id
 * @param {string} [params.length='medium']
 * @returns {Promise<CompareSummarizeResponse>}
 */
export async function compareSummarizeDocument({ document_id, length = 'medium' }) {
  const { data } = await apiClient.post('/api/summarize/compare', {
    document_id,
    length,
  })
  return data
}

/**
 * Request evaluation of all 3 summarization modes against a ground-truth reference.
 *
 * @param {Object} params
 * @param {string} params.document_id
 * @param {string} params.reference
 * @param {string} [params.length='medium']
 * @param {Object} [params.summaries]
 * @returns {Promise<CompareEvaluateResponse>}
 */
export async function compareEvaluateDocument({ document_id, reference, length = 'medium', summaries = null }) {
  const { data } = await apiClient.post('/api/evaluate/compare', {
    document_id,
    reference,
    length,
    summaries,
  })
  return data
}

/**
 * Ask a question about an uploaded document using RAG.
 *
 * @param {Object} params
 * @param {string} params.document_id
 * @param {string} params.question
 * @returns {Promise<{question: string, answer: string, confidence: number, sources: string[]}>}
 */
export async function chatWithDocument({ document_id, question }) {
  const { data } = await apiClient.post('/api/chat', {
    document_id,
    question,
  })
  return data
}

/**
 * Fetch all past documents and summaries from the history database.
 *
 * @returns {Promise<{documents: Array<Object>}>}
 */
export async function fetchHistory() {
  const { data } = await apiClient.get('/api/history')
  return data
}

/**
 * Fetch full history details for a single document.
 *
 * @param {string} document_id
 * @returns {Promise<Object>}
 */
export async function fetchHistoryDocument(document_id) {
  const { data } = await apiClient.get(`/api/history/${document_id}`)
  return data
}

/**
 * Delete a document from history.
 *
 * @param {string} document_id
 * @returns {Promise<{message: string}>}
 */
export async function deleteHistoryItem(document_id) {
  const { data } = await apiClient.delete(`/api/history/${document_id}`)
  return data
}

/**
 * Generate a downloadable Executive Summary Report.
 *
 * @param {Object} params
 * @param {string} params.document_id
 * @param {string} [params.mode='extractive']
 * @param {string} [params.length='medium']
 * @returns {Promise<{document_id: string, filename: string, markdown: string, html: string}>}
 */
export async function exportExecutiveBrief({ document_id, mode = 'extractive', length = 'medium' }) {
  const { data } = await apiClient.post('/api/export/brief', {
    document_id,
    mode,
    length,
  })
  return data
}

export default apiClient

