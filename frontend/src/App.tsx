import {
  addEdge,
  Background,
  type Connection,
  Controls,
  type Edge,
  type IsValidConnection,
  MiniMap,
  type NodeMouseHandler,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { type DragEvent, useCallback, useMemo, useRef, useState } from 'react'
import './App.css'
import { ConfigPanel } from './components/ConfigPanel'
import { GlitchNode, type GlitchNodeType } from './components/GlitchNode'
import { Palette } from './components/Palette'
import { useNodes } from './hooks/useNodes'
import type { NodeDescriptor } from './types'

const nodeTypes = { glitchNode: GlitchNode }

/** Short base name for a node id, e.g. "displace.band" -> "band". */
function baseName(type: string): string {
  return type.split('.').pop() ?? type
}

function Editor() {
  const { nodes: catalog, loading, error } = useNodes()
  const byType = useMemo(() => new Map(catalog.map((n) => [n.type, n])), [catalog])

  const [nodes, setNodes, onNodesChange] = useNodesState<GlitchNodeType>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { screenToFlowPosition } = useReactFlow()
  const canvasRef = useRef<HTMLDivElement>(null)

  const addNode = useCallback(
    (descriptor: NodeDescriptor, position: { x: number; y: number }) => {
      setNodes((current) => {
        const ids = new Set(current.map((n) => n.id))
        const base = baseName(descriptor.type)
        let i = 1
        while (ids.has(`${base}_${i}`)) i++
        const id = `${base}_${i}`
        const node: GlitchNodeType = {
          id,
          type: 'glitchNode',
          position,
          data: { descriptor, label: id, params: {} },
        }
        return [...current, node]
      })
    },
    [setNodes],
  )

  const addFromPalette = useCallback(
    (descriptor: NodeDescriptor) => {
      const bounds = canvasRef.current?.getBoundingClientRect()
      const jitter = () => (Math.random() - 0.5) * 90
      const position = bounds
        ? screenToFlowPosition({
            x: bounds.x + bounds.width / 2 + jitter(),
            y: bounds.y + bounds.height / 3 + jitter(),
          })
        : { x: 200, y: 150 }
      addNode(descriptor, position)
    },
    [addNode, screenToFlowPosition],
  )

  const onDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault()
      const descriptor = byType.get(event.dataTransfer.getData('application/gnode'))
      if (!descriptor) return
      addNode(descriptor, screenToFlowPosition({ x: event.clientX, y: event.clientY }))
    },
    [byType, addNode, screenToFlowPosition],
  )

  // Mirrors the backend's can_connect policy: exact type match, ANY as wildcard.
  const isValidConnection: IsValidConnection<Edge> = useCallback(
    (conn) => {
      const source = nodes.find((n) => n.id === conn.source)
      const target = nodes.find((n) => n.id === conn.target)
      const out = source?.data.descriptor.outputs.find((p) => p.name === conn.sourceHandle)
      const inp = target?.data.descriptor.inputs.find((p) => p.name === conn.targetHandle)
      if (!out || !inp) return false
      return out.type === 'ANY' || inp.type === 'ANY' || out.type === inp.type
    },
    [nodes],
  )

  const onConnect = useCallback(
    (conn: Connection) => setEdges((eds) => addEdge(conn, eds)),
    [setEdges],
  )

  const onNodeClick: NodeMouseHandler<GlitchNodeType> = useCallback(
    (_event, node) => setSelectedId(node.id),
    [],
  )
  const onPaneClick = useCallback(() => setSelectedId(null), [])

  const setParams = useCallback(
    (nodeId: string, params: Record<string, unknown>) => {
      setNodes((current) =>
        current.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, params } } : n)),
      )
    },
    [setNodes],
  )

  const selected = selectedId ? nodes.find((n) => n.id === selectedId) : undefined

  return (
    <div className="app">
      <header className="app-header">
        <span className="app-logo">⬡</span>
        <span className="app-title">gnode</span>
        <span className="app-tag">node-based glitch editor</span>
      </header>
      <div
        className="editor"
        style={{ gridTemplateColumns: selected ? '240px 1fr 300px' : '240px 1fr' }}
      >
        <Palette catalog={catalog} loading={loading} error={error} onAdd={addFromPalette} />
        {/* biome-ignore lint/a11y/noStaticElementInteractions: the canvas is a drag-and-drop drop target; keyboard interaction is handled by React Flow */}
        <div className="canvas" ref={canvasRef} onDrop={onDrop} onDragOver={onDragOver}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            isValidConnection={isValidConnection}
            nodeTypes={nodeTypes}
            defaultViewport={{ x: 0, y: 0, zoom: 1 }}
            minZoom={0.2}
            deleteKeyCode={['Backspace', 'Delete']}
          >
            <Background gap={16} size={1} color="#1e293b" />
            <Controls />
            <MiniMap zoomable pannable nodeColor="#334155" maskColor="rgba(0,0,0,0.6)" />
          </ReactFlow>
        </div>
        {selected && (
          <ConfigPanel
            key={selected.id}
            nodeId={selected.id}
            title={selected.data.descriptor.title}
            schema={selected.data.descriptor.params_schema}
            params={selected.data.params}
            onChange={(params) => setParams(selected.id, params)}
            onClose={() => setSelectedId(null)}
          />
        )}
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ReactFlowProvider>
      <Editor />
    </ReactFlowProvider>
  )
}
