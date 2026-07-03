import { createContext } from 'react'
import type { MissingPort } from './graph'
import type { NodePreview } from './types'

/** Per-node evaluate results, read by GlitchNode to show a thumbnail / error
 * without those results being part of the node state that triggers re-evaluation. */
export interface PreviewState {
  previews: Record<string, NodePreview>
  errors: Record<string, string>
  /** Node id -> unmet required input ports (not yet wired up; not an error). */
  incomplete: Record<string, MissingPort[]>
}

export const PreviewContext = createContext<PreviewState>({
  previews: {},
  errors: {},
  incomplete: {},
})
