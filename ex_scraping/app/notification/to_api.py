import os

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.pricelog import pricelog as m_pricelog, command as p_cmd
from databases.sqldb.pricelog import repository as p_repo
from common.read_config import get_api_sending_options
from .constants import API_OPTIONS
from .enums import APIURLName
from .models import ParseInfosUpdate, ParseInfo, PriceUpdateResponse, APIPathOption


async def convert_pricelog_to_parseinfo(
    ses: AsyncSession,
    pricelog_list: list[m_pricelog.PriceLog],
) -> ParseInfosUpdate:
    urlrepo = p_repo.URLRepository(ses=ses)
    shoprepo = p_repo.ShopRepository(ses=ses)
    parseinfos = ParseInfosUpdate()
    for pricelog in pricelog_list:
        url = await urlrepo.get(command=p_cmd.URLGetCommand(id=pricelog.url_id))
        shop = await shoprepo.get(command=p_cmd.ShopGetCommand(id=pricelog.shop_id))
        if not url or not shop:
            raise ValueError(f"url or shop is None, url:{url}, shop:{shop}")
        pinfo = ParseInfo(
            url=url.url,
            name=pricelog.title,
            price=pricelog.price,
            condition=pricelog.condition,
            taxin=True,
            on_sale=pricelog.on_sale,
            salename=pricelog.salename,
            timestamp=pricelog.created_at,
            is_success=pricelog.is_success,
            storename=shop.name,
        )
        parseinfos.infos.append(pinfo)
    return parseinfos


def get_api_base_url():
    apisendopt = get_api_sending_options()
    return apisendopt.urls.base_url


async def send_to_api(ses: AsyncSession, pricelog_list: list[m_pricelog.PriceLog]):
    name = APIURLName.UPDATE_PRICE.value
    apiopt = APIPathOption(name=name, **API_OPTIONS[name])
    base_url = get_api_base_url()
    api_url = os.path.join(base_url, apiopt.path)

    try:
        parseinfos = await convert_pricelog_to_parseinfo(
            ses=ses, pricelog_list=pricelog_list
        )
    except Exception as e:
        return False, f"data convert error, {e}"
    async with httpx.AsyncClient() as client:
        try:
            match apiopt.method.lower():
                case "post":
                    res = await client.post(
                        api_url, json=parseinfos.model_dump(mode="json")
                    )
                case "patch":
                    res = await client.patch(
                        api_url, json=parseinfos.model_dump(mode="json")
                    )
                case "get":
                    res = await client.get(
                        api_url, params=parseinfos.model_dump(mode="json")
                    )
                case _:
                    raise ValueError(f"no support method, {apiopt.method.lower()}")
            res.raise_for_status()
        except Exception as e:
            return False, f"failed to api, {e}"
    res_json = res.json()
    if isinstance(res_json, list):
        if not res_json or len(res_json) > 1:
            return False, f"no data response or no suppoert response , {res_json}"
        res_json = res_json[0]
    if not isinstance(res_json, dict):
        return False, f"invalid type response, type:{type(res_json)}, {res_json}"
    priceupres = PriceUpdateResponse(**res_json)
    return priceupres.ok, priceupres.error_msg
