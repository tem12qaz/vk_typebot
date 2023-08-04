import json
import logging
import random

import aiohttp
from aiohttp import FormData

from vk_api_lib.classes.urls import VK_API_SEND_MESSAGE_PATH, VK_API_URL, VK_API_DELETE_MESSAGE_PATH, VK_API_EDIT_MESSAGE_PATH, \
    VK_API_GET_MESSAGE_BY_CONSERVATION_ID_PATH, VK_API_GET_UPLOAD_SERVER_PHOTO_PATH, VK_API_SAVE_MESSAGE_PHOTO_PATH, \
    VK_API_GET_USERS_PATH

from vk_api_lib.classes.attachments import Photo, Video
from vk_api_lib.classes.handler import MainHandler
from vk_api_lib.classes.keyboard import Keyboard
from vk_api_lib.classes.message import Message


class VkRequestError(Exception):
    msg = 'REQUEST ERROR id{id} msg "{msg}"'


errors = {}


class Bot:
    def __init__(self, token: str, handler: MainHandler, logger: logging.Logger):
        self.token: str = token
        self.handler = handler
        self.logger = logger
        handler.bot = self

    async def request(self, path: str, data: dict) -> dict:
        data['access_token'] = self.token
        data['v'] = 5.131

        print(data)

        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    url=VK_API_URL + path,
                    data=data
                )
                resp = await resp.json()
        except Exception as e:
            self.logger.error(e)
            return {}
        else:
            return resp

    async def error_handler(self, resp: dict, args: dict):
        resp = resp['error']
        if resp['error_code'] == 909:
            await self.send_message(args['user_id'], args['text'], args['keyboard'], args['photos'])
        else:
            error_msg = VkRequestError.msg.format(id=resp['error_code'], msg=resp['error_msg'])
            self.logger.error(error_msg)
            raise VkRequestError(error_msg)

    async def send_message(self, user_id: int, text: str, keyboard: Keyboard | dict = None,
                           photos: list[str | Photo] = None, videos: list[str | Video] = None,
                           forward: list[Message] = None):
        data = {
            'user_id': user_id,
            'message': text,
            'random_id': random.randint(0, 2147483647),
        }
        if keyboard:
            data['keyboard'] = keyboard.json() if type(keyboard) == Keyboard else json.dumps(keyboard)

        if photos:
            attachments = []
            for photo in photos:
                if type(photo) is str:
                    attachments.append(await self.attach_photo(user_id, photo))
                elif type(photo) is Photo:
                    attachments.append(photo)
                else:
                    raise TypeError('only type <str> and <Photo> supported')
            data['attachment'] = ','.join(map(lambda x: x.data, attachments))

        else:
            attachments = None

        if forward:
            # forward_2 = {
            #     "peer_id": forward[0].user_id,
            #     "owner_id": forward[0].user_id,
            #     "message_ids": [message.id for message in forward],
            #     "conversation_message_ids": [message.conversation_message_id for message in forward],
            # }
            data["forward_messages"] = [message.id for message in forward]
        else:
            forward = None

        resp = await self.request(VK_API_SEND_MESSAGE_PATH, data)
        if resp.get('error'):
            await self.error_handler(
                resp,
                {
                    'user_id': user_id,
                    'text': text,
                    'keyboad': keyboard,
                    'photos': photos,
                    'forward': forward
                })
        else:
            return Message(user_id, text, resp['response'], self, keyboard, attachments)

    async def edit_message(
            self,
            user_id: int,
            message_id: int,
            text: str,
            keyboard: Keyboard | dict = None,
            photos: list[str | Photo] = None,
            videos: list[str | Video] = None,
            message=None):

        data = {
            'peer_id': user_id,
            'message_id': message_id,
            'message': text,
            'random_id': random.randint(0, 2147483647),
        }
        if keyboard:
            data['keyboard'] = keyboard.json() if type(keyboard) == Keyboard else json.dumps(keyboard)

        if photos:
            attachments = []
            for photo in photos:
                if type(photo) is str:
                    attachments.append(await self.attach_photo(user_id, photo))
                elif type(photo) is Photo:
                    attachments.append(photo)
                else:
                    raise TypeError('only type <str> and <Photo> supported')

            data['attachment'] = ','.join(map(lambda x: x.data, attachments))
        else:
            attachments = None

        resp = await self.request(VK_API_EDIT_MESSAGE_PATH, data)
        if resp.get('error'):
            await self.error_handler(
                resp,
                {
                    'user_id': user_id,
                    'message_id': message_id,
                    'text': text,
                    'keyboard': keyboard,
                    'photos': photos,
                    'message': message
                }
            )
        else:
            if message:
                message.text = text
                message.keyboard = keyboard
                if photos:
                    message.parse_attachments(attachments, save_old=False)
                return message
            else:
                return Message(user_id, text, resp['response'], self, keyboard, attachments)

    async def delete_message(self, message_id: int) -> None:
        data = {
            'message_ids': f'{message_id},',
            'delete_for_all': True
        }
        resp = await self.request(VK_API_DELETE_MESSAGE_PATH, data)
        if resp.get('error'):
            await self.error_handler(resp, {'message_id': message_id})

    async def get_message_by_conversation_id(self, user_id: int, conversation_id: int):
        data = {
            'conversation_message_ids': f'{conversation_id},',
            'peer_id': user_id
        }
        resp = await self.request(VK_API_GET_MESSAGE_BY_CONSERVATION_ID_PATH, data)
        if resp.get('error'):
            await self.error_handler(resp, {'user_id': user_id, 'conversation_id': conversation_id})

        message = resp['response']['items'][0]

        return message

    async def get_upload_photo_server(self, user_id: int):
        data = {
            'peer_id': user_id
        }

        resp = await self.request(VK_API_GET_UPLOAD_SERVER_PHOTO_PATH, data)
        if resp.get('error'):
            await self.error_handler(resp, {'user_id': user_id})

        return resp['response']['upload_url']

    async def upload_message_photo(self, user_id: int, photo_path: str):
        try:
            data = FormData()
            data.add_field('photo', self.encode_photo(photo_path))

            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    url=await self.get_upload_photo_server(user_id),
                    data=data
                )
                resp = json.loads(await resp.text())
        except Exception as e:
            self.logger.error(e)
            return {}
        else:
            return resp

    async def save_message_photo(self, server: int, photo: str, hash_: str):
        data = {
            'server': server,
            'photo': photo,
            'hash': hash_
        }

        resp = await self.request(VK_API_SAVE_MESSAGE_PHOTO_PATH, data)
        if resp.get('error'):
            await self.error_handler(resp, {'server': server, 'photo': photo, 'hash': hash_})
        return resp['response'][0]

    async def attach_photo(self, user_id: int, photo_path: str) -> Photo:
        data = await self.upload_message_photo(user_id, photo_path)
        photo_data = await self.save_message_photo(**data)

        return Photo.from_message_handler(photo_data)

    async def get_user_data(self, user_id: int):
        data = {
            'user_id': user_id,
            'fields': 'nickname'
        }
        resp = await self.request(VK_API_GET_USERS_PATH, data)
        if resp.get('error'):
            await self.error_handler(resp, {'user_id': user_id})

        user = resp['response'][0]

        return user

    @staticmethod
    def encode_photo(photo_path: str) -> bytes:
        with open(photo_path, "rb") as image_file:
            encoded = image_file.read()
        return encoded

