import { Handle, type Node, type NodeProps, Position } from '@xyflow/react'
import type { NodeDescriptor } from '../types'

export interface GlitchNodeData {
  descriptor: NodeDescriptor
  label: string
  params: Record<string, unknown>
  [key: string]: unknown
}

export type GlitchNodeType = Node<GlitchNodeData, 'glitchNode'>

/** A canvas node: header (id + type) with typed input handles on the left and
 * output handles on the right, coloured per port type (colours come from the
 * backend catalog). */
export function GlitchNode({ data, selected }: NodeProps<GlitchNodeType>) {
  const { descriptor, label } = data
  return (
    <div className={`glitch-node${selected ? ' selected' : ''}`}>
      <div className="node-header">
        <span className="node-label">{label}</span>
        {label !== descriptor.title && <span className="node-type">{descriptor.title}</span>}
      </div>
      <div className="node-body">
        <div className="ports inputs">
          {descriptor.inputs.map((port) => (
            <div className="port-row" key={port.name} title={`${port.name}: ${port.type}`}>
              <Handle
                type="target"
                position={Position.Left}
                id={port.name}
                style={{ background: port.color }}
                className={port.required ? 'req' : 'opt'}
              />
              <span className="port-name">{port.name}</span>
            </div>
          ))}
        </div>
        <div className="ports outputs">
          {descriptor.outputs.map((port) => (
            <div className="port-row out" key={port.name} title={`${port.name}: ${port.type}`}>
              <span className="port-name">{port.name}</span>
              <Handle
                type="source"
                position={Position.Right}
                id={port.name}
                style={{ background: port.color }}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
