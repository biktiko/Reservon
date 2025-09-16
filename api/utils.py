from datetime import datetime, timedelta
from django.utils import timezone
import re

def _parse_local(dt_str: str):
    """
    Parses a string into a timezone-aware datetime object.
    Handles "DD.MM.YYYY HH:MM" and relative terms like "today 09:00" or "tomorrow 14:30".
    """
    if not isinstance(dt_str, str):
        return None

    normalized_str = dt_str.lower().strip()
    local_tz = timezone.get_current_timezone()
    now = timezone.now().astimezone(local_tz)
    
    target_day = None
    time_part = None

    # Step 1: Check for relative day terms
    if "tomorrow" in normalized_str:
        target_day = now.date() + timedelta(days=1)
    elif "today" in normalized_str:
        target_day = now.date()

    # Step 2: Try to extract time (HH:MM) using regex
    time_match = re.search(r'(\d{1,2}:\d{2})', normalized_str)
    if time_match:
        time_part = datetime.strptime(time_match.group(1), '%H:%M').time()

    # Step 3: Combine day and time or parse full string
    if target_day:
        # We found "today" or "tomorrow". Use the extracted time or default to 00:00.
        final_time = time_part or datetime.min.time()
        naive_dt = datetime.combine(target_day, final_time)
        return timezone.make_aware(naive_dt, local_tz)
    
    # Step 4: If no relative term, try the full "DD.MM.YYYY HH:MM" format
    try:
        naive_dt = datetime.strptime(dt_str, '%d.%m.%Y %H:%M')
        return timezone.make_aware(naive_dt, local_tz)
    except ValueError:
        pass

    # If all parsing fails, return None
    return None


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