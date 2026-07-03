import type { Edge } from '@xyflow/react'
import type { GlitchNodeType } from './components/GlitchNode'
import type { GnodeGraph, NodeDescriptor } from './types'

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

export interface LoadedGraph {
  nodes: GlitchNodeType[]
  edges: Edge[]
  seed: number
  resolution: [number, number]
  /** Node types present in the file but missing from the current catalog. */
  skipped: string[]
}

/** Rebuild the React Flow canvas from a loaded `.gnode` graph. Nodes whose type
 * is absent from the catalog (and edges touching them) are dropped and reported. */
export function fromGnodeGraph(
  graph: GnodeGraph,
  byType: Map<string, NodeDescriptor>,
): LoadedGraph {
  const skipped: string[] = []
  const nodes: GlitchNodeType[] = []
  graph.nodes.forEach((n, i) => {
    const descriptor = byType.get(n.type)
    if (!descriptor) {
      skipped.push(n.type)
      return
    }
    nodes.push({
      id: n.id,
      type: 'glitchNode',
      position: { x: n.pos?.[0] ?? 120 + i * 40, y: n.pos?.[1] ?? 120 + i * 40 },
      data: { descriptor, label: n.id, params: { ...n.params } },
    })
  })
  const present = new Set(nodes.map((n) => n.id))
  const edges: Edge[] = graph.edges
    .filter((e) => present.has(e.from[0]) && present.has(e.to[0]))
    .map((e) => ({
      id: `${e.from[0]}.${e.from[1]}->${e.to[0]}.${e.to[1]}`,
      source: e.from[0],
      sourceHandle: e.from[1],
      target: e.to[0],
      targetHandle: e.to[1],
    }))
  const [w, h] = graph.meta.resolution
  return { nodes, edges, seed: graph.meta.seed, resolution: [w, h], skipped }
}

export interface Incompleteness {
  /** Node ids missing a required connection (or depending on one that is) —
   * excluded from what gets submitted to `/api/evaluate`. */
  excluded: Set<string>
  /** For each excluded node, the required input port names still unmet. */
  missing: Record<string, string[]>
}

/** A freshly-dropped or not-yet-wired node is an expected, transient canvas
 * state, not a broken graph — find nodes with an unmet *required* input (and
 * anything depending on them) so they can be excluded from evaluation and
 * shown as an informational badge instead of failing the whole graph. */
export function findIncomplete(nodes: GlitchNodeType[], edges: Edge[]): Incompleteness {
  const unmetRequired = (node: GlitchNodeType, excluded: Set<string>) =>
    node.data.descriptor.inputs
      .filter((port) => port.required)
      .filter((port) => {
        const edge = edges.find((e) => e.target === node.id && e.targetHandle === port.name)
        return !edge || excluded.has(edge.source)
      })

  const excluded = new Set<string>()
  let changed = true
  while (changed) {
    changed = false
    for (const node of nodes) {
      if (excluded.has(node.id)) continue
      if (unmetRequired(node, excluded).length > 0) {
        excluded.add(node.id)
        changed = true
      }
    }
  }

  const missing: Record<string, string[]> = {}
  for (const node of nodes) {
    if (!excluded.has(node.id)) continue
    missing[node.id] = unmetRequired(node, excluded).map((port) => port.name)
  }
  return { excluded, missing }
}
