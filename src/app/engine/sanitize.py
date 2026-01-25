from __future__ import annotations

import re

_ILLEGAL = re.compile(r'[\\/:*?"<>|]+')
_MULTI_US = re.compile(r"_+")


def sanitize_filename(s: str) -> str:
    if not s:
        return ""
    s = s.strip().replace(" ", "_")
    s = _ILLEGAL.sub("_", s)
    s = _MULTI_US.sub("_", s).strip("_")
    return s
