from google.adk.agents import LlmAgent

from .schema import ChunkExtraction

INSTRUCTION = """You are a script clearance breakdown analyst preparing an E&O research inventory.
From the screenplay excerpt, extract EVERY instance of these 9 categories:
1 character_name — named characters (include occupation/locale hints in context_snippet)
2 business_org — named companies, schools, bars, hospitals, organizations
3 location_address — named locations and street addresses
4 phone_url_email — phone numbers, URLs, email addresses
5 product_brand — named products, brands, trademarks
6 referenced_work — titles of artworks, books, films, TV shows, songs
7 real_person — real people mentioned in dialogue or action
8 on_screen_text — signage, props, newspaper headlines, any text seen on screen
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
