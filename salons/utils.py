from datetime import timedelta

def round_down_to_5(dt):
    """
    Округляет datetime dt вниз до ближайшей отметки кратной 5 минутам.
    Например, 10:52:23 -> 10:50:00.
    """
    return dt - timedelta(
        minutes=dt.minute % 5,
        seconds=dt.second,
        microseconds=dt.microsecond
    )

