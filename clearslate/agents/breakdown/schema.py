from typing import Literal

from pydantic import BaseModel, Field

Category = Literal[
    "character_name", "business_org", "location_address", "phone_url_email",
    "product_brand", "referenced_work", "real_person", "on_screen_text", "vehicle_identifier",
]

class ExtractedElement(BaseModel):
    category: Category
    text: str = Field(description="The element exactly as written in the script")
    pages: list[int] = Field(description="Page numbers from [PAGE n] markers where it appears")
    scene: str | None = Field(default=None, description="Nearest preceding scene heading")
    context_snippet: str = Field(max_length=300, description="Verbatim line(s) of context, <=300 chars")

class ChunkExtraction(BaseModel):
    elements: list[ExtractedElement]
