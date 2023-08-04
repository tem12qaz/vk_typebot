import copy
from typing import Optional

from loader import logger
from vk_api_lib.classes.attachments import Photo, Video, Market
from vk_api_lib.classes.keyboard import Keyboard
from vk_api_lib.classes.update import Update


class Message(Update):
    def __init__(
            self,
            user_id: int,
            text: str,
            message_id: int,
            conversation_message_id: int,
            bot,
            ref: Optional[str] = None,
            ref_source: Optional[str] = None,
            keyboard: Optional[Keyboard | dict] = None,
            photos: Optional[list[Photo]] = None,
            videos: Optional[list[Video]] = None,
            markets: Optional[list[Market]] = None,
            attachments: Optional[list[Video | Photo]] = None,
            payload: Optional[str] = None,
            **kwargs
    ):

        self.user_id = user_id
        self.text = text
        self.bot = bot
        self.ref = ref
        self.ref_source = ref_source
        self.id = message_id
        self.conversation_message_id = conversation_message_id
        self.keyboard = keyboard
        self.photos = photos
        self.videos = videos
        self.markets = markets
        self.payload = payload

        if attachments:
            self.parse_attachments(attachments, save_old=True)

    def parse_attachments(self, attachments: list[Video | Photo], save_old=True):
        videos_ = []
        photos_ = []

        for attachment in attachments:
            if type(attachment) is Photo:
                photos_.append(attachment)
            elif type(attachment) is Video:
                videos_.append(attachment)
        if (type(self.videos) is list) and save_old:
            self.videos.extend(videos_)
        else:
            self.videos = videos_
        if (type(self.photos) is list) and save_old:
            self.photos.extend(photos_)
        else:
            self.photos = photos_

    async def answer(self, text: str, keyboard: Keyboard | dict = None, photos: list[str] = None,
                     videos: list[str | Video] = None):
        return await self.bot.send_message(
            self.user_id, text, keyboard, photos, videos
        )

    async def delete(self) -> None:
        await self.bot.delete_message(self.id)

    async def edit(self, text: str = None, keyboard: Keyboard | dict = None, photos: list[str] = None,
                   videos: list[str | Video] = None) -> None:
        if not text:
            text = self.text

        if keyboard is None:
            keyboard = self.keyboard

        if photos is None:
            photos = self.photos

        if videos is None:
            videos = self.videos

        await self.bot.edit_message(
            self.user_id, self.id, text, keyboard, photos, videos, self
        )

    async def forward(self, user_id: int, text: str = None, keyboard: Keyboard | dict = None, photos: list[str] = None,
                      videos: list[str | Video] = None) -> None:
        await self.bot.send_message(
            user_id, text, keyboard, photos, videos, [self]
        )

    @classmethod
    def get_attachments(cls, attachments: list) -> tuple[list[Photo], list[Video], list[Market]]:
        photos: list[Photo] = []
        videos: list[Video] = []
        markets: list[Market] = []

        for attachment in attachments:
            if attachment['type'] == 'photo':
                photos.append(Photo.from_message_handler(attachment))
            elif attachment['type'] == 'video':
                pass
            elif attachment['type'] == 'market':
                markets.append(Market.from_message_handler(attachment))

        photos = None if not photos else photos
        videos = None if not videos else videos
        markets = None if not markets else markets

        return photos, videos, markets

    @classmethod
    def from_message_handler(cls, message: dict, bot):
        message = message['message']
        user_id = message.get('peer_id')
        text = message.get('text')
        message_id = message.get('id')
        attachments = message.get('attachments')
        ref = message.get('ref')
        ref_source = message.get('ref_source')
        conversation_message_id = message.get('conversation_message_id')
        payload = message.get('payload')

        photos, videos, markets = cls.get_attachments(attachments)
        if user_id and message_id and conversation_message_id:
            return cls(
                user_id=user_id,
                text=text,
                message_id=message_id,
                conversation_message_id=conversation_message_id,
                bot=bot,
                ref=ref,
                ref_source=ref_source,
                photos=photos,
                videos=videos,
                markets=markets,
                payload=payload
            )
        else:
            logger.error('cant parse message')
            return None

    @classmethod
    def from_callback_handler(cls, message: dict, bot):
        message_id = message.get('id')
        text = message.get('text')
        user_id = message.get('peer_id')
        keyboard_dict = message.get('keyboard')
        conversation_message_id = message.get('conversation_message_id')
        payload = message.get('payload')

        if keyboard_dict:
            keyboard_dict.pop('author_id')
            for i, row in enumerate(keyboard_dict['buttons']):
                for j, button in enumerate(row):
                    if button['action']['type'] not in ('text', 'callback'):
                        new_button = copy.deepcopy(button)
                        new_button.pop('color')
                        keyboard_dict['buttons'][i][j] = new_button

        attachments = message.get('attachments')
        photos, videos, markets = cls.get_attachments(attachments)

        if user_id and text and message_id and conversation_message_id:
            return cls(user_id=user_id, message_id=message_id, text=text,
                       conversation_message_id=conversation_message_id,
                       bot=bot, keyboard=keyboard_dict, photos=photos, videos=videos,
                       markets=markets, payload=payload)
        else:
            logger.error('cant parse message')
            return None
