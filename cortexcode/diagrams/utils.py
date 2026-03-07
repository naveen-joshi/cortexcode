import re
from collections import defaultdict
from typing import Dict, List


STYLE_CLASS = '    classDef class fill:#f9f,stroke:#333,stroke-width:2px'
STYLE_FUNCTION = '    classDef function fill:#bbf,stroke:#333,stroke-width:2px'
STYLE_INTERFACE = '    classDef interface fill:#bfb,stroke:#333,stroke-width:2px'
STYLE_EXTERNAL = '    classDef external fill:#eee,stroke:#999,stroke-width:1px,dash:5,5'


def sanitize_id(name: str) -> str:
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if sanitized and sanitized[0].isdigit():
        sanitized = 'n' + sanitized
    return sanitized[:50]


def build_callers(call_graph: Dict[str, List[str]]) -> Dict[str, List[str]]:
    callers: Dict[str, List[str]] = defaultdict(list)
    for caller, callees in call_graph.items():
        for callee in callees:
            callers[callee].append(caller)
    return callers
