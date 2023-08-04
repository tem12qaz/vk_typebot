from typing import Type

from loader import logger
from vk_api_lib.classes.callback_data import CallbackData
from vk_api_lib.classes.message import Message
from vk_api_lib.classes.update import Update


class Callback(Update):
    def __init__(self, callback_data: CallbackData, peer_id: int, message: Message = None):
        self.message = message
        self.callback_data = callback_data
        self.user_id = peer_id

    @classmethod
    async def parse(cls, callback: dict, callback_data_class: Type[CallbackData], bot):
        peer_id = callback.get('peer_id')
        conversation_message_id = callback.get('conversation_message_id')
        payload = callback.get('payload').get(callback_data_class.__name__)

        if peer_id and (payload is not None):
            callback_data: callback_data_class = await callback_data_class.parse(payload)
            if conversation_message_id:
                message_resp = await bot.get_message_by_conversation_id(peer_id, conversation_message_id)
                message = Message.from_callback_handler(message_resp, bot)
                return cls(callback_data=callback_data, peer_id=peer_id, message=message)
            else:
                return cls(callback_data=callback_data, peer_id=peer_id)
        else:
            logger.error(f'cant parse callback')
            return None



