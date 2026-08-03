import { useRef, useState } from "react"
import { ApiError, createRun, type RunCreated } from "../api"

interface UploadPaneProps {
  onCreated: (run: RunCreated) => void
}

type Mode = "upload" | "paste"

const ACCEPT = ".pdf,.fountain,.txt"

/** Upload view: drag/drop or file picker, or a paste-text alternative. */
export function UploadPane({ onCreated }: UploadPaneProps) {
  const [mode, setMode] = useState<Mode>("upload")
  const [file, setFile] = useState<File | null>(null)
  const [pastedText, setPastedText] = useState("")
  const [isDragging, setIsDragging] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<{ code: string; message: string } | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const canSubmit = mode === "upload" ? file !== null : pastedText.trim().length > 0

  async function handleSubmit() {
    if (!canSubmit || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      const run = await createRun(
        mode === "upload" ? { file: file! } : { text: pastedText },
      )
      onCreated(run)
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ code: err.code, message: err.message })
      } else {
        setError({
          code: "network_error",
          message: err instanceof Error ? err.message : "Something went wrong.",
        })
      }
    } finally {
      setSubmitting(false)
    }
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragging(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) {
      setFile(dropped)
      setError(null)
    }
  }

  return (
    <div className="upload-pane">
      <div className="upload-pane__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "upload"}
          className={`upload-pane__tab ${mode === "upload" ? "is-active" : ""}`}
          onClick={() => setMode("upload")}
        >
          Upload file
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "paste"}
          className={`upload-pane__tab ${mode === "paste" ? "is-active" : ""}`}
          onClick={() => setMode("paste")}
        >
          Paste text
        </button>
      </div>

      {mode === "upload" ? (
        <div
          className={`upload-pane__dropzone ${isDragging ? "is-dragging" : ""} ${file ? "has-file" : ""}`}
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="upload-pane__file-input"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null)
              setError(null)
            }}
          />
          {file ? (
            <>
              <p className="upload-pane__filename">{file.name}</p>
              <p className="upload-pane__hint">Click or drop to replace</p>
            </>
          ) : (
            <>
              <p className="upload-pane__prompt">Drop a script here, or click to browse</p>
              <p className="upload-pane__hint">.pdf · .fountain · .txt</p>
            </>
          )}
        </div>
      ) : (
        <textarea
          className="upload-pane__textarea"
          placeholder="Paste your screenplay text here…"
          value={pastedText}
          onChange={(e) => {
            setPastedText(e.target.value)
            setError(null)
          }}
          rows={12}
        />
      )}

      {error && (
        <div className="error-banner" role="alert">
          <span className="error-banner__code">{error.code}</span>
          <span className="error-banner__message">{error.message}</span>
        </div>
      )}

      <div className="upload-pane__footer">
        <p className="upload-pane__caption">Screenplays up to 130 pages, English.</p>
        <button
          type="button"
          className="button button--primary"
          disabled={!canSubmit || submitting}
          onClick={handleSubmit}
        >
          {submitting ? "Analyzing…" : "Analyze script"}
        </button>
      </div>
    </div>
  )
}
