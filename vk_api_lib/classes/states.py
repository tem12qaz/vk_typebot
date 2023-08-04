from vk_api_lib.classes.filters import StateFilter


class State:
    def __init__(self, name: str):
        self.name = name

    def filter(self) -> StateFilter:
        return StateFilter(self)


# class StateForm:
#     states = list[State]
#
#     def __init__(self):




