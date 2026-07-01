import { createContext } from 'react'
import type { NodePreview } from './types'

/** Per-node evaluate results, read by GlitchNode to show a thumbnail / error
 * without those results being part of the node state that triggers re-evaluation. */
export interface PreviewState {
  previews: Record<string, NodePreview>
  errors: Record<string, string>
}

export const PreviewContext = createContext<PreviewState>({ previews: {}, errors: {} })
