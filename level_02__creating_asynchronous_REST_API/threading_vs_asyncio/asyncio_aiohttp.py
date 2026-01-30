import aiohttp
import asyncio

from decorators import measure_time_asyncio


async def fetch(session: aiohttp.ClientSession, url: str):
    async with session.get(url) as resp:
        return resp.status

@measure_time_asyncio
async def run_asyncio(url, times=10):
    async with aiohttp.ClientSession() as session:
        tasks = (fetch(session, url) for _ in range(times))
        results = await asyncio.gather(*tasks)
    print(f"Total received: {len(results)} responses")


if __name__ == "__main__":
    URL = "https://en.wikipedia.org/wiki/Fibonacci_sequence"
    TIMES = 100
    asyncio.run(run_asyncio(URL, TIMES))
