import { CATEGORY_ORDER, categoryHue, categoryLabel } from "../categories"

interface CategoryFilterBarProps {
  counts: Record<string, number>
  active: string | null
  onChange: (category: string | null) => void
}

/** 9 category chips + "All", each showing a live count. */
export function CategoryFilterBar({ counts, active, onChange }: CategoryFilterBarProps) {
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0)

  return (
    <div className="filter-bar" role="tablist" aria-label="Filter by category">
      <button
        type="button"
        className={`filter-chip filter-chip--all ${active === null ? "is-active" : ""}`}
        onClick={() => onChange(null)}
        aria-pressed={active === null}
      >
        All <span className="filter-chip__count">{total}</span>
      </button>
      {CATEGORY_ORDER.map((category) => (
        <button
          key={category}
          type="button"
          className={`filter-chip ${active === category ? "is-active" : ""}`}
          style={{ "--chip-hue": categoryHue(category) } as React.CSSProperties}
          onClick={() => onChange(category)}
          aria-pressed={active === category}
        >
          {categoryLabel(category)} <span className="filter-chip__count">{counts[category] ?? 0}</span>
        </button>
      ))}
    </div>
  )
}
