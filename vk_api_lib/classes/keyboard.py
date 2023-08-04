import json

from tortoise import Model
from tortoise.queryset import QuerySet

from vk_api_lib.classes.callback_data import CallbackData, EmptyCallback


class EndList(Exception):
    pass


class Colors:
    primary = 'primary'
    negative = 'negative'
    positive = 'positive'
    secondary = 'secondary'


class Button:
    colors = Colors

    def __init__(self, action: str, color: str = None, label: str = None, payload: CallbackData = None,
                 link: str = None):
        data = {'type': action}
        if label:
            data['label'] = label
        if payload:
            data['payload'] = payload.new()
        if link:
            data['link'] = link

        self.json = {'action': data}

        if color:
            self.json['color'] = color

    @classmethod
    def text(cls, text: str, payload: CallbackData = None, color: str = None):
        return cls(action='text', label=text, color=color, payload=payload)

    @classmethod
    def callback(cls, text: str, payload: CallbackData = None, color: str = None):
        return cls(action='callback', label=text, color=color, payload=payload)

    @classmethod
    def link(cls, text: str, link: str, payload: CallbackData = None):
        return cls(action='open_link', label=text, link=link, payload=payload)

    @classmethod
    def location(cls, payload: CallbackData = None):
        return cls(action='location', payload=payload)


class Keyboard:
    def __init__(self, keyboard: list[list[Button]], inline: bool = False, one_time: bool = False):
        self.keyboard: list[list[Button]] = keyboard
        self.inline = inline
        self.one_time = one_time

    def json(self):
        result = {'buttons': []}
        for i, row in enumerate(self.keyboard):
            result['buttons'].append([])
            for j, button in enumerate(row):
                result['buttons'][i].append(button.json)
        result['inline'] = self.inline
        result['one_time'] = self.one_time
        return json.dumps(result)


class KeyboardFactory:
    async def create(self) -> Keyboard:
        pass


class ObjectsGridCallbackKeyboard(KeyboardFactory):
    model: Model
    cols: int
    rows: int
    inline: bool = True
    display_page_button: bool = True
    display_back_button: bool = True
    previous_btn_text: str = '<'
    next_btn_text: str = '>'
    page_btn_text: str = '{page}/{count}'
    previous_btn_color: str = 'primary'
    next_btn_color: str = 'primary'
    page_btn_color: str = 'primary'

    def __init__(self, page: int, **kwargs):
        self.current_object_ = None
        self.count = None
        self.page = page
        self.kwargs = kwargs
        self.objects = None
        pass

    def get_queryset(self) -> QuerySet:
        return self.model.all()

    def get_object_button(self, data_object: Model) -> Button:
        raise NotImplementedError('define this function')

    def get_back_button(self) -> Button:
        raise NotImplementedError('define this function')

    def get_list_callback_data(self, page: int) -> CallbackData:
        raise NotImplementedError('define this function')

    def get_list_button(self, text: str, color: str, page: int):
        return Button.callback(text, payload=self.get_list_callback_data(page), color=color)

    async def create_without_grid(self) -> tuple[Keyboard, list[Model]]:
        keyboard = await self.create(without_grid=True)
        return keyboard, self.objects

    async def no_objects(self):
        raise NotImplementedError('define this function')

    async def create(self, without_grid: bool = False) -> Keyboard:
        try:
            objects_on_page = self.cols * self.rows
            offset = objects_on_page * self.page
            limit = offset + objects_on_page

            count = await self.model.all().count()
            pages = count // objects_on_page
            if (count % objects_on_page) != 0:
                pages += 1
            self.count = pages

            objects = await self.get_queryset().offset(offset).limit(limit)
            print(len(objects))
            print(objects_on_page)
            if without_grid:
                self.objects = objects
            if not objects:
                if self.page == 0:
                    await self.no_objects()
                raise EndList
        except AttributeError:
            raise AttributeError(f'define attributes "model", "cols", "rows" at class {self.__class__.__name__}')

        keyboard = []
        if not without_grid:
            i = 0

            try:
                for row in range(self.rows):
                    keyboard.append([])
                    for col in range(self.cols):
                        self.current_object_ = objects[i]
                        keyboard[-1].append(self.get_object_button(self.current_object_))
                        i += 1
            except IndexError:
                if not keyboard[-1]:
                    keyboard.pop(-1)

        keyboard.append(
            [
                self.get_list_button(self.previous_btn_text, self.previous_btn_color, self.page-1),
                self.get_list_button(self.next_btn_text, self.next_btn_color, self.page+1)
            ]
        )
        if self.display_page_button:
            keyboard[-1].insert(1, Button.callback(
                self.page_btn_text.format(
                    page=self.page + 1, count=self.count
                ),
                payload=EmptyCallback(),
                color=self.page_btn_color
            ))

        if self.display_back_button:
            keyboard.append([self.get_back_button()])

        return Keyboard(keyboard, inline=self.inline)
