import asyncio

from asyncio_aiohttp import run_asyncio
from threads import run_threads

URL = "https://en.wikipedia.org/wiki/Fibonacci_sequence"
TIMES = 500
asyncio.run(run_asyncio(URL, TIMES))
run_threads(URL, TIMES)
