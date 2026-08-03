import type { Element, ElementCategory } from "./api"

export const CATEGORY_ORDER: ElementCategory[] = [
  "character_name",
  "business_org",
  "location_address",
  "phone_url_email",
  "product_brand",
  "referenced_work",
  "real_person",
  "on_screen_text",
  "vehicle_identifier",
]

interface CategoryMeta {
  label: string
  hue: number
}

// Distinct, muted hues spread around the wheel — read clearly as chips on a
// dark surface without shouting.
export const CATEGORY_META: Record<ElementCategory, CategoryMeta> = {
  character_name: { label: "Character", hue: 340 },
  business_org: { label: "Business / Org", hue: 208 },
  location_address: { label: "Location", hue: 152 },
  phone_url_email: { label: "Contact", hue: 184 },
  product_brand: { label: "Product / Brand", hue: 32 },
  referenced_work: { label: "Referenced Work", hue: 266 },
  real_person: { label: "Real Person", hue: 6 },
  on_screen_text: { label: "On-Screen Text", hue: 224 },
  vehicle_identifier: { label: "Vehicle ID", hue: 66 },
}

export function categoryLabel(category: string): string {
  return CATEGORY_META[category as ElementCategory]?.label ?? category
}

export function categoryHue(category: string): number {
  return CATEGORY_META[category as ElementCategory]?.hue ?? 0
}

/** Counts elements per category, with every known category present (0 if absent). */
export function countByCategory(elements: Element[]): Record<ElementCategory, number> {
  const counts = Object.fromEntries(CATEGORY_ORDER.map((c) => [c, 0])) as Record<
    ElementCategory,
    number
  >
  for (const el of elements) {
    if (el.category in counts) counts[el.category] += 1
  }
  return counts
}
