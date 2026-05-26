from langchain_core.tools import BaseTool

from .all_wines import make_all_wines_tool
from .cellar_overview import make_cellar_overview_tool
from .low_stock import make_flag_low_stock_tool
from .wine_by_field import make_wines_by_field_tool
from .wine_quantity import make_wine_count_tool

__all__ = [
    "make_all_wines_tool",
    "make_cellar_overview_tool",
    "make_flag_low_stock_tool",
    "make_wines_by_field_tool",
    "make_wine_count_tool",
]


def make_tools(user_id: str) -> list[BaseTool]:
    return [
        make_cellar_overview_tool(user_id),
        make_all_wines_tool(user_id),
        make_flag_low_stock_tool(user_id),
        make_wines_by_field_tool(user_id),
        make_wine_count_tool(user_id),
    ]
