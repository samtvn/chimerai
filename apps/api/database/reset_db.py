import argparse
import asyncio

from .drop_db import drop_db
from .init_db import init_db


async def reset_db(scenario: str = "default"):
    await drop_db()
    await init_db(scenario=scenario)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        type=str,
        default="default",
        help="Seeding scenario (e.g. default, red_focused, no_white)",
    )
    args = parser.parse_args()
    asyncio.run(reset_db(scenario=args.scenario))
