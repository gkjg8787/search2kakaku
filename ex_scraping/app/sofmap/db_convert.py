from domain.models.pricelog import pricelog as m_pricelog
from sofmap.model import ParseResults


class DBModelConvert:

    @classmethod
    def parseresults_to_db_model(
        cls, results: ParseResults
    ) -> list[m_pricelog.PriceLog]:
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
                point=parseresult.point,
                stock_quantity=parseresult.stock_quantity,
                shops_url=parseresult.shops_url,
                sub_price=parseresult.sub_price,
                url=m_pricelog.URL(url=parseresult.url),
                shop=m_pricelog.Shop(name=parseresult.sitename),
            )
            pl_results.append(pricelog)
        return pl_results
