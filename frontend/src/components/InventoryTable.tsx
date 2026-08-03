import { useMemo } from "react"
import type { Element } from "../api"
import { CategoryChip } from "./CategoryChip"

interface InventoryTableProps {
  elements: Element[]
  filter: string | null
}

function firstPage(el: Element): number {
  return el.pages.length > 0 ? Math.min(...el.pages) : Number.MAX_SAFE_INTEGER
}

/** Page-ordered element inventory with category filter and the Phase 2 gate button. */
export function InventoryTable({ elements, filter }: InventoryTableProps) {
  const rows = useMemo(() => {
    const filtered = filter ? elements.filter((el) => el.category === filter) : elements
    return [...filtered].sort((a, b) => firstPage(a) - firstPage(b))
  }, [elements, filter])

  return (
    <div className="inventory-table">
      <div className="inventory-table__scroll">
        <table>
          <thead>
            <tr>
              <th className="col-pages">Pages</th>
              <th className="col-category">Category</th>
              <th className="col-text">Text</th>
              <th className="col-scene">Scene</th>
              <th className="col-snippet">Context</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((el) => (
              <tr key={el.id}>
                <td className="col-pages">{el.pages.join(", ")}</td>
                <td className="col-category">
                  <CategoryChip category={el.category} size="sm" />
                </td>
                <td className="col-text">{el.text}</td>
                <td className="col-scene">{el.scene ?? "—"}</td>
                <td className="col-snippet" title={el.context_snippet}>
                  {el.context_snippet}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="inventory-table__empty" colSpan={5}>
                  No elements match this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="inventory-table__footer">
        <span className="inventory-table__count">
          {filter ? `${rows.length} of ${elements.length}` : elements.length} elements extracted
        </span>
        <div className="inventory-table__start" title="Research phase coming in Phase 2">
          <button type="button" className="button button--primary" disabled>
            Start research
          </button>
          <span className="inventory-table__start-caption">
            Research phase coming in Phase 2
          </span>
        </div>
      </div>
    </div>
  )
}
