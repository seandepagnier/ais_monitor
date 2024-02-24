import asyncio
import wireless
import decode_ais

import gc, os, micropython
async def test1():



loop = asyncio.get_event_loop()
loop.create_task(test1())
loop.create_task(test2())
loop.create_task(test3())
loop.run_forever()
