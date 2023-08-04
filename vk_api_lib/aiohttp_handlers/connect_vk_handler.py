from aiohttp import web

from loader import logger

GROUP_ID: int = 220338985
RETURN_STRING: str = 'b3d69462'


async def connect_vk(req: web.Request) -> web.Response:
    data = await req.json()
    logger.warning(data)
    if data['type'] == "confirmation" and data["group_id"] == GROUP_ID:
        return web.Response(text=RETURN_STRING)
    else:
        return web.Response()
