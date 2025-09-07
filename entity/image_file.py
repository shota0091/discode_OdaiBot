class ImageFile:
    def __init__(self, id: int, filename: str, sent: bool):
        self.id = id
        self.filename = filename
        self.sent = sent

    def mark_sent(self):
        self.sent = True
