import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import apps.api.env  # noqa: F401
from apps.api.agents.subagents.inventory_audit import create_inventory_audit_agent
from apps.api.database.database import AsyncSessionLocal
from apps.api.database.dependencies import get_demo_user_id
from apps.api.database.models import cellar, menu, transactions, users, wines  # noqa: F401
from langchain_core.messages import HumanMessage


async def main():
    async with AsyncSessionLocal() as db:
        user_id = str(await get_demo_user_id(db))
        agent = create_inventory_audit_agent(db, user_id)
        config = {"configurable": {"thread_id": f"inventory-audit-test-{user_id}"}}

        query = "Summarize the current cellar state and flag any low-stock wines."
        print(f"Query: {query!r}\n")

        final_message = ""
        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=query)]},
            config=config,
            version="v2",
        ):
            kind = event.get("event")
            name = event.get("name", "")

            if kind == "on_chat_model_end":
                output = event.get("data", {}).get("output")
                if hasattr(output, "tool_calls") and not output.tool_calls:
                    final_message = output.content

            print(f"  {kind} | {name}")

        print(f"\nFinal: {final_message}\n")


if __name__ == "__main__":
    asyncio.run(main())
