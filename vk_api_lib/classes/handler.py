import traceback
from typing import Callable

from aiohttp import web

from config import VK_SECRET
from loader import logger
from vk_api_lib.classes.boardpost import BoardPost
from vk_api_lib.classes.FSM import FSM, FSMContext
from vk_api_lib.classes.callback import Callback
from vk_api_lib.classes.callback_data import CallbackData
from vk_api_lib.classes.filters import Filter, UseAsyncCheck
from vk_api_lib.classes.message import Message
from vk_api_lib.classes.update import Update


class MainHandler:
    def __init__(self, fsm: FSM, filters: list[Filter]):
        self.message_handlers: list[MessageHandler] = []
        self.callback_handlers: list[CallbackHandler] = []
        self.board_handlers: list[BoardHandler] = []
        self.bot = None
        self.fsm = fsm
        self.callback_datas = {}
        self.filters = filters

    def register_callback_data(self):
        for cb in CallbackData.__subclasses__():
            self.callback_datas[cb.__name__] = cb

    def board_post_handler(self, *filters: Filter):

        def wrapper_1(func: Callable):
            async def wrapper_2(post: BoardPost, fsm: FSMContext):
                if not post:
                    return
                try:
                    await func(post, fsm=fsm)
                except Exception as e:
                    logger.error(
                        f'f"EXCEPTION {traceback.format_exc()} - - - VkBot user_id: {post.user_id} board post"')
                else:
                    logger.info(f"VkBot user_id: {post.user_id} board post")

            handler = BoardHandler(wrapper_2, *filters)
            self.board_handlers.append(handler)
            return wrapper_2

        return wrapper_1

    def callback_handler(self, *filters: Filter):

        def wrapper_1(func: Callable):

            async def wrapper_2(callback: Callback, fsm: FSMContext):
                try:
                    await func(callback, fsm=fsm)
                except Exception as e:
                    logger.error(f'f"EXCEPTION {traceback.format_exc()} - - - VkBot callback user_id: {callback.message.user_id} data: {callback.callback_data}"')
                else:
                    logger.info(f"VkBot callback user_id: {callback.message.user_id} data: {callback.callback_data}")

            handler = CallbackHandler(wrapper_2, *filters)
            self.callback_handlers.append(handler)

            return wrapper_2

        return wrapper_1

    def message_handler(self, *filters: Filter):
        def wrapper_1(func: Callable):
            async def wrapper_2(message: Message, fsm: FSMContext):
                if not message:
                    return
                try:
                    await func(message, fsm=fsm)

                except Exception as e:
                    logger.error(
                        f'f"EXCEPTION {traceback.format_exc()} - - - VkBot user_id: {message.user_id} text: {message.text}"'
                    )
                else:
                    logger.info(f"VkBot user_id: {message.user_id} text: {message.text}")

            handler = MessageHandler(wrapper_2, *filters)
            self.message_handlers.append(handler)
            return wrapper_2

        return wrapper_1

    def get_context(self, data: dict) -> FSMContext:
        message = data.get('message')

        if message:
            user_id = message['from_id']
            peer_id = message['peer_id']
        else:
            user_id = data['user_id']
            peer_id = data['peer_id']

        return self.fsm.get_context(peer_id, user_id)

    async def check_message_handlers(self, message: dict) -> bool:
        fsm_context = self.get_context(message)
        message = Message.from_message_handler(message, self.bot)

        for handler in self.message_handlers:
            handler: MessageHandler

            if await handler.check(update=message, fsm=fsm_context, filters=self.filters):
                await handler.run_func(message=message, fsm=fsm_context)
                return True
        return False

    async def check_callback_handlers(self, callback: dict) -> bool:
        fsm_context = self.get_context(callback)
        callback_data_class = self.callback_datas[tuple(callback['payload'].keys())[0]]
        callback: Callback = await Callback.parse(
            callback, callback_data_class, self.bot
        )
        for handler in self.callback_handlers:
            handler: CallbackHandler

            if await handler.check(update=callback, fsm=fsm_context, filters=self.filters):
                if not callback:
                    return False
                await handler.run_func(callback=callback, fsm=fsm_context)
                return True
        return False

    async def check_board_handlers(self, update: dict) -> bool:
        fsm_context = self.fsm.get_context(update['from_id'], update['from_id'])
        post: BoardPost = BoardPost.from_update(update)
        for handler in self.board_handlers:
            handler: BoardHandler
            if await handler.check(update=post, fsm=fsm_context, filters=self.filters):
                await handler.run_func(post=post, fsm=fsm_context)
                return True
        return False

    def get_aiohttp_handler(self):
        async def handler(req: web.Request) -> web.Response:
            data = await req.json()
            # print(data)
            logger.warning(data)
            if data['secret'] != VK_SECRET:
                return web.HTTPNotFound()
            else:
                try:
                    if data['type'] == 'message_new':
                        await self.check_message_handlers(data['object'])
                    elif data['type'] == 'message_event':
                        await self.check_callback_handlers(data['object'])
                    elif data['type'] == 'board_post_new':
                        await self.check_board_handlers(data['object'])
                except Exception as e:
                    logger.error(f'f"EXCEPTION {traceback.format_exc()} ')

                finally:
                    return web.Response(text='ok')

        return handler


class SuperHandler:
    def __init__(self, func: callable, *filters: Filter):
        self.func = func
        self.filters = filters

    async def check(self, update: Update, filters: list[Filter], **kwargs):
        for filter_ in filters:
            try:
                filter_check = filter_.check(update, **kwargs)
            except UseAsyncCheck:
                filter_check = await filter_.async_check(update, **kwargs)
            if not filter_check:
                return False

        for filter_ in self.filters:
            try:
                filter_check = filter_.check(update, **kwargs)
            except UseAsyncCheck:
                filter_check = await filter_.async_check(update, **kwargs)
            if not filter_check:
                return False

        return True

    async def run_func(self, data: Update, fsm: FSMContext):
        await self.func(data)


class MessageHandler(SuperHandler):
    async def run_func(self, message: Message, fsm: FSMContext):
        await self.func(message, fsm=fsm)


class CallbackHandler(SuperHandler):
    async def run_func(self, callback: Callback, fsm: FSMContext):
        await self.func(callback, fsm=fsm)


class BoardHandler(SuperHandler):
    async def run_func(self, post: BoardPost, fsm: FSMContext):
        await self.func(post, fsm=fsm)
