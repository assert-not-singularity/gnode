export type ToastKind = 'info' | 'error'

export interface Toast {
  id: number
  message: string
  kind: ToastKind
}

interface ToastsProps {
  toasts: Toast[]
  onDismiss: (id: number) => void
}

/** Transient notifications (save/load/export feedback and errors). The region is
 * an aria-live status so screen readers announce new toasts. */
export function Toasts({ toasts, onDismiss }: ToastsProps) {
  if (toasts.length === 0) return null
  return (
    <output className="toasts" aria-live="polite">
      {toasts.map((t) => (
        <button
          key={t.id}
          type="button"
          className={`toast toast-${t.kind}`}
          onClick={() => onDismiss(t.id)}
          title="Dismiss"
        >
          {t.message}
        </button>
      ))}
    </output>
  )
}
