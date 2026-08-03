import { categoryHue, categoryLabel } from "../categories"

interface CategoryChipProps {
  category: string
  size?: "sm" | "md"
}

/** Small colored pill for an element category. Hue-coded per categories.ts. */
export function CategoryChip({ category, size = "md" }: CategoryChipProps) {
  const hue = categoryHue(category)
  return (
    <span
      className={`category-chip category-chip--${size}`}
      style={{ "--chip-hue": hue } as React.CSSProperties}
    >
      {categoryLabel(category)}
    </span>
  )
}
