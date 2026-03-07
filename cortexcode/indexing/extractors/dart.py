import re
from typing import Any, Callable


DetectDartFramework = Callable[[str, str, str], str | None]
ExtractDartCalls = Callable[[str, int], list[str]]
ExtractDartParams = Callable[[str], list[str]]


def extract_dart_regex(
    source: str,
    rel_path: str,
    detect_dart_framework: DetectDartFramework,
    extract_dart_calls: ExtractDartCalls,
    extract_dart_params: ExtractDartParams,
) -> list[dict[str, Any]]:
    symbols = []
    lines = source.split("\n")

    class_re = re.compile(r'^\s*(?:abstract\s+)?class\s+(\w+)')
    func_re = re.compile(r'^\s*(?:static\s+)?(?:Future<[^>]*>|void|int|double|String|bool|dynamic|List<[^>]*>|Map<[^>]*>|Widget|State<[^>]*>|\w+)\s+(\w+)\s*\(')
    top_func_re = re.compile(r'^(?:Future<[^>]*>|void|int|double|String|bool|dynamic|Widget|State<[^>]*>|\w+)\s+(\w+)\s*\(')
    enum_re = re.compile(r'^\s*enum\s+(\w+)')
    mixin_re = re.compile(r'^\s*mixin\s+(\w+)')
    ext_re = re.compile(r'^\s*extension\s+(\w+)')

    current_class = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        m = class_re.match(stripped)
        if m:
            name = m.group(1)
            framework = detect_dart_framework(name, stripped, source)
            symbols.append({
                "name": name,
                "type": "class",
                "line": i + 1,
                "framework": framework,
                "calls": extract_dart_calls(source, i),
            })
            current_class = name
            continue

        m = enum_re.match(stripped)
        if m:
            symbols.append({"name": m.group(1), "type": "enum", "line": i + 1})
            continue

        m = mixin_re.match(stripped)
        if m:
            symbols.append({"name": m.group(1), "type": "class", "line": i + 1, "framework": "dart-mixin"})
            continue

        m = ext_re.match(stripped)
        if m:
            symbols.append({"name": m.group(1), "type": "class", "line": i + 1, "framework": "dart-extension"})
            continue

        m = func_re.match(stripped)
        if m:
            name = m.group(1)
            if name not in ("if", "while", "for", "switch", "catch", "class", "return"):
                params = extract_dart_params(stripped)
                sym_type = "method" if current_class and line.startswith("  ") else "function"
                framework = detect_dart_framework(name, stripped, source)
                symbols.append({
                    "name": name,
                    "type": sym_type,
                    "line": i + 1,
                    "params": params,
                    "class": current_class if sym_type == "method" else None,
                    "framework": framework,
                    "calls": extract_dart_calls(source, i),
                })
        elif not line.startswith(" "):
            m = top_func_re.match(stripped)
            if m:
                name = m.group(1)
                if name not in ("if", "while", "for", "switch", "catch", "class", "return", "import"):
                    symbols.append({
                        "name": name,
                        "type": "function",
                        "line": i + 1,
                        "params": extract_dart_params(stripped),
                        "calls": extract_dart_calls(source, i),
                        "framework": detect_dart_framework(name, stripped, source),
                    })
            current_class = None

    return symbols


def extract_imports_regex(source: str, ext: str) -> list[dict[str, Any]]:
    imports = []
    if ext == ".dart":
        for match in re.finditer(r"import\s+'([^']+)'", source):
            module = match.group(1)
            imports.append({"module": module, "imported": []})
    return imports


def extract_dart_params(line: str) -> list[str]:
    match = re.search(r'\(([^)]*)\)', line)
    if not match:
        return []
    params_str = match.group(1).strip()
    if not params_str:
        return []
    params = []
    for param in params_str.split(","):
        param = param.strip().rstrip("?")
        parts = param.split()
        if len(parts) >= 2:
            params.append(parts[-1])
        elif parts:
            params.append(parts[0])
    return params[:8]


def extract_dart_calls(source: str, line_idx: int) -> list[str]:
    calls = set()
    lines = source.split("\n")
    for i in range(line_idx + 1, min(line_idx + 30, len(lines))):
        line = lines[i].strip()
        if line.startswith("class ") or line.startswith("enum "):
            break
        for match in re.finditer(r'(\w+)\s*\(', line):
            name = match.group(1)
            if name not in ("if", "while", "for", "switch", "catch", "return", "print"):
                calls.add(name)
    return list(calls)[:10]


def detect_dart_framework(name: str, line: str, source: str) -> str | None:
    if "extends StatelessWidget" in line or "extends StatelessWidget" in source[max(0, source.find(name) - 10):source.find(name) + 200]:
        return "flutter-widget"
    if "extends StatefulWidget" in line:
        return "flutter-stateful"
    if "extends State<" in line:
        return "flutter-state"
    if "Widget build(" in line:
        return "flutter-build"
    if "@override" in source[max(0, source.find(name) - 30):source.find(name) + 5]:
        pass
    ctx = source[max(0, source.find(f"class {name}")):source.find(f"class {name}") + 500] if f"class {name}" in source else ""
    if "extends ChangeNotifier" in ctx:
        return "flutter-provider"
    if "extends GetxController" in ctx or "extends GetxService" in ctx:
        return "flutter-getx"
    if "extends Bloc<" in ctx or "extends Cubit<" in ctx:
        return "flutter-bloc"
    if "extends Equatable" in ctx:
        return "dart-equatable"
    if "FirebaseAuth" in ctx or "FirebaseFirestore" in ctx or "FirebaseMessaging" in ctx:
        return "flutter-firebase"
    if "Dio()" in ctx or "http.get" in ctx or "http.post" in ctx:
        return "dart-http"
    if "extends StateNotifier" in ctx or "extends AsyncNotifier" in ctx:
        return "flutter-riverpod"
    if "extends ConsumerWidget" in ctx or "extends ConsumerStatefulWidget" in ctx:
        return "flutter-riverpod"

    return None
