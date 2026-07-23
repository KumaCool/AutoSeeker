import re


def parse_salary(text):
    text = str(text or "").upper().replace(" ", "")
    range_match = re.search(r"(\d+(?:\.\d+)?)K?-(\d+(?:\.\d+)?)K", text)
    single_match = re.search(r"(\d+(?:\.\d+)?)K", text)
    if range_match:
        return float(range_match.group(1)), float(range_match.group(2))
    if single_match:
        value = float(single_match.group(1))
        return value, value
    return None, None
