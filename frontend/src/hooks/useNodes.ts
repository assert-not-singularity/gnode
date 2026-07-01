import { useEffect, useState } from 'react'
import { fetchNodes } from '../api/client'
import type { NodeDescriptor } from '../types'

export interface CatalogState {
  nodes: NodeDescriptor[]
  loading: boolean
  error: string | null
}

/** Fetch the node catalog once on mount. */
export function useNodes(): CatalogState {
  const [state, setState] = useState<CatalogState>({ nodes: [], loading: true, error: null })

  useEffect(() => {
    let active = true
    fetchNodes()
      .then((nodes) => {
        if (active) setState({ nodes, loading: false, error: null })
      })
      .catch((err: unknown) => {
        if (active) {
          setState({
            nodes: [],
            loading: false,
            error: err instanceof Error ? err.message : String(err),
          })
        }
      })
    return () => {
      active = false
    }
  }, [])

  return state
}
