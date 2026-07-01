// Typed fetch wrappers for the gnode backend API.

import type {
  EvaluateResult,
  GnodeGraph,
  GraphFileInfo,
  ImageUploadResult,
  NodeDescriptor,
  ValidationResult,
} from '../types'

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (body?.detail) detail = JSON.stringify(body.detail)
    } catch {
      // non-JSON error body — keep statusText
    }
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

const jsonHeaders = { 'Content-Type': 'application/json' }

export function fetchNodes(): Promise<NodeDescriptor[]> {
  return fetch('/api/nodes').then(asJson<NodeDescriptor[]>)
}

export function validateGraph(graph: GnodeGraph): Promise<ValidationResult> {
  return fetch('/api/validate', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(graph),
  }).then(asJson<ValidationResult>)
}

export function evaluateGraph(graph: GnodeGraph, targets: string[]): Promise<EvaluateResult> {
  return fetch('/api/evaluate', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ graph, targets }),
  }).then(asJson<EvaluateResult>)
}

export function uploadImage(file: File): Promise<ImageUploadResult> {
  const form = new FormData()
  form.append('file', file)
  return fetch('/api/images', { method: 'POST', body: form }).then(asJson<ImageUploadResult>)
}

export function listGraphs(): Promise<GraphFileInfo[]> {
  return fetch('/api/graphs').then(asJson<GraphFileInfo[]>)
}

export function saveGraph(filename: string, graph: GnodeGraph): Promise<{ filename: string }> {
  return fetch('/api/graphs', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ filename, graph }),
  }).then(asJson<{ filename: string }>)
}

export function loadGraph(filename: string): Promise<GnodeGraph> {
  return fetch(`/api/graphs/${encodeURIComponent(filename)}`).then(asJson<GnodeGraph>)
}
