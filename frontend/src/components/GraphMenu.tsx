import { useCallback, useEffect, useState } from 'react'
import { listGraphs, loadGraph, saveGraph } from '../api/client'
import type { GnodeGraph, GraphFileInfo } from '../types'

interface GraphMenuProps {
  /** Build the current canvas as a `.gnode` payload (for save / export). */
  getGraph: () => GnodeGraph
  onLoad: (graph: GnodeGraph, name: string) => void
  onNew: () => void
  hasNodes: boolean
  notify: (message: string, kind?: 'info' | 'error') => void
}

/** Trigger a browser download of `text` as a file named `filename`. */
function downloadText(filename: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/** Header controls for graph persistence: New, name + Save, Load, and export. */
export function GraphMenu({ getGraph, onLoad, onNew, hasNodes, notify }: GraphMenuProps) {
  const [name, setName] = useState('untitled')
  const [saved, setSaved] = useState<GraphFileInfo[]>([])

  const refresh = useCallback(() => {
    listGraphs()
      .then(setSaved)
      .catch(() => {
        /* listing is best-effort; leave the previous list */
      })
  }, [])

  useEffect(refresh, [refresh])

  const onSave = async () => {
    const trimmed = name.trim()
    if (!trimmed) {
      notify('Enter a name before saving', 'error')
      return
    }
    const filename = trimmed.endsWith('.gnode') ? trimmed : `${trimmed}.gnode`
    try {
      const result = await saveGraph(filename, getGraph())
      notify(`Saved ${result.filename}`)
      refresh()
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err), 'error')
    }
  }

  const onPick = async (filename: string) => {
    if (!filename) return
    try {
      const graph = await loadGraph(filename)
      const stem = filename.replace(/\.gnode$/, '')
      onLoad(graph, stem)
      setName(stem)
      notify(`Loaded ${filename}`)
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err), 'error')
    }
  }

  const onNewClick = () => {
    if (hasNodes && !window.confirm('Clear the canvas? Unsaved changes will be lost.')) return
    onNew()
  }

  const onExport = () => {
    const trimmed = name.trim() || 'untitled'
    downloadText(`${trimmed}.gnode`, JSON.stringify(getGraph(), null, 2), 'application/json')
  }

  return (
    <div className="graph-menu">
      <button type="button" className="gm-btn" onClick={onNewClick}>
        New
      </button>
      <input
        className="gm-name"
        type="text"
        aria-label="Graph name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <button type="button" className="gm-btn" onClick={onSave}>
        Save
      </button>
      <select
        className="gm-load"
        aria-label="Load a saved graph"
        value=""
        onChange={(e) => onPick(e.target.value)}
      >
        <option value="">Load…</option>
        {saved.map((g) => (
          <option key={g.filename} value={g.filename}>
            {g.name}
          </option>
        ))}
      </select>
      <button type="button" className="gm-btn" onClick={onExport} disabled={!hasNodes}>
        Export .gnode
      </button>
    </div>
  )
}
