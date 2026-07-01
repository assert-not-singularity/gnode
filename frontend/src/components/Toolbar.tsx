interface ToolbarProps {
  seed: number
  onSeed: (seed: number) => void
  resolution: [number, number]
  onResolution: (resolution: [number, number]) => void
  status: string
}

/** Global controls: graph seed (+ reroll), output size, and evaluate status. */
export function Toolbar({ seed, onSeed, resolution, onResolution, status }: ToolbarProps) {
  return (
    <div className="toolbar">
      <label className="tb-field">
        <span>seed</span>
        <input type="number" value={seed} onChange={(e) => onSeed(Number(e.target.value))} />
      </label>
      <button
        type="button"
        className="reroll"
        title="Reroll global seed"
        onClick={() => onSeed(Math.floor(Math.random() * 1_000_000_000))}
      >
        🎲
      </button>
      <label className="tb-field">
        <span>size</span>
        <input
          type="number"
          aria-label="height"
          value={resolution[0]}
          onChange={(e) => onResolution([Number(e.target.value), resolution[1]])}
        />
        <span className="tb-x">×</span>
        <input
          type="number"
          aria-label="width"
          value={resolution[1]}
          onChange={(e) => onResolution([resolution[0], Number(e.target.value)])}
        />
      </label>
      {status && (
        <span className={`tb-status status-${status.replace(/\W+/g, '-')}`}>{status}</span>
      )}
    </div>
  )
}
