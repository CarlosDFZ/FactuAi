import re


def extract_uuid_from_text(text):
    patterns = [
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        r"[0-9a-fA-F]{8}\s*-\s*[0-9a-fA-F]{4}\s*-\s*[0-9a-fA-F]{4}\s*-\s*[0-9a-fA-F]{4}\s*-\s*[0-9a-fA-F]{12}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            uuid = match.group(0)
            uuid = re.sub(r"\s+", "", uuid)
            return uuid.upper()

    return None