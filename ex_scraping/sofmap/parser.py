from datetime import datetime, timezone
import re

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

NONE_PRICE = -1
NONE_POINT = 0
NONE_STOCK_NUM = 0
SOFMAP = "sofmap"


class ParseResult(BaseModel):
    title: str = ""
    price: int = NONE_PRICE
    condition: str = ""
    on_sale: bool = False
    salename: str = ""
    is_success: bool = False
    url: str = ""
    shopname: str = SOFMAP
    image_url: str = ""
    stock_msg: str = ""
    brand: str = ""
    release_date: str = ""
    point: int = NONE_POINT
    stock_quantity: int = NONE_STOCK_NUM
    shops_url: str = ""
    sub_price: int = NONE_PRICE


class ParseResults(BaseModel):
    results: list[ParseResult] = Field(default_factory=list)


class SofmapParser:
    html_str: str
    results: ParseResults

    def __init__(self, html_str: str):
        self.html_str = html_str
        self.results = []

    def get_results(self):
        return self.results

    def execute(self, url: str = ""):
        soup = BeautifulSoup(self.html_str, "html.parser")
        ptn = r"#change_style_list li"
        elems = soup.select(ptn)
        if not elems:
            return
        results = ParseResults()
        for elem in elems:
            result = ParseResult()
            result.image_url = self._get_image_url(elem)
            result.title = self._get_title(elem)
            result.price = self._get_price(elem)
            result.stock_msg = self._get_stock(elem)
            if "限定数終了" in result.stock_msg:
                result.is_success = False
            else:
                result.is_success = True
            result.brand = self._get_brand(elem)
            result.release_date = self._get_release_date(elem)
            result.point = self._get_point(elem)
            result.condition = self._get_condition(elem)
            result.shops_url, result.stock_quantity, result.sub_price = (
                self._get_stock_quantity(elem)
            )
            if url:
                result.url = url
            results.results.append(result)
        self.results = results

    @classmethod
    def _trim_str(cls, text: str) -> str:
        table = str.maketrans(
            {
                "\u3000": "",
                "\r": "",
                "\n": "",
                "\t": " ",
                "\xa0": " ",
            }
        )
        return text.translate(table).strip()

    def _get_image_url(self, elem) -> str:
        ptn = r"a.itemimg img"
        tag = elem.select_one(ptn)
        if not tag:
            return ""
        return tag["src"]

    def _get_title(self, elem) -> str:
        ptn = r"a.product_name"
        tag = elem.select_one(ptn)
        if not tag:
            return ""
        return self._trim_str(str(tag.text))

    def _get_price(self, elem) -> int:
        ptn = r"span.price"
        tag = elem.select_one(ptn)
        if not tag:
            return NONE_PRICE
        price = int(re.sub("\\D", "", tag.text))
        return price

    def _get_stock(self, elem) -> str:
        ptn = r".stock_review-box"
        tag = elem.select_one(ptn)
        if not tag:
            return ""
        return self._trim_str(str(tag.text))

    def _get_brand(self, elem) -> str:
        ptn = r".brand"
        tag = elem.select_one(ptn)
        if not tag:
            return ""
        return self._trim_str(str(tag.text))

    def _get_release_date(self, elem) -> str:
        ptn = r".date"
        tag = elem.select_one(ptn)
        if not tag:
            return ""
        return self._trim_str(str(tag.text))

    def _get_point(self, elem) -> int:
        ptn = r".point"
        tag = elem.select_one(ptn)
        if not tag:
            return NONE_POINT
        try:
            point = int(re.sub("\\D", "", tag.text))
        except Exception:
            return NONE_POINT
        return point

    def _get_condition(self, elem) -> str:
        ptn = r".ic.item-type.used"
        tag = elem.select_one(ptn)
        if not tag:
            return ""
        condition = self._trim_str(str(tag.text))

        rank_ptn = r"img.ic.usedrank"
        rank_tag = elem.select_one(rank_ptn)
        if not rank_tag:
            return condition
        rank_url = rank_tag["src"]
        match = re.search(r"usedrank_([A-Z])\.svg", rank_url)
        if match:
            extracted_char = match.group(1)
            if extracted_char:
                return f"Rank{extracted_char}"
        return condition

    def _get_stock_quantity(self, elem) -> tuple[str, int, int]:
        ptn = r".used_box.txt a"
        tag = elem.select_one(ptn)
        if not tag:
            return "", NONE_STOCK_NUM, NONE_PRICE
        if hasattr(tag, "href"):
            shops_url = tag["href"]
        else:
            shops_url = ""
        try:
            stock_num = int(re.sub("\\D", "", str(tag.find(string=True))))
        except Exception:
            return shops_url, NONE_STOCK_NUM, NONE_PRICE
        sub_price_tag = tag.select_one(r".price-txt")
        if not sub_price_tag:
            return shops_url, stock_num, NONE_PRICE
        try:
            sub_price = int(re.sub("\\D", "", str(sub_price_tag.text)))
        except Exception:
            return shops_url, stock_num, NONE_PRICE
        return shops_url, stock_num, sub_price
