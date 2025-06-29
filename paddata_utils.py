import re
import datetime

DATE_PATTERNS = [
    r'\d{4}-\d{2}-\d{2}',
    r'\d{4}/\d{2}/\d{2}',
    r'\d{2}/\d{2}/\d{4}',
    r'\d{4}년\s?\d{2}월\s?\d{2}일'
]

def extract_date(text):
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group()
    datetime_match = re.search(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}', text)
    if datetime_match:
        return datetime_match.group().split()[0]
    return None

def parse_date(date_str):
    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
        year, month, day = date_str.split('-')
        return int(year), int(month), int(day)
    if re.match(r'\d{4}/\d{2}/\d{2}', date_str):
        year, month, day = date_str.split('/')
        return int(year), int(month), int(day)
    if re.match(r'\d{2}/\d{2}/\d{4}', date_str):
        parts = date_str.split('/')
        return int(parts[2]), int(parts[0]), int(parts[1])
    match = re.match(r'(\d{4})년\s?(\d{1,2})월\s?(\d{1,2})일', date_str)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    today = datetime.date.today()
    return today.year, today.month, today.day

