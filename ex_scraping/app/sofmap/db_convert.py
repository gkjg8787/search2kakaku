from domain.models.pricelog import pricelog as m_pricelog
from sofmap.model import ParseResults, ParseResult


class DBModelConvert:

    @classmethod
    def parseresults_to_db_model(
        cls, results: ParseResults, remove_duplicate: bool = True
    ) -> list[m_pricelog.PriceLog]:
        if remove_duplicate:
            new_results = cls.remove_duplicates_of_parseresults(
                results=results, update_stock_quantity=True
            )
        else:
            new_results = results
        pl_results: list[m_pricelog.PriceLog] = []
        for parseresult in new_results.results:
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
                used_list_url=parseresult.used_list_url,
                sub_price=parseresult.sub_price,
                url=m_pricelog.URL(url=parseresult.url),
                shop=m_pricelog.Shop(name=parseresult.sitename),
            )
            pl_results.append(pricelog)
        return pl_results

    @classmethod
    def remove_duplicates_of_parseresults(
        cls, results: ParseResults, update_stock_quantity: bool = True
    ):
        """
        update_stock_quantity : stock_quantityが初期値ゼロの場合のみ更新する。元から値が入っている場合は変更しない。
        """

        def is_update_stock_quantity(p: ParseResult):
            return update_stock_quantity and p.stock_quantity == 0

        unique_results = ParseResults()
        unique_dict: dict[str, ParseResult] = {}
        update_stock_dict: dict[str, ParseResult] = {}
        exclude_value = {"shops_with_stock"}
        for result in results.results:
            result_str = result.model_dump_json(exclude=exclude_value)
            if not unique_results.results:
                unique_results.results.append(result)
                unique_dict[result_str] = result
                if is_update_stock_quantity(result):
                    result.stock_quantity = 1
                    update_stock_dict[result_str] = result
                continue
            if result_str in unique_dict:
                if update_stock_quantity and result_str in update_stock_dict:
                    unique_dict[result_str].stock_quantity += 1
                continue
            unique_results.results.append(result)
            unique_dict[result_str] = result
            if is_update_stock_quantity(result):
                result.stock_quantity = 1
                update_stock_dict[result_str] = result
        return unique_results
