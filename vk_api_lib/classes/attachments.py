from typing import Optional


class Photo:
    def __init__(
            self,
            id: int,
            owner_id: int,
            album_id: int,
            user_id: int,
            text: str,
            date: int,
            width: Optional[int] = None,
            height: Optional[int] = None,
            **kwargs
    ):
        self.id = id
        self.owner_id = owner_id
        self.album_id = album_id
        self.user_id = user_id
        self.text = text
        self.date = date
        self.width = width
        self.height = height

    @property
    def data(self):
        return f'photo{self.owner_id}_{self.id_}'

    @classmethod
    def from_message_handler(cls, photo: dict):
        return cls(**photo)

    @classmethod
    def from_callback_handler(cls, resp: dict):
        data = resp['photo']

        return cls(**data)


class Video:
    pass


class Market:
    def __init__(self, id: int, owner_id: int, title: str, **kwargs):
        self.id = id
        self.owner_id = owner_id
        self.title = title

    @classmethod
    def from_message_handler(cls, market: dict):
        print(market)
        return cls(**market['market'])

