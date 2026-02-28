import asyncio
from core.data_feed import stream_symbol, db_worker
from core.symbols import get_top_symbols

async def main():
    # Start DB worker FIRST
    asyncio.create_task(db_worker())

    # Get top symbols
    symbols = get_top_symbols(20)
    print("Scanning:", symbols)

    # Start symbol streams
    tasks = [stream_symbol(symbol) for symbol in symbols]

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())