from redis import asyncio as aioredis
# from vk_api_lib.classes.states import State


class FSM:
    async def get(self, key: str): pass
    async def set(self, key: str, value): pass
    async def set_hash(self, key: str, data: dict): pass
    async def get_hash(self, key: str) -> dict: pass
    async def delete(self, key: str): pass
    async def init_redis(self, url: str = "redis://localhost", db: int = 1): pass
    def get_context(self, peer_id: int, user_id: int): pass


class SimpleRedisFSM(FSM):
    def __init__(
            self,
            prefix: str = 'vk_fsm_'):
        self.prefix = prefix
        self.redis = None

    async def init_redis(self, url: str = "redis://localhost", db: int = 1):
        self.redis = await aioredis.from_url(url, encoding='utf-8', db=db, decode_responses=True)

    async def get(self, key: str):
        return await self.redis.get(self.prefix + key)

    async def set(self, key: str, value):
        await self.redis.set(self.prefix + key, value)

    async def set_hash(self, key: str, data: dict):
        await self.redis.hmset(self.prefix + key, data)

    async def get_hash(self, key: str) -> dict:
        return await self.redis.hgetall(self.prefix + key)

    async def delete(self, key: str):
        return await self.redis.delete(self.prefix + key)

    def get_context(self, peer_id: int, user_id: int):
        return FSMContext(
            self, peer_id, user_id
        )


class FSMContext:
    def __init__(self, fsm: FSM, peer_id: int, user_id: int):
        self.peer_id = peer_id
        self.user_id = user_id
        self.fsm = fsm
        self.key = f'{peer_id}_{user_id}'

    async def set_data(self, **kwargs):
        postfix = 'data'
        if not kwargs:
            return
        await self.fsm.set_hash(self.key + postfix, kwargs)

    async def get_data(self):
        postfix = 'data'
        data = await self.fsm.get_hash(self.key + postfix)
        if data is None:
            data = {}
        return data

    # async def set_state_form(self, form: StateForm):
    #     postfix = 'state'
    #     state_name = form.states[0].__name__
    #     await self.fsm.set(self.key + postfix, StateForm.__name__ + ';' + state_name)
    #     await self.fsm.set()

    async def get_state(self):
        postfix = 'state'
        return await self.fsm.get(self.key + postfix)

    async def set_state(self, state: 'State'):
        postfix = 'state'
        return await self.fsm.set(self.key + postfix, state.name)

    async def drop_state(self):
        postfix = 'state'
        return await self.fsm.delete(self.key + postfix)

    async def drop_data(self):
        postfix = 'data'
        return await self.fsm.delete(self.key + postfix)

    async def update_data(self, **kwargs):
        data: dict = await self.get_data()
        if data:
            data.update(kwargs)
            await self.set_data(**data)
        else:
            await self.set_data(**kwargs)


