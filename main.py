import asyncio
from core.data_feed import stream_symbol
from core.symbols import get_top_symbols

async def main():
    symbols = get_top_symbols(20)
    print("Scanning:", symbols)

    tasks = [stream_symbol(symbol) for symbol in symbols]
    await asyncio.gather(*tasks)

asyncio.run(main())