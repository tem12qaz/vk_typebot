from vk_api_lib.classes.update import Update


class BoardPost(Update):
    def __init__(self, post_id: int, from_id: int, topic_id: int, text: str):
        self.id = post_id
        self.user_id = from_id
        self.topic_id = topic_id
        self.text = text

    @classmethod
    def from_update(cls, update: dict):
        post_id = update['id']
        from_id = update['from_id']
        topic_id = update['topic_id']
        text = update['text']
        return cls(post_id, from_id, topic_id, text)