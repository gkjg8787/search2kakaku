from domain.models.pricelog import pricelog as m_pricelog
from app.getdata.models import search as search_model


class DBModelConvert:

    @classmethod
    def searchresult_to_db_models(
        cls, results: search_model.SearchResults
    ) -> list[m_pricelog.PriceLog]:
        if not results.results:
            return []
        pl_results: list[m_pricelog.PriceLog] = []
        for parseresult in results.results:
            pricelog = m_pricelog.PriceLog(
                title=parseresult.title,
                price=parseresult.price,
                condition=parseresult.condition,
                on_sale=parseresult.on_sale,
                salename=parseresult.salename,
                is_success=parseresult.is_success,
                image_url=parseresult.image_url,
                stock_msg=parseresult.stock_msg,
                stock_quantity=parseresult.stock_quantity,
                url=m_pricelog.URL(url=parseresult.url),
                shop=m_pricelog.Shop(name=parseresult.sitename),
            )
            if parseresult.sub_urls:
                pricelog.used_list_url = parseresult.sub_urls[0]
            if parseresult.others.get("point"):
                pricelog.point = parseresult.others.get("point")
            if parseresult.others.get("sub_price"):
                pricelog.sub_price = parseresult.others.get("sub_price")
            pl_results.append(pricelog)
        return pl_results
