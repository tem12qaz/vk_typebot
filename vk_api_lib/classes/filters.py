import json

from vk_api_lib.classes.FSM import FSMContext
# from vk_api_lib.classes.states import State
# from vk_api_lib.classes.boardpost import BoardPost
# from vk_api_lib.classes.callback import Callback
# from vk_api_lib.classes.message import Message
from vk_api_lib.classes.update import Update


class UseAsyncCheck(Exception):
    msg = 'use "await filter.async_check()"'


class UseSyncCheck(Exception):
    msg = 'use "filter.check()"'


class Filter:
    def check(self, update: Update, **kwargs) -> bool:
        raise UseAsyncCheck

    async def async_check(self, update: Update, fsm: FSMContext, **kwargs) -> bool:
        raise UseSyncCheck

    @property
    def is_not(self):
        return NotFilter(self)


class NotFilter(Filter):
    def __init__(self, *filters):
        self.filters = filters

    async def async_check(self, **kwargs):
        for filter_ in self.filters:
            try:
                filter_check = filter_.check(**kwargs)
            except UseAsyncCheck:
                filter_check = await filter_.async_check(**kwargs)
            if filter_check:
                return False
        return True


class TextFilter(Filter):
    def __init__(self, *match_list: str, case_sensitive=True):
        self.match_list = match_list
        self.case_sensitive = case_sensitive
        self.reverse = False

    def check(self, message: 'Message', **kwargs) -> bool:
        text = message.text
        text = text if self.case_sensitive else text.lower()
        for match in self.match_list:
            match = match if self.case_sensitive else match.lower()
            if match == text:
                return True
        return False


class OrFilter(Filter):
    def __init__(self, *filters):
        self.filters = filters

    async def async_check(self, update: Update, *args, **kwargs):
        for filter_ in self.filters:
            try:
                filter_check = filter_.check(update, *args, **kwargs)
            except UseAsyncCheck:
                filter_check = await filter_.async_check(update, *args, **kwargs)
            if filter_check:
                return True
        return False


class CallbackFilter(Filter):
    def __init__(self, callback_data_class):
        self.callback_data_class = callback_data_class

    def check(self, callback: 'Callback', **kwargs) -> bool:
        callback_data = callback.callback_data
        if not callback_data:
            return False
        if not type(callback_data) is self.callback_data_class:
            return False

        return True


class CommandFilter(Filter):
    def __init__(self, *match_list: str):
        self.match_list = match_list
        
    def check(self, message: 'Message', **kwargs) -> bool:

        command = message.payload
        if command:
            command = json.loads(command)
            if not command:
                return False
            command = command.get('command')
            for match in self.match_list:
                if match == command:
                    return True
        return False


class StateFilter(Filter):
    def __init__(self, *state_list: 'State'):
        self.state_list = state_list

    async def async_check(self, update: Update, fsm: FSMContext, **kwargs) -> bool:
        state_str = await fsm.get_state()
        print(state_str)
        if state_str is None and not self.state_list:
            return True
        for state in self.state_list:
            if state.name == state_str:
                return True


class TopicFilter(Filter):
    def __init__(self, *ids):
        self.ids = ids

    def check(self, post: 'BoardPost', **kwargs) -> bool:
        if post.topic_id not in self.ids:
            return False
        else:
            return True


class HasMarketFilter(Filter):
    def check(self, message: 'Message', **kwargs) -> bool:
        if message.markets:
            return True
        else:
            return False






