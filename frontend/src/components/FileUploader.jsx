import { useCallback, useState } from 'react'

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt']
const MAX_FILE_SIZE_MB = 20
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

export default function FileUploader({ onUpload, isUploading }) {
  const [dragActive, setDragActive] = useState(false)
  const [clientError, setClientError] = useState(null)
  const [selectedFileName, setSelectedFileName] = useState(null)

  const validateAndProcess = (file) => {
    setClientError(null)
    if (!file) return

    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setClientError(
        `Unsupported file type '${ext}'. Please upload a PDF, DOCX, or TXT file.`
      )
      return
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setClientError(
        `File size (${(file.size / 1024 / 1024).toFixed(1)} MB) exceeds the limit of ${MAX_FILE_SIZE_MB} MB.`
      )
      return
    }

    setSelectedFileName(file.name)
    onUpload(file)
  }

  const handleDrag = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndProcess(e.dataTransfer.files[0])
    }
  }, [])

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndProcess(e.target.files[0])
    }
  }

  return (
    <div className="space-y-3">
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition ${
          dragActive
            ? 'border-accent bg-accent-soft/30'
            : 'border-edge-strong bg-surface hover:border-accent'
        }`}
      >
        <input
          type="file"
          id="file-upload"
          accept=".pdf,.docx,.txt"
          onChange={handleChange}
          disabled={isUploading}
          className="absolute inset-0 cursor-pointer opacity-0 disabled:cursor-not-allowed"
        />

        {isUploading ? (
          <div className="flex flex-col items-center space-y-2">
            <svg
              className="h-8 w-8 animate-spin text-accent"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8H4z"
              />
            </svg>
            <p className="text-sm font-medium text-ink">
              Uploading {selectedFileName}…
            </p>
            <p className="text-xs text-ink-muted">Extracting and cleaning text</p>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-surface-sunken text-ink-muted">
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 16.5v-9m0 0l-3.75 3.75M12 7.5l3.75 3.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div className="text-sm text-ink">
              <span className="font-semibold text-accent">Click to upload</span>{' '}
              or drag and drop
            </div>
            <p className="text-xs text-ink-muted">
              PDF, DOCX, or TXT (up to {MAX_FILE_SIZE_MB} MB)
            </p>
          </div>
        )}
      </div>

      {clientError && (
        <div className="rounded-lg border border-danger/30 bg-danger-soft p-3 text-xs text-danger">
          {clientError}
        </div>
      )}
    </div>
  )
}
