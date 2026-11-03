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
        `Unsupported format '${ext}'. Please upload a standard PDF, DOCX, or TXT file.`
      )
      return
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setClientError(
        `File size (${(file.size / 1024 / 1024).toFixed(1)} MB) exceeds the maximum limit of ${MAX_FILE_SIZE_MB} MB.`
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
    <div className="space-y-4">
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`group relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 text-center transition duration-200 ${
          dragActive
            ? 'border-indigo-500 bg-indigo-50/50 scale-[1.01] shadow-lg shadow-indigo-500/10'
            : 'border-slate-300 bg-white hover:border-indigo-400 hover:bg-slate-50/50 shadow-xs'
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
          <div className="flex flex-col items-center space-y-3 py-4">
            <div className="relative">
              <div className="h-14 w-14 rounded-2xl bg-indigo-100 flex items-center justify-center text-indigo-600 animate-pulse">
                <svg className="h-7 w-7 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">
                Processing {selectedFileName}&hellip;
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                Extracting text, running OCR fallback if scanned, and normalizing
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 ring-8 ring-indigo-50/50 transition group-hover:scale-110 group-hover:bg-indigo-100">
              <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>

            <div>
              <p className="text-base font-semibold text-slate-800">
                <span className="text-indigo-600 group-hover:underline">Click to upload</span> or drag and drop your document
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Supports research papers, legal contracts, reports, and books up to {MAX_FILE_SIZE_MB} MB
              </p>
            </div>

            {/* Supported format badges */}
            <div className="flex items-center justify-center gap-2 pt-1">
              <span className="inline-flex items-center rounded-md bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700 ring-1 ring-inset ring-rose-600/20">
                PDF
              </span>
              <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700 ring-1 ring-inset ring-blue-600/20">
                DOCX
              </span>
              <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                TXT
              </span>
              <span className="inline-flex items-center rounded-md bg-purple-50 px-2 py-1 text-xs font-medium text-purple-700 ring-1 ring-inset ring-purple-600/20">
                OCR Auto-detect
              </span>
            </div>
          </div>
        )}
      </div>

      {clientError && (
        <div className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-700">
          <span className="text-sm">⚠️</span>
          <p className="font-medium">{clientError}</p>
        </div>
      )}
    </div>
  )
}
