
import re
from datetime import datetime, timedelta
from django.utils import timezone
from dateutil.relativedelta import relativedelta

# --- Keyword Dictionaries for 3 languages ---

KEYWORDS = {
    'today': ['today', 'сегодня', 'այսօր', 'սօր'],
    'tomorrow': ['tomorrow', 'tmrw', 'завтра', 'վաղը'],
    'day_after_tomorrow': ['day after tomorrow', 'послезавтра', 'մյուս օրը'],
    'yesterday': ['yesterday', 'вчера', 'երեկ'],
    
    'next': ['next', 'следующий', 'հաջորդ', 'մյուս'],
    'last': ['last', 'предыдущий', 'прошлый', 'նախորդ'],
    
    'day': ['day', 'days', 'день', 'дня', 'дней', 'օր'],
    'week': ['week', 'weeks', 'неделя', 'недели', 'недель', 'շաբաթ'],
    'month': ['month', 'months', 'месяц', 'месяца', 'месяцев', 'ամիս'],
    'year': ['year', 'years', 'год', 'года', 'лет', 'տարի'],

    'morning': ['morning', 'утро', 'утром', 'առավոտ'],
    'afternoon': ['afternoon', 'day', 'днем', 'днём', 'ցերեկ'],
    'evening': ['evening', 'tonight', 'вечер', 'вечером', 'երեկո'],

    'days_of_week': {
        'mon': ['monday', 'понедельник', 'пн', 'երկուշաբթի'],
        'tue': ['tuesday', 'вторник', 'вт', 'երեքշաբթի'],
        'wed': ['wednesday', 'среда', 'ср', 'չորեքշաբթի'],
        'thu': ['thursday', 'четверг', 'чт', 'հինգշաբթի'],
        'fri': ['friday', 'пятница', 'пт', 'ուրբաթ'],
        'sat': ['saturday', 'суббота', 'сб', 'շաբաթ'],
        'sun': ['sunday', 'воскресенье', 'вс', 'կիրակի'],
    },
    'months_of_year': {
        1: ['january', 'январь', 'янв', 'հունվար'],
        2: ['february', 'февраль', 'фев', 'փետրվար'],
        3: ['march', 'март', 'мар', 'մարտ'],
        4: ['april', 'апрель', 'апр', 'ապրիլ'],
        5: ['may', 'май', 'մայիս'],
        6: ['june', 'июнь', 'июн', 'հունիս'],
        7: ['july', 'июль', 'июл', 'հուլիս'],
        8: ['august', 'август', 'авг', 'օգոստոս'],
        9: ['september', 'сентябрь', 'сен', 'սեպտեմբեր'],
        10: ['october', 'октябрь', 'окт', 'հոկտեմբեր'],
        11: ['november', 'ноябрь', 'ноя', 'նոյեմբեր'],
        12: ['december', 'декабрь', 'дек', 'դեկտեմբեր'],
    }
}

def parse_natural_language_date(text: str):
    """
    Parses a natural language string into a timezone-aware datetime object.
    Handles various relative terms, languages, and formats.
    """
    if not isinstance(text, str):
        return None

    text_lower = text.lower().strip()
    local_tz = timezone.get_current_timezone()
    now = timezone.now().astimezone(local_tz)
    
    base_date = now.date()
    time_part = None
    
    words = set(re.split(r'[\s,.]+', text_lower))

    # --- Extract time early for weekday disambiguation ---
    time_match = re.search(r'(\d{1,2}:\d{2})', text_lower)
    if time_match:
        try:
            time_part = datetime.strptime(time_match.group(1), '%H:%M').time()
        except ValueError:
            time_part = None

    # --- Step 1: Handle simple relative terms ---
    if any(kw in words for kw in KEYWORDS['tomorrow']):
        base_date = now.date() + timedelta(days=1)
    elif any(kw in words for kw in KEYWORDS['day_after_tomorrow']):
        base_date = now.date() + timedelta(days=2)
    elif any(kw in words for kw in KEYWORDS['yesterday']):
        base_date = now.date() - timedelta(days=1)
    elif any(kw in words for kw in KEYWORDS['today']):
        base_date = now.date()

    # --- Step 2: Handle "in X days/weeks/months" ---
    # Example: "через 3 дня", "in 2 weeks"
    match = re.search(r'(\d+)\s*(' + '|'.join(KEYWORDS['day'] + KEYWORDS['week'] + KEYWORDS['month']) + ')', text_lower)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        if unit in KEYWORDS['day']:
            base_date = now.date() + timedelta(days=num)
        elif unit in KEYWORDS['week']:
            base_date = now.date() + timedelta(weeks=num)
        elif unit in KEYWORDS['month']:
            base_date = now.date() + relativedelta(months=num)

    # --- Step 3: Handle "next/last week/month/year" and days of week ---
    is_next = any(kw in words for kw in KEYWORDS['next'])
    is_last = any(kw in words for kw in KEYWORDS['last'])

    # "next Monday", "прошлый вторник"
    for day_code, day_names in KEYWORDS['days_of_week'].items():
        if any(name in words for name in day_names):
            day_index = list(KEYWORDS['days_of_week'].keys()).index(day_code)
            # Normalize difference to 0..6
            days_ahead_mod = (day_index - now.weekday()) % 7

            if is_next:
                # Explicit NEXT -> always future week if same day, else upcoming this week
                days_ahead = 7 if days_ahead_mod == 0 else days_ahead_mod
            elif is_last:
                # Explicit LAST -> always previous occurrence
                days_ahead = days_ahead_mod - 7 if days_ahead_mod != 0 else -7
            else:
                # Nearest upcoming occurrence (including today if time is in the future)
                if days_ahead_mod == 0:
                    if time_part is not None:
                        # If specific time provided, choose today only if it's still ahead
                        days_ahead = 0 if time_part > now.time() else 7
                    else:
                        # No time provided -> treat as upcoming; prefer today only if we haven't effectively passed the day
                        # To keep behavior deterministic, pick today if current time is before end of day; else next week
                        days_ahead = 0 if now.time() < datetime.max.time().replace(hour=23, minute=59, second=59, microsecond=0) else 7
                else:
                    days_ahead = days_ahead_mod

            base_date = now.date() + timedelta(days=days_ahead)
            break # Exit after finding a day

    # "next week", "в прошлом месяце"
    if any(kw in words for kw in KEYWORDS['week']):
        delta = timedelta(weeks=1 if is_next else -1 if is_last else 0)
        base_date = now.date() + delta
    elif any(kw in words for kw in KEYWORDS['month']):
        delta = relativedelta(months=1 if is_next else -1 if is_last else 0)
        base_date = now.date() + delta
    elif any(kw in words for kw in KEYWORDS['year']):
        delta = relativedelta(years=1 if is_next else -1 if is_last else 0)
        base_date = now.date() + delta

    # --- Step 4: Time fallback by part of day if time not provided ---
    if not time_part:
        # If no explicit time, check for morning/afternoon/evening
        if any(kw in words for kw in KEYWORDS['morning']):
            time_part = datetime.strptime('09:00', '%H:%M').time()
        elif any(kw in words for kw in KEYWORDS['afternoon']):
            time_part = datetime.strptime('14:00', '%H:%M').time()
        elif any(kw in words for kw in KEYWORDS['evening']):
            time_part = datetime.strptime('19:00', '%H:%M').time()

    # --- Step 5: Try absolute date parsing if no relative terms were decisive ---
    # Support both 'DD.MM.YYYY' and 'YYYY-MM-DD' with or without explicit time.
    if base_date == now.date():
        absolute_parsed = None
        # Try full datetime formats first
        for fmt in ('%d.%m.%Y %H:%M', '%Y-%m-%d %H:%M'):
            try:
                absolute_parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        if absolute_parsed is not None:
            return timezone.make_aware(absolute_parsed, local_tz)

        # Try date-only formats
        for fmt in ('%d.%m.%Y', '%Y-%m-%d'):
            try:
                date_only = datetime.strptime(text, fmt).date()
                base_date = date_only
                break
            except ValueError:
                continue
        # If still not parsed, keep base_date as-is (today)

    # --- Step 6: Combine base_date and time_part ---
    final_time = time_part or now.time()
    naive_dt = datetime.combine(base_date, final_time)
    aware_dt = timezone.make_aware(naive_dt, local_tz)
    
    return aware_dt
