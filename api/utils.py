from datetime import datetime, timedelta
from django.utils import timezone

def _parse_local(dt_str: str):
    """
    Парсим строку "DD.MM.YYYY HH:MM" как локальное время в settings.TIME_ZONE.
    """
    try:
        naive = datetime.strptime(dt_str, '%d.%m.%Y %H:%M')
    except Exception:
        return None
    return timezone.make_aware(naive, timezone.get_current_timezone())

def subtract_intervals(avails, busys):
    """
    Из списка доступных avails ( [(s,e),...] ) вычесть busy ( [(s,e),...] ).
    Вернуть список свободных [(s,e),...].
    """
    result = []
    for a_start, a_end in avails:
        cuts = [(a_start, a_end)]
        for b_start, b_end in busys:
            new = []
            for c_start, c_end in cuts:
                # нет пересечения
                if b_end <= c_start or b_start >= c_end:
                    new.append((c_start, c_end))
                    continue
                # busy полностью закрывает
                if b_start <= c_start and b_end >= c_end:
                    continue
                # overlap слева
                if b_start <= c_start < b_end < c_end:
                    new_start = b_end
                    if new_start < c_end:
                        new.append((new_start, c_end))
                    continue
                # overlap справа
                if c_start < b_start < c_end <= b_end:
                    new_end = b_start
                    if c_start < new_end:
                        new.append((c_start, new_end))
                    continue
                # busy внутри: разделяет на два
                if c_start < b_start and b_end < c_end:
                    new.append((c_start, b_start))
                    new.append((b_end, c_end))
                    continue
            cuts = new
        result.extend(cuts)
    return result

def merge_intervals(intervals):
    """
    Сливает пересекающиеся и соприкасающиеся интервалы.
    """
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: x[0])
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        last_s, last_e = merged[-1]
        # если пересекаются или стыкуются
        if s <= last_e + timedelta(seconds=1):
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))
    return merged