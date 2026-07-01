// TypeScript mirror of the backend API contract (gnode.server.schemas + the
// node catalog descriptors from GET /api/nodes).

export interface PortInfo {
  name: string
  type: string
  color: string
  /** Present on input ports. */
  required?: boolean
}

export interface JsonSchemaProperty {
  type?: string
  title?: string
  default?: unknown
  description?: string
  enum?: (string | number)[]
  items?: { type?: string }
  anyOf?: JsonSchemaProperty[]
  $ref?: string
  properties?: Record<string, JsonSchemaProperty>
  required?: string[]
  // Widget hints emitted via json_schema_extra.
  widget?: string
  min?: number
  max?: number
  step?: number
  language?: string
  choices?: (string | number)[]
}

export interface JsonSchema {
  type?: string
  title?: string
  properties?: Record<string, JsonSchemaProperty>
  required?: string[]
  $defs?: Record<string, JsonSchemaProperty>
}

export interface NodeDescriptor {
  type: string
  category: string
  title: string
  inputs: PortInfo[]
  outputs: PortInfo[]
  params_schema: JsonSchema
}

// ── .gnode graph payload ──────────────────────────────────────────────
export interface GraphMeta {
  seed: number
  resolution: [number, number]
}

export interface GraphNodeData {
  id: string
  type: string
  params: Record<string, unknown>
  pos?: [number, number]
}

export interface GraphEdge {
  from: [string, string]
  to: [string, string]
}

export interface GnodeGraph {
  version?: string
  meta: GraphMeta
  nodes: GraphNodeData[]
  edges: GraphEdge[]
}

// ── API responses ─────────────────────────────────────────────────────
export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

export interface NodePreview {
  port: string
  kind: string
  data_url: string
  width: number
  height: number
}

export interface EvaluateResult {
  previews: Record<string, NodePreview>
  errors: Record<string, string>
}

export interface ImageUploadResult {
  image_id: string
  width: number
  height: number
}

export interface GraphFileInfo {
  name: string
  filename: string
}
