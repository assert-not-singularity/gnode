import { type DragEvent, useMemo, useState } from 'react'
import type { NodeDescriptor } from '../types'

interface PaletteProps {
  catalog: NodeDescriptor[]
  loading: boolean
  error: string | null
  onAdd: (descriptor: NodeDescriptor) => void
}

/** Categorized, searchable node list. Drag an item onto the canvas or
 * double-click it to add a node. */
export function Palette({ catalog, loading, error, onAdd }: PaletteProps) {
  const [query, setQuery] = useState('')

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase()
    const filtered = q
      ? catalog.filter((n) => n.title.toLowerCase().includes(q) || n.type.toLowerCase().includes(q))
      : catalog
    const map = new Map<string, NodeDescriptor[]>()
    for (const node of filtered) {
      const list = map.get(node.category) ?? []
      list.push(node)
      map.set(node.category, list)
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [catalog, query])

  const onDragStart = (event: DragEvent<HTMLButtonElement>, type: string) => {
    event.dataTransfer.setData('application/gnode', type)
    event.dataTransfer.effectAllowed = 'move'
  }

  return (
    <aside className="palette">
      <input
        className="palette-search"
        placeholder="Search nodes…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        spellCheck={false}
      />
      {loading && <p className="muted small">Loading catalog…</p>}
      {error && <p className="error small">Backend offline? ({error})</p>}
      <div className="palette-list">
        {grouped.map(([category, items]) => (
          <div key={category} className="palette-group">
            <div className="palette-cat">{category}</div>
            {items.map((node) => (
              <button
                type="button"
                key={node.type}
                className="palette-item"
                draggable
                onDragStart={(e) => onDragStart(e, node.type)}
                onDoubleClick={() => onAdd(node)}
                title={`${node.type} — drag onto the canvas or double-click to add`}
              >
                {node.title}
              </button>
            ))}
          </div>
        ))}
      </div>
    </aside>
  )
}
