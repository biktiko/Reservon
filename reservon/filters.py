import logging

class IgnoreStaticRequestsFilter(logging.Filter):
    def filter(self, record):
        return not any(
            part in record.getMessage() for part in ['/static/', '/media/']
        )
