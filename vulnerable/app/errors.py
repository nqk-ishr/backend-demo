class HttpError(Exception):
    """Lỗi kèm mã HTTP: handler ném ra, main.py đổi thành phản hồi JSON."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message
