from pydantic import BaseModel


class GeminiSeleniumOptions(BaseModel):
    use_selenium: bool = False
    wait_css_selector: str | None = None
    page_load_timeout: int | None = None
    tag_wait_timeout: int | None = None
    page_wait_time: float | None = None


class AskGeminiOptions(BaseModel, extra="ignore"):
    sitename: str = ""
    label: str = ""
    selenium: GeminiSeleniumOptions | None = None
    recreate_parser: bool = False
