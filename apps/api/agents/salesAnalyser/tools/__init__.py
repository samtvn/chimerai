from langchain_core.tools import BaseTool

from .sales_history import make_sales_history_tool
from .top_movers import make_top_movers_tool
from .top_sellers import make_top_sellers_tool

__all__ = [
    "make_sales_history_tool",
    "make_top_movers_tool",
    "make_top_sellers_tool",
]


def make_tools(user_id: str) -> list[BaseTool]:
    return [
        make_sales_history_tool(user_id),
        make_top_movers_tool(user_id),
        make_top_sellers_tool(user_id),
    ]
