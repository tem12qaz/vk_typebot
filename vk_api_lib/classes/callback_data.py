import copy

from tortoise import Model
from tortoise.exceptions import DoesNotExist

from vk_api_lib.classes.filters import CallbackFilter


class NotFoundObject(Exception):
    message = 'Not found {type} with id {id}'


class CallbackData:
    def new(self) -> dict:
        if hasattr(self, '__annotations__'):
            datas = copy.deepcopy(self.__dict__)
            for name, annotation in self.__annotations__.items():
                if Model.__subclasscheck__(annotation):
                    datas[name] = datas[name].id
        else:
            datas = {}

        return {self.__class__.__name__: datas}

    @classmethod
    def filter(cls):
        return CallbackFilter(cls)

    @classmethod
    async def parse(cls, callback_data: dict):
        if hasattr(cls, '__annotations__') and callback_data:
            datas = copy.deepcopy(cls.__annotations__)
            for key, value in callback_data.items():
                annotation = cls.__annotations__[key]
                if Model.__subclasscheck__(annotation):
                    try:
                        datas[key] = await annotation.get(id=int(value))
                    except (DoesNotExist, ValueError):
                        raise NotFoundObject(NotFoundObject.message.format(
                            type=annotation, id=value
                        ))

                else:
                    datas[key] = annotation(value)
        else:
            datas = {}

        return cls(**datas)


class EmptyCallback(CallbackData):
    pass
