import type { Edge } from '@xyflow/react'
import type { GlitchNodeType } from './components/GlitchNode'
import type { GnodeGraph } from './types'

/** Convert the React Flow canvas state into a `.gnode` graph payload. */
export function toGnodeGraph(
  nodes: GlitchNodeType[],
  edges: Edge[],
  seed: number,
  resolution: [number, number],
): GnodeGraph {
  return {
    version: '1.0',
    meta: { seed, resolution },
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.data.descriptor.type,
      params: n.data.params,
      pos: [n.position.x, n.position.y],
    })),
    edges: edges.flatMap((e) =>
      e.sourceHandle && e.targetHandle
        ? [
            {
              from: [e.source, e.sourceHandle] as [string, string],
              to: [e.target, e.targetHandle] as [string, string],
            },
          ]
        : [],
    ),
  }
}
