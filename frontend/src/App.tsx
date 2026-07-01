import { useMemo } from 'react'
import './App.css'
import { useNodes } from './hooks/useNodes'

export default function App() {
  const { nodes, loading, error } = useNodes()

  const byCategory = useMemo(() => {
    const map = new Map<string, { type: string; title: string }[]>()
    for (const node of nodes) {
      const list = map.get(node.category) ?? []
      list.push({ type: node.type, title: node.title })
      map.set(node.category, list)
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [nodes])

  return (
    <div className="app">
      <header className="app-header">
        <span className="app-logo">⬡</span>
        <span className="app-title">gnode</span>
        <span className="app-tag">node-based glitch editor</span>
      </header>

      <main className="app-body">
        {loading && <p className="muted">Loading node catalog…</p>}
        {error && (
          <p className="error">
            Could not load the catalog ({error}). Is the backend running? Start it with{' '}
            <code>make serve</code>.
          </p>
        )}
        {!loading && !error && (
          <>
            <p className="muted">
              {nodes.length} nodes across {byCategory.length} categories
            </p>
            <div className="catalog">
              {byCategory.map(([category, items]) => (
                <section key={category} className="cat">
                  <h2>{category}</h2>
                  <ul>
                    {items.map((node) => (
                      <li key={node.type}>{node.title}</li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  )
}
