import { type ChangeEvent, useState } from 'react'
import { uploadImage } from '../api/client'
import type { JsonSchema, JsonSchemaProperty, NodePreview } from '../types'

interface ConfigPanelProps {
  nodeId: string
  title: string
  schema: JsonSchema
  params: Record<string, unknown>
  onChange: (params: Record<string, unknown>) => void
  onClose: () => void
  /** The node's last rendered output, if any (enables PNG export + compare). */
  preview?: NodePreview
  onCompare?: () => void
}

/** Side panel that renders a node's params from its JSON Schema + widget hints
 * (emitted by the backend's typed field factories) into typed controls. */
export function ConfigPanel({
  nodeId,
  title,
  schema,
  params,
  onChange,
  onClose,
  preview,
  onCompare,
}: ConfigPanelProps) {
  const properties = schema.properties ?? {}
  const update = (key: string, value: unknown) => onChange({ ...params, [key]: value })

  return (
    <aside className="config-panel">
      <div className="config-header">
        <div className="config-heading">
          <h3>{title}</h3>
          <span className="config-id">{nodeId}</span>
        </div>
        <button
          type="button"
          className="config-close"
          onClick={onClose}
          aria-label="Close config panel"
        >
          ×
        </button>
      </div>
      <div className="config-body">
        {Object.keys(properties).length === 0 && <p className="muted small">No parameters.</p>}
        {Object.entries(properties).map(([key, prop]) => (
          <Field
            key={key}
            name={key}
            prop={prop}
            value={params[key]}
            onChange={(v) => update(key, v)}
          />
        ))}
      </div>
      {preview && (
        <div className="config-actions">
          <button type="button" className="gm-btn" onClick={onCompare}>
            ⤢ Compare
          </button>
          <a className="gm-btn" href={preview.data_url} download={`${nodeId}.png`}>
            ⤓ PNG
          </a>
        </div>
      )}
    </aside>
  )
}

/** Unwrap a Pydantic Optional (`anyOf: [X, null]`) to its effective property,
 * carrying the outer title/default/widget hints. */
function unwrap(prop: JsonSchemaProperty): { effective: JsonSchemaProperty; nullable: boolean } {
  if (prop.anyOf) {
    const nonNull = prop.anyOf.filter((p) => p.type !== 'null')
    if (nonNull.length === 1) {
      return {
        effective: {
          ...nonNull[0],
          title: prop.title ?? nonNull[0].title,
          default: prop.default,
          description: prop.description ?? nonNull[0].description,
          widget: prop.widget ?? nonNull[0].widget,
          min: prop.min ?? nonNull[0].min,
          max: prop.max ?? nonNull[0].max,
          step: prop.step ?? nonNull[0].step,
          choices: prop.choices ?? nonNull[0].choices,
          language: prop.language ?? nonNull[0].language,
        },
        nullable: true,
      }
    }
  }
  return { effective: prop, nullable: false }
}

function hexToRgb(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

function rgbToHex(rgb: number[]): string {
  const [r, g, b] = rgb.map((c) => Math.max(0, Math.min(255, Math.round(c))))
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`
}

interface FieldProps {
  name: string
  prop: JsonSchemaProperty
  value: unknown
  onChange: (value: unknown) => void
}

function Field({ name, prop, value, onChange }: FieldProps) {
  const { effective, nullable } = unwrap(prop)
  const label = effective.title ?? name
  // Only fall back to the default when the value was never set; an explicit
  // null must survive (so nullable fields can render as "none"/empty).
  const current = value === undefined ? effective.default : value
  const id = `param-${name}`

  if (name === 'image_id') {
    return <ImageIdField id={id} label={label} value={current} onChange={onChange} />
  }

  const labelEl = (
    <label htmlFor={id}>
      {label}
      {typeof current === 'number' && effective.widget === 'slider' && (
        <span className="field-val">{current}</span>
      )}
    </label>
  )

  if (effective.widget === 'slider') {
    const num = typeof current === 'number' ? current : Number(effective.default ?? 0)
    return (
      <div className="field">
        {labelEl}
        <input
          id={id}
          type="range"
          min={effective.min}
          max={effective.max}
          step={effective.step}
          value={num}
          onChange={(e) => onChange(Number(e.target.value))}
        />
      </div>
    )
  }

  if (effective.widget === 'seed') {
    const num = typeof current === 'number' ? current : ''
    return (
      <div className="field">
        <label htmlFor={id}>{label}</label>
        <div className="field-row">
          <input
            id={id}
            type="number"
            placeholder="(from global seed)"
            value={num}
            onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
          />
          <button
            type="button"
            className="reroll"
            title="Reroll"
            onClick={() => onChange(Math.floor(Math.random() * 1_000_000_000))}
          >
            🎲
          </button>
        </div>
      </div>
    )
  }

  if (effective.widget === 'color') {
    const rgb = Array.isArray(current) ? (current as number[]) : [0, 0, 0]
    return (
      <div className="field">
        <label htmlFor={id}>{label}</label>
        <input
          id={id}
          type="color"
          value={rgbToHex(rgb)}
          onChange={(e) => onChange(hexToRgb(e.target.value))}
        />
      </div>
    )
  }

  if (effective.widget === 'vec2') {
    const vec = Array.isArray(current) ? (current as number[]) : [0, 0]
    return (
      <fieldset className="field vec2-field">
        <legend>{label}</legend>
        <div className="field-row">
          {[0, 1].map((i) => (
            <input
              key={i}
              type="number"
              aria-label={`${label} ${i === 0 ? 'x' : 'y'}`}
              value={vec[i] ?? 0}
              onChange={(e) => {
                const next = [...vec]
                next[i] = Number(e.target.value)
                onChange(next)
              }}
            />
          ))}
        </div>
      </fieldset>
    )
  }

  if (effective.widget === 'code') {
    return (
      <div className="field">
        <label htmlFor={id}>{label}</label>
        <textarea
          id={id}
          className="code-field"
          spellCheck={false}
          rows={8}
          value={typeof current === 'string' ? current : ''}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    )
  }

  if (effective.enum) {
    const numeric = effective.enum.every((v) => typeof v === 'number')
    return (
      <div className="field">
        <label htmlFor={id}>{label}</label>
        <select
          id={id}
          value={String(current ?? '')}
          onChange={(e) => {
            const v = e.target.value
            if (v === '') return onChange(null)
            onChange(numeric ? Number(v) : v)
          }}
        >
          {nullable && <option value="">— none —</option>}
          {effective.enum.map((opt) => (
            <option key={String(opt)} value={String(opt)}>
              {String(opt)}
            </option>
          ))}
        </select>
      </div>
    )
  }

  switch (effective.type) {
    case 'boolean':
      return (
        <div className="field field-check">
          <label htmlFor={id}>
            <input
              id={id}
              type="checkbox"
              checked={Boolean(current)}
              onChange={(e) => onChange(e.target.checked)}
            />
            {label}
          </label>
        </div>
      )
    case 'integer':
    case 'number':
      return (
        <div className="field">
          <label htmlFor={id}>{label}</label>
          <input
            id={id}
            type="number"
            min={effective.min}
            max={effective.max}
            step={effective.step}
            value={typeof current === 'number' ? current : ''}
            onChange={(e) => {
              const raw = e.target.value
              if (raw === '') return onChange(nullable ? null : (effective.default ?? 0))
              onChange(Number(raw))
            }}
          />
        </div>
      )
    case 'string':
      return (
        <div className="field">
          <label htmlFor={id}>{label}</label>
          <input
            id={id}
            type="text"
            value={typeof current === 'string' ? current : ''}
            onChange={(e) => onChange(e.target.value)}
          />
        </div>
      )
    default:
      return <JsonField id={id} label={label} value={current} onChange={onChange} />
  }
}

/** Upload an image and store the returned id (used for `io.load_image`). */
function ImageIdField({
  id,
  label,
  value,
  onChange,
}: {
  id: string
  label: string
  value: unknown
  onChange: (value: unknown) => void
}) {
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState<string | null>(null)

  const onFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    // Reset so picking the same file again still fires onChange.
    event.target.value = ''
    if (!file) return
    setBusy(true)
    setFailed(null)
    try {
      const result = await uploadImage(file)
      onChange(result.image_id)
    } catch (err) {
      setFailed(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        placeholder="image id (or upload)"
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="field-row upload-row">
        <label className="upload-btn">
          upload…
          <input type="file" accept="image/*" onChange={onFile} hidden />
        </label>
        {busy && <span className="muted small">uploading…</span>}
        {failed && <span className="error small">{failed}</span>}
      </div>
    </div>
  )
}

/** Fallback for arrays/objects (e.g. gradient-map stops): edit as JSON. */
function JsonField({
  id,
  label,
  value,
  onChange,
}: {
  id: string
  label: string
  value: unknown
  onChange: (value: unknown) => void
}) {
  return (
    <div className="field">
      <label htmlFor={id}>
        {label} <span className="muted small">(JSON)</span>
      </label>
      <textarea
        id={id}
        className="code-field"
        spellCheck={false}
        rows={4}
        defaultValue={value == null ? '' : JSON.stringify(value)}
        onBlur={(e) => {
          try {
            onChange(JSON.parse(e.target.value))
          } catch {
            /* keep last valid value on parse error */
          }
        }}
      />
    </div>
  )
}
