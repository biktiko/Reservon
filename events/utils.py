
import re
from datetime import datetime

def normalize_day_of_week(day_input):
    """
    Normalizes various day of the week formats to a standard 3-letter lowercase string (e.g., 'mon').
    Handles single strings, lists of strings, and different languages.
    """
    DAY_MAP = {
        # English
        'mon': 'mon', 'monday': 'mon',
        'tue': 'tue', 'tuesday': 'tue',
        'wed': 'wed', 'wednesday': 'wed',
        'thu': 'thu', 'thursday': 'thu',
        'fri': 'fri', 'friday': 'fri',
        'sat': 'sat', 'saturday': 'sat',
        'sun': 'sun', 'sunday': 'sun',
        # Russian
        'пн': 'mon', 'понедельник': 'mon',
        'вт': 'tue', 'вторник': 'tue',
        'ср': 'wed', 'среда': 'wed',
        'чт': 'thu', 'четверг': 'thu',
        'пт': 'fri', 'пятница': 'fri',
        'сб': 'sat', 'суббота': 'sat',
        'вс': 'sun', 'воскресенье': 'sun',
    }
    
    if not day_input:
        return []
    if isinstance(day_input, str):
        day_input = re.split(r'[,\s]+', day_input)

    normalized_days = []
    for day in day_input:
        if not day: continue
        normalized = DAY_MAP.get(str(day).lower().strip())
        if normalized:
            normalized_days.append(normalized)
        elif 'any' in str(day).lower():
            return ['any']
            
    return list(set(normalized_days))

def normalize_month(month_input):
    """
    Normalizes various month formats to a standard 3-letter lowercase string (e.g., 'jan').
    Handles single strings/numbers, lists, and different languages.
    """
    MONTH_MAP = {
        # English
        'jan': 'jan', 'january': 'jan', '1': 'jan',
        'feb': 'feb', 'february': 'feb', '2': 'feb',
        'mar': 'mar', 'march': 'mar', '3': 'mar',
        'apr': 'apr', 'april': 'apr', '4': 'apr',
        'may': 'may', '5': 'may',
        'jun': 'jun', 'june': 'jun', '6': 'jun',
        'jul': 'jul', 'july': 'jul', '7': 'jul',
        'aug': 'aug', 'august': 'aug', '8': 'aug',
        'sep': 'sep', 'september': 'sep', '9': 'sep',
        'oct': 'oct', 'october': 'oct', '10': 'oct',
        'nov': 'nov', 'november': 'nov', '11': 'nov',
        'dec': 'dec', 'december': 'dec', '12': 'dec',
        # Russian
        'янв': 'jan', 'январь': 'jan',
        'фев': 'feb', 'февраль': 'feb',
        'мар': 'mar', 'март': 'mar',
        'апр': 'apr', 'апрель': 'apr',
        'май': 'may',
        'июн': 'jun', 'июнь': 'jun',
        'июл': 'jul', 'июль': 'jul',
        'авг': 'aug', 'август': 'aug',
        'сен': 'sep', 'сентябрь': 'sep',
        'окт': 'oct', 'октябрь': 'oct',
        'ноя': 'nov', 'ноябрь': 'nov',
        'дек': 'dec', 'декабрь': 'dec',
    }

    if not month_input:
        return []
    if isinstance(month_input, str):
        month_input = re.split(r'[,\s]+', month_input)
    
    normalized_months = []
    for month in month_input:
        if not month: continue
        normalized = MONTH_MAP.get(str(month).lower().strip())
        if normalized:
            normalized_months.append(normalized)
        elif 'any' in str(month).lower():
            return ['any']

    return list(set(normalized_months))

def normalize_specific_dates(date_input):
    """
    Normalizes various date formats into a list of 'YYYY-MM-DD' strings.
    Handles lists of strings or a single string with comma/space separators.
    """
    if not date_input:
        return []
    if isinstance(date_input, str):
        date_input = re.split(r'[,\s]+', date_input)

    normalized_dates = []
    for date_str in date_input:
        if not date_str: continue
        try:
            # Use dateutil.parser for robust parsing if available, otherwise try strptime
            # For this example, we stick to a few formats for simplicity without adding dependencies.
            dt_obj = None
            for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y'):
                try:
                    dt_obj = datetime.strptime(date_str.strip(), fmt)
                    break
                except ValueError:
                    continue
            if dt_obj:
                normalized_dates.append(dt_obj.strftime('%Y-%m-%d'))
        except Exception:
            # Ignore dates that cannot be parsed
            continue
    return normalized_dates

def normalize_time_slots(time_input):
    """
    Normalizes various time formats into a list of 'HH:MM' strings.
    """
    if not time_input:
        return []
    if isinstance(time_input, str):
        time_input = re.split(r'[,\s]+', time_input)

    normalized_times = []
    for time_str in time_input:
        if not time_str: continue
        time_str = time_str.strip().upper()
        try:
            dt_obj = None
            # Try 24-hour format first
            for fmt in ('%H:%M', '%H'):
                try:
                    dt_obj = datetime.strptime(time_str, fmt)
                    break
                except ValueError:
                    continue
            
            # Try 12-hour format with AM/PM
            if not dt_obj:
                 for fmt in ('%I:%M%p', '%I%p'):
                    try:
                        dt_obj = datetime.strptime(time_str.replace(" ", ""), fmt)
                        break
                    except ValueError:
                        continue
            
            if dt_obj:
                normalized_times.append(dt_obj.strftime('%H:%M'))
        except Exception:
            continue
            
    return sorted(list(set(normalized_times)))
