from typing import List

from sqlmodel import Field, Relationship

from domain.models.base_model import SQLBase

from common import constants


class URL(SQLBase, table=True):
    url: str = Field(default="", index=True)

    logs: List["PriceLog"] = Relationship(back_populates="url")


class Shop(SQLBase, table=True):
    name: str = Field(index=True)

    logs: List["PriceLog"] = Relationship(back_populates="shop")


class PriceLog(SQLBase, table=True):
    title: str = Field(index=True)
    price: int
    condition: str
    on_sale: bool = Field(default=False)
    salename: str = Field(default="")
    is_success: bool
    image_url: str
    stock_msg: str
    point: int = Field(default=constants.NONE_POINT)
    stock_quantity: int = Field(default=constants.NONE_STOCK_NUM)
    shops_url: str = Field(default="")
    sub_price: int = Field(default=constants.NONE_PRICE)

    url_id: int | None = Field(default=None, foreign_key="url.id")
    url: URL | None = Relationship(back_populates="logs")
    shop_id: int | None = Field(default=None, foreign_key="shop.id")
    shop: Shop | None = Relationship(back_populates="logs")
