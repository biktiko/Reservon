class BookingError(Exception):
    def __init__(self, message, nearest_before=None, nearest_after=None):
        super().__init__(message)
        self.message = message
        self.nearest_before = nearest_before
        self.nearest_after = nearest_after

class ClientError(Exception):
    def __init__(self, message, status=400):
        self.message = message
        self.status = status