import { useEffect } from 'react'
import type { NodePreview } from '../types'

interface CompareModalProps {
  title: string
  after: NodePreview
  afterLabel: string
  before?: NodePreview
  beforeLabel?: string
  onClose: () => void
}

/** A lightbox that enlarges a node's rendered output, with an optional
 * side-by-side "before" (the upstream image feeding this node) for glitch
 * before/after comparison. */
export function CompareModal({
  title,
  after,
  afterLabel,
  before,
  beforeLabel,
  onClose,
}: CompareModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label={`${title} preview`}>
      <button type="button" className="modal-scrim" onClick={onClose} aria-label="Close preview" />
      <div className="modal-card">
        <div className="modal-head">
          <h3>{title}</h3>
          <button
            type="button"
            className="config-close"
            onClick={onClose}
            aria-label="Close preview"
          >
            ×
          </button>
        </div>
        <div className={`compare${before ? ' two' : ''}`}>
          {before && (
            <figure className="compare-pane">
              <img src={before.data_url} alt={`${beforeLabel} output`} draggable={false} />
              <figcaption>before · {beforeLabel}</figcaption>
            </figure>
          )}
          <figure className="compare-pane">
            <img src={after.data_url} alt={`${afterLabel} output`} draggable={false} />
            <figcaption>{before ? `after · ${afterLabel}` : afterLabel}</figcaption>
          </figure>
        </div>
      </div>
    </div>
  )
}
