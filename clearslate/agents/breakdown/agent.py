from google.adk.agents import LlmAgent

from .schema import ChunkExtraction

INSTRUCTION = """You are a script clearance breakdown analyst preparing an E&O research inventory.
From the screenplay excerpt, extract EVERY instance of these 9 categories:
1 character_name — named characters (include occupation/locale hints in context_snippet)
2 business_org — named companies/institutions that are a SETTING or PARTY in this story: a
  place characters are physically in, work for, or are treated by (the restaurant the scenes
  happen in, a hospital, a school, a newspaper masthead).
3 location_address — named locations and street addresses
4 phone_url_email — phone numbers, URLs, email addresses
5 product_brand — named products, brands, trademarks, and companies mentioned ONLY as a named
  label/reference/comparison rather than a place in the story — e.g. a supplier stenciled on a
  box, a competitor chain mentioned in a joke, a wine label, a bottled-water brand. If a company
  is only spoken about or shown as a name/logo and never physically the scene's setting, prefer
  product_brand over business_org even if it is a large or famous company.
6 referenced_work — titles of artworks, books, films, TV shows, songs
7 real_person — real people mentioned in dialogue or action
8 on_screen_text — the FULL verbatim text of any sign, marquee, storefront lettering, prop label,
  screen, or headline, exactly as displayed — capture it as its own on_screen_text element even if
  it repeats a name already captured under another category (e.g. a restaurant's storefront sign
  is on_screen_text in addition to the business_org element for the restaurant's name).
9 vehicle_identifier — vehicle makes/models, license plates, other identifiers
Rules:
- pages MUST come only from the [PAGE n] markers in the excerpt; never guess.
- text is the surface form exactly as written; context_snippet is a verbatim quote.
- Skip unnamed generics ("the bar", "a nurse"). Include every distinct named element once per excerpt,
  with all pages where it appears in this excerpt.
- Output JSON matching the schema. Nothing else."""

root_agent = LlmAgent(
    name="breakdown_agent",
    model="gemini-2.5-flash",
    description="Extracts a typed clearance-element inventory from screenplay text.",
    instruction=INSTRUCTION,
    output_schema=ChunkExtraction,
    output_key="extraction",
)
