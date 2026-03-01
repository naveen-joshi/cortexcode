"""AST Indexer - Parse code files and extract symbols, calls, and relationships."""

import json
import hashlib
import re
from pathlib import Path
from typing import Any

from tree_sitter import Language, Parser

from cortexcode.plugins import plugin_registry

import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript
import tree_sitter_go
import tree_sitter_rust
import tree_sitter_java
import tree_sitter_c_sharp

try:
    import tree_sitter_kotlin
    _HAS_KOTLIN = True
except ImportError:
    _HAS_KOTLIN = False

try:
    import tree_sitter_swift
    _HAS_SWIFT = True
except ImportError:
    _HAS_SWIFT = False


LANGUAGE_MAP = {
    ".py": ("python", tree_sitter_python.language),
    ".js": ("javascript", tree_sitter_javascript.language),
    ".jsx": ("javascript", tree_sitter_javascript.language),
    ".ts": ("typescript", tree_sitter_typescript.language_tsx),
    ".tsx": ("typescript", tree_sitter_typescript.language_tsx),
    ".go": ("go", tree_sitter_go.language),
    ".rs": ("rust", tree_sitter_rust.language),
    ".java": ("java", tree_sitter_java.language),
    ".cs": ("csharp", tree_sitter_c_sharp.language),
}

if _HAS_KOTLIN:
    LANGUAGE_MAP[".kt"] = ("kotlin", tree_sitter_kotlin.language)
    LANGUAGE_MAP[".kts"] = ("kotlin", tree_sitter_kotlin.language)

if _HAS_SWIFT:
    LANGUAGE_MAP[".swift"] = ("swift", tree_sitter_swift.language)

# Dart uses regex-based extraction (no tree-sitter pip package)
REGEX_LANGUAGES = {
    ".dart": "dart",
}


class CodeIndexer:
    """Parse source files and extract symbols, calls, and relationships."""
    
    SUPPORTED_EXTENSIONS = set(LANGUAGE_MAP.keys()) | set(REGEX_LANGUAGES.keys())
    
    @classmethod
    def get_all_extensions(cls) -> set[str]:
        """Get all supported extensions including plugin-registered ones."""
        return cls.SUPPORTED_EXTENSIONS | plugin_registry.registered_extensions
    
    def __init__(self):
        self.parsers: dict[str, Parser] = {}
        self.symbols: list[dict[str, Any]] = []
        self.call_graph: dict[str, list[str]] = {}
        self.file_symbols: dict[str, list[dict[str, Any]]] = {}
        self.gitignore_patterns: list[tuple[str, bool]] = []
        self.default_ignore_patterns = {
            "__pycache__", ".git", ".venv", "venv", "node_modules",
            ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cortexcode",
            "dist", "build", "target", ".idea", ".vscode", ".next", ".nuxt",
            ".svelte-kit", "coverage", ".cache", "*.log", ".env.local"
        }
    
    def _get_parser(self, ext: str) -> Parser | None:
        """Get or create a parser for the given extension."""
        if ext in self.parsers:
            return self.parsers[ext]
        
        if ext not in LANGUAGE_MAP:
            return None
        
        try:
            lang_func = LANGUAGE_MAP[ext][1]
            parser = Parser(Language(lang_func()))
            self.parsers[ext] = parser
            return parser
        except Exception as e:
            print(f"Failed to load parser for {ext}: {e}")
            return None
    
    def index_directory(self, root_path: Path, incremental: bool = False) -> dict[str, Any]:
        """Index all supported files in a directory.
        
        Args:
            root_path: Path to index
            incremental: If True, only re-index changed files based on hash
        """
        root_path = Path(root_path).resolve()
        self.symbols = []
        self.call_graph = {}
        self.file_symbols = {}
        self.parsers = {}
        
        self._load_gitignore(root_path)
        
        # Load plugins from config
        plugin_config = root_path / ".cortexcode" / "plugins.json"
        plugin_registry.load_from_config(plugin_config)
        
        old_hashes = {}
        if incremental:
            index_path = root_path / ".cortexcode" / "index.json"
            if index_path.exists():
                try:
                    old_index = json.loads(index_path.read_text(encoding="utf-8"))
                    old_hashes = old_index.get("file_hashes", {})
                except (json.JSONDecodeError, OSError):
                    pass
        
        for ext in self.get_all_extensions():
            for file_path in root_path.rglob(f"*{ext}"):
                if self._should_ignore(file_path, root_path):
                    continue
                
                if incremental and old_hashes:
                    try:
                        current_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
                        rel_path = str(file_path.relative_to(root_path))
                        if old_hashes.get(rel_path) == current_hash:
                            old_index_path = root_path / ".cortexcode" / "index.json"
                            if old_index_path.exists():
                                try:
                                    old_data = json.loads(old_index_path.read_text(encoding="utf-8"))
                                    if rel_path in old_data.get("files", {}):
                                        self.file_symbols[rel_path] = old_data["files"][rel_path]
                                        for sym in old_data["files"][rel_path].get("symbols", []):
                                            self.symbols.append(sym)
                                            name = sym.get("name")
                                            if name:
                                                if name not in self.call_graph:
                                                    self.call_graph[name] = []
                                                self.call_graph[name].extend(sym.get("calls", []))
                                        continue
                                except:
                                    pass
                    except OSError:
                        pass
                
                self._index_file(file_path, root_path)
        
        return self._build_index(root_path)
    
    def _load_gitignore(self, root: Path) -> None:
        """Load all .gitignore files from root and subdirectories."""
        self.gitignore_patterns = []
        
        for gitignore_path in root.rglob(".gitignore"):
            try:
                gitignore_dir = gitignore_path.parent
                rel_dir = gitignore_dir.relative_to(root) if gitignore_dir != root else Path(".")
                
                for line in gitignore_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    is_negation = line.startswith("!")
                    pattern = line[1:].strip() if is_negation else line
                    
                    if pattern:
                        full_pattern = str(rel_dir / pattern) if rel_dir != Path(".") else pattern
                        self.gitignore_patterns.append((full_pattern, is_negation))
            except (OSError, UnicodeDecodeError):
                continue
    
    def _matches_gitignore(self, file_path: Path, root: Path) -> bool:
        """Check if file matches gitignore patterns."""
        try:
            rel_path = file_path.relative_to(root)
            rel_str = str(rel_path)
            parts = rel_path.parts
            
            for pattern, is_negation in self.gitignore_patterns:
                if self._match_pattern(pattern, parts, rel_str):
                    return not is_negation
            
            return False
        except ValueError:
            return True
    
    def _match_pattern(self, pattern: str, parts: tuple, rel_str: str) -> bool:
        """Match a single gitignore pattern."""
        pattern = pattern.rstrip("/")
        
        if "/" in pattern:
            pattern_parts = pattern.split("/")
            if pattern.startswith("/"):
                pattern_parts[0] = pattern_parts[0][1:]
                if parts[:len(pattern_parts)] == tuple(pattern_parts):
                    return True
            else:
                for i in range(len(parts) - len(pattern_parts) + 1):
                    if parts[i:i+len(pattern_parts)] == tuple(pattern_parts):
                        return True
        else:
            for part in parts:
                if part == pattern or (pattern.startswith("*") and part.endswith(pattern[1:])):
                    return True
        
        if rel_str == pattern:
            return True
        
        return False
    
    def _should_ignore(self, file_path: Path, root: Path) -> bool:
        """Check if file should be ignored based on gitignore or defaults."""
        path_str = str(file_path)
        
        for pattern in self.default_ignore_patterns:
            if pattern in path_str:
                return True
        
        return self._matches_gitignore(file_path, root)
    
    def _index_file(self, file_path: Path, root: Path) -> None:
        """Index a single file."""
        ext = file_path.suffix.lower()
        
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return
        
        rel_path = str(file_path.relative_to(root))
        
        # Plugin-based extraction (custom framework plugins)
        plugin_symbols = plugin_registry.extract_symbols(content, ext, rel_path)
        if plugin_symbols is not None:
            plugin_imports = plugin_registry.extract_imports(content, ext) or []
            file_data = {
                "symbols": plugin_symbols,
                "imports": plugin_imports,
                "exports": [],
                "api_routes": [],
                "entities": [],
            }
            self.file_symbols[rel_path] = file_data
            self.symbols.extend(plugin_symbols)
            for sym in plugin_symbols:
                name = sym.get("name", "")
                if name:
                    if name not in self.call_graph:
                        self.call_graph[name] = []
                    self.call_graph[name].extend(sym.get("calls", []))
            return
        
        # Regex-based languages (Dart)
        if ext in REGEX_LANGUAGES:
            symbols = self._extract_regex(content, ext, rel_path)
            imports = self._extract_imports_regex(content, ext)
            file_data = {
                "symbols": symbols,
                "imports": imports,
                "exports": [],
                "api_routes": [],
                "entities": [],
            }
            self.file_symbols[rel_path] = file_data
            self.symbols.extend(symbols)
            for sym in symbols:
                name = sym["name"]
                if name not in self.call_graph:
                    self.call_graph[name] = []
                self.call_graph[name].extend(sym.get("calls", []))
            return
        
        parser = self._get_parser(ext)
        if not parser:
            return
        
        try:
            tree = parser.parse(bytes(content, "utf8"))
        except Exception:
            return
        
        symbols = self._extract_symbols(content, tree.root_node, ext)
        
        imports = self._extract_imports(content, tree.root_node, ext)
        exports = self._extract_exports(content, tree.root_node, ext)
        api_routes = self._extract_api_routes(content, tree.root_node, ext)
        entities = self._extract_entities(content, tree.root_node, ext)
        
        file_data = {
            "symbols": symbols,
            "imports": imports,
            "exports": exports,
            "api_routes": api_routes,
            "entities": entities,
        }
        
        self.file_symbols[rel_path] = file_data
        self.symbols.extend(symbols)
        
        for sym in symbols:
            name = sym["name"]
            if name not in self.call_graph:
                self.call_graph[name] = []
            self.call_graph[name].extend(sym.get("calls", []))
    
    def _extract_symbols(self, source: str, node, ext: str) -> list[dict[str, Any]]:
        """Extract all symbols from AST based on language."""
        symbols = []
        
        if ext == ".py":
            self._extract_python(source, node, symbols, None)
        elif ext in (".js", ".jsx"):
            self._extract_javascript(source, node, symbols, None)
        elif ext in (".ts", ".tsx"):
            self._extract_typescript(source, node, symbols, None)
        elif ext == ".go":
            self._extract_go(source, node, symbols, None)
        elif ext == ".rs":
            self._extract_rust(source, node, symbols, None)
        elif ext == ".java":
            self._extract_java(source, node, symbols, None)
        elif ext == ".cs":
            self._extract_csharp(source, node, symbols, None)
        elif ext in (".kt", ".kts"):
            self._extract_kotlin(source, node, symbols, None)
        elif ext == ".swift":
            self._extract_swift(source, node, symbols, None)
        
        return symbols
    
    def _extract_python(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Python symbols."""
        self._extract_generic(source, node, symbols, current_class, "function_definition", "class_definition")
    
    def _extract_javascript(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract JavaScript/React symbols."""
        self._extract_js_ts_generic(source, node, symbols, current_class, is_ts=False)
    
    def _extract_typescript(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract TypeScript/Angular/Next.js symbols."""
        self._extract_js_ts_generic(source, node, symbols, current_class, is_ts=True)
    
    def _extract_js_ts_generic(self, source: str, node, symbols: list, current_class: str | None, is_ts: bool) -> None:
        """Extract JavaScript/TypeScript with framework support."""
        node_type = node.type
        
        if node_type == "function_declaration":
            name = self._get_node_name(node, source)
            if name:
                params = self._extract_params(node, source, node_type)
                calls = self._extract_calls(node, source)
                doc = self._extract_jsdoc(node, source)
                
                sym_type = "method" if current_class else "function"
                framework = self._detect_framework(name, node, source)
                
                sym = {
                    "name": name,
                    "type": sym_type,
                    "line": node.start_point.row + 1,
                    "params": params,
                    "calls": calls,
                    "class": current_class,
                    "framework": framework,
                }
                if doc:
                    sym["doc"] = doc
                symbols.append(sym)
        
        elif node_type in ("lexical_declaration", "variable_declaration"):
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value")
                    
                    if name_node and value_node:
                        name = name_node.text.decode("utf-8")
                        
                        if value_node.type in ("arrow_function", "function_expression", "function"):
                            params = self._extract_params(value_node, source, value_node.type)
                            calls = self._extract_calls(value_node, source)
                            return_type = self._extract_return_type(value_node, source) if is_ts else None
                            doc = self._extract_jsdoc(node, source)
                            
                            sym_type = "method" if current_class else "function"
                            framework = self._detect_framework(name, value_node, source)
                            
                            sym = {
                                "name": name,
                                "type": sym_type,
                                "line": node.start_point.row + 1,
                                "params": params,
                                "calls": calls,
                                "class": current_class,
                                "framework": framework,
                            }
                            if return_type:
                                sym["return_type"] = return_type
                            if doc:
                                sym["doc"] = doc
                            symbols.append(sym)
                        
                        elif value_node.type == "call_expression":
                            # const router = express.Router() or similar
                            pass
        
        elif node_type in ("export_statement", "export_default_declaration"):
            for child in node.children:
                self._extract_js_ts_generic(source, child, symbols, current_class, is_ts)
            return
        
        elif node_type in ("class_declaration", "class_expression"):
            name = self._get_node_name(node, source)
            if name:
                methods = []
                class_calls = []
                
                for child in node.children:
                    if child.type == "class_body":
                        for member in child.children:
                            if member.type in ("method_definition", "public_field_definition", "field_definition"):
                                method_name = self._get_node_name(member, source)
                                if method_name:
                                    params = self._extract_params(member, source, member.type)
                                    method_calls = self._extract_calls(member, source)
                                    methods.append({
                                        "name": method_name,
                                        "type": "method",
                                        "line": member.start_point.row + 1,
                                        "params": params,
                                        "calls": method_calls,
                                    })
                                    class_calls.extend(method_calls)
                
                framework = self._detect_class_framework(name, node, source)
                
                symbols.append({
                    "name": name,
                    "type": "class",
                    "line": node.start_point.row + 1,
                    "methods": methods,
                    "calls": list(set(class_calls)),
                    "framework": framework,
                })
                
                current_class = name
        
        elif is_ts and node_type == "interface_declaration":
            name = self._get_node_name(node, source)
            if name:
                members = []
                for child in node.children:
                    if child.type == "object_type" or child.type == "interface_body":
                        for member in child.children:
                            prop_name = self._get_node_name(member, source)
                            if prop_name:
                                members.append(prop_name)
                symbols.append({
                    "name": name,
                    "type": "interface",
                    "line": node.start_point.row + 1,
                    "members": members if members else None,
                    "framework": "typescript",
                })
        
        elif is_ts and node_type == "type_alias_declaration":
            name = self._get_node_name(node, source)
            if name:
                symbols.append({
                    "name": name,
                    "type": "type",
                    "line": node.start_point.row + 1,
                    "framework": "typescript",
                })
        
        elif is_ts and node_type == "enum_declaration":
            name = self._get_node_name(node, source)
            if name:
                symbols.append({
                    "name": name,
                    "type": "enum",
                    "line": node.start_point.row + 1,
                    "framework": "typescript",
                })
        
        for child in node.children:
            self._extract_js_ts_generic(source, child, symbols, current_class, is_ts)
    
    def _extract_return_type(self, node, source: str) -> str | None:
        """Extract return type annotation from a function node."""
        type_ann = node.child_by_field_name("return_type")
        if type_ann:
            return type_ann.text.decode("utf-8").lstrip(": ").strip()
        return None
    
    def _detect_framework(self, name: str, node, source: str) -> str | None:
        """Detect framework: React, React Native, Expo, Next.js, NestJS, Express, FastAPI, Django, Flask."""
        source_bytes = node.text if hasattr(node, 'text') else b''
        source_str = source_bytes.decode("utf-8", errors="ignore")
        
        # React Native specific hooks/APIs
        if any(rn in source_str for rn in ("useNavigation", "useRoute", "useAnimatedStyle", "useSharedValue")):
            return "react-native-hook"
        if any(rn in source_str for rn in ("StyleSheet.create", "Dimensions.get", "PixelRatio")):
            return "react-native-util"
        
        # React Native components (import check)
        rn_components = ("View", "Text", "TouchableOpacity", "FlatList", "ScrollView", "SafeAreaView", "StatusBar", "Alert", "Modal")
        if name and name[0].isupper() and any(f"<{c}" in source_str or f"{c}>" in source_str for c in rn_components):
            return "react-native-component"
        
        # Expo
        if any(expo in source_str for expo in ("expo-", "usePermissions", "useCameraPermissions", "useAssets", "Notifications.schedule")):
            return "expo"
        if "expo-router" in source_str or "useLocalSearchParams" in source_str or "useGlobalSearchParams" in source_str:
            return "expo-router"
        
        # React hooks
        if "useState" in source_str or "useEffect" in source_str or "useContext" in source_str or "useReducer" in source_str or "useMemo" in source_str:
            if name and name[0].isupper():
                return "react-component"
            if name and name.startswith("use"):
                return "react-hook"
            return "react-hook"
        
        # Next.js App Router
        if name in ("generateMetadata", "generateStaticParams"):
            return "nextjs-app-router"
        if "'use server'" in source_str or '"use server"' in source_str:
            return "nextjs-server-action"
        if "'use client'" in source_str or '"use client"' in source_str:
            return "nextjs-client"
        
        # Next.js Pages Router
        if "getServerSideProps" in name or "getStaticProps" in name or "getStaticPaths" in name:
            return "nextjs-ssg"
        if "getServerSideProps" in source_str or "getStaticProps" in source_str:
            return "nextjs-page"
        
        # NestJS
        if "@Get(" in source_str or "@Post(" in source_str or "@Put(" in source_str or "@Delete(" in source_str or "@Patch(" in source_str:
            return "nestjs-controller"
        if "@Injectable" in source_str:
            return "nestjs-service"
        if "@Controller" in source_str and "nestjs" not in source_str.lower():
            return "nestjs-controller"
        if "@Guard" in source_str or "CanActivate" in source_str:
            return "nestjs-guard"
        if "@Pipe" in source_str or "PipeTransform" in source_str:
            return "nestjs-pipe"
        
        # Express
        if "app.get(" in source_str or "app.post(" in source_str or "router.get(" in source_str or "router.post(" in source_str:
            return "express-route"
        if "app.use(" in source_str and "router" not in name:
            return "express-middleware"
        
        # FastAPI (Python)
        if "@app.get(" in source_str or "@app.post(" in source_str or "@router.get(" in source_str or "@router.post(" in source_str:
            return "fastapi-endpoint"
        if "Depends(" in source_str and ("async def" in source_str or "def " in source_str):
            return "fastapi-dependency"
        
        # Django
        if "request.method" in source_str or "HttpResponse" in source_str or "JsonResponse" in source_str:
            return "django-view"
        if "@api_view" in source_str or "APIView" in source_str:
            return "django-rest"
        
        # Flask
        if "@app.route(" in source_str or "@blueprint.route(" in source_str:
            return "flask-route"
        
        # Remix
        if name in ("loader", "action") and ("json(" in source_str or "redirect(" in source_str):
            return "remix-loader"
        
        # React component (PascalCase + return JSX) — must be last React check
        if name and name[0].isupper() and ("return" in source_str or "=>" in source_str):
            if "<" in source_str:
                return "react-component"
        
        return None
    
    def _detect_class_framework(self, name: str, node, source: str) -> str | None:
        """Detect class-level framework: Angular, React Native, NestJS, etc."""
        source_bytes = node.text if hasattr(node, 'text') else b''
        source_str = source_bytes.decode("utf-8", errors="ignore")
        
        # Angular
        if "@Component" in source_str:
            return "angular-component"
        elif "@Injectable" in source_str:
            return "angular-service"
        elif "@NgModule" in source_str:
            return "angular-module"
        elif "@Directive" in source_str:
            return "angular-directive"
        elif "@Pipe" in source_str and "PipeTransform" in source_str:
            return "angular-pipe"
        
        # React Native class component
        elif "extends Component" in source_str or "extends PureComponent" in source_str:
            rn_indicators = ("View", "Text", "TouchableOpacity", "FlatList", "StyleSheet")
            if any(ind in source_str for ind in rn_indicators):
                return "react-native-component"
            return "react-class-component"
        
        # NestJS
        elif "@Controller" in source_str:
            return "nestjs-controller"
        elif "@Injectable" in source_str and "nestjs" not in source_str.lower():
            return "nestjs-service"
        elif "@Module" in source_str and "imports:" in source_str:
            return "nestjs-module"
        
        # Spring Boot
        elif "@Controller" in source_str or "@RestController" in source_str:
            return "spring-boot"
        
        return None
    
    def _extract_go(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Go symbols."""
        self._extract_generic(source, node, symbols, current_class, "function_declaration", "method_declaration", "type_declaration")
    
    def _extract_rust(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Rust symbols."""
        self._extract_generic(source, node, symbols, current_class, "function_item", "struct_item", "impl_item", "enum_item")
    
    def _extract_java(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Java symbols with Spring Boot detection."""
        self._extract_java_with_framework(source, node, symbols, current_class)
    
    def _extract_java_with_framework(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Java with Spring Boot framework detection."""
        node_type = node.type
        
        if node_type == "method_declaration":
            name = self._get_node_name(node, source)
            if name:
                params = self._extract_params(node, source, node_type)
                calls = self._extract_calls(node, source)
                
                symbols.append({
                    "name": name,
                    "type": "method",
                    "line": node.start_point.row + 1,
                    "params": params,
                    "calls": calls,
                    "class": current_class,
                })
        
        elif node_type == "class_declaration":
            name = self._get_node_name(node, source)
            if name:
                methods = []
                class_calls = []
                
                for child in node.children:
                    if child.type == "method_declaration":
                        method_name = self._get_node_name(child, source)
                        if method_name:
                            params = self._extract_params(child, source, child.type)
                            method_calls = self._extract_calls(child, source)
                            methods.append({
                                "name": method_name,
                                "type": "method",
                                "line": child.start_point.row + 1,
                                "params": params,
                                "calls": method_calls,
                            })
                            class_calls.extend(method_calls)
                
                framework = self._detect_java_framework(name, node, source)
                
                symbols.append({
                    "name": name,
                    "type": "class",
                    "line": node.start_point.row + 1,
                    "methods": methods,
                    "calls": list(set(class_calls)),
                    "framework": framework,
                })
                
                current_class = name
        
        elif node_type == "interface_declaration":
            name = self._get_node_name(node, source)
            if name:
                symbols.append({
                    "name": name,
                    "type": "interface",
                    "line": node.start_point.row + 1,
                    "framework": self._detect_java_framework(name, node, source),
                })
        
        for child in node.children:
            self._extract_java_with_framework(source, child, symbols, current_class)
    
    def _detect_java_framework(self, name: str, node, source: str) -> str | None:
        """Detect Spring Boot and Android framework patterns."""
        source_bytes = node.text if hasattr(node, 'text') else b''
        source_str = source_bytes.decode("utf-8", errors="ignore")
        
        # Android
        if "extends AppCompatActivity" in source_str or "extends Activity" in source_str or "extends FragmentActivity" in source_str:
            return "android-activity"
        if "extends Fragment" in source_str or "extends DialogFragment" in source_str:
            return "android-fragment"
        if "extends ViewModel" in source_str or "extends AndroidViewModel" in source_str:
            return "android-viewmodel"
        if "extends Service" in source_str or "extends IntentService" in source_str:
            return "android-service"
        if "extends BroadcastReceiver" in source_str:
            return "android-receiver"
        if "extends ContentProvider" in source_str:
            return "android-provider"
        if "extends RecyclerView.Adapter" in source_str or "extends ArrayAdapter" in source_str:
            return "android-adapter"
        if "@Entity" in source_str and "@ColumnInfo" in source_str:
            return "android-room"
        if "@Dao" in source_str and ("@Query" in source_str or "@Insert" in source_str):
            return "android-room"
        if "@Database" in source_str and "RoomDatabase" in source_str:
            return "android-room-db"
        if "@HiltAndroidApp" in source_str or "@AndroidEntryPoint" in source_str:
            return "android-hilt"
        
        # Spring Boot
        if "@Entity" in source_str or "@Table" in source_str:
            return "spring-entity"
        elif "@Repository" in source_str:
            return "spring-repository"
        elif "@Service" in source_str:
            return "spring-service"
        elif "@Controller" in source_str or "@RestController" in source_str:
            return "spring-controller"
        elif "@Component" in source_str:
            return "spring-component"
        elif "@Configuration" in source_str:
            return "spring-config"
        
        return None
    
    def _extract_csharp(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract C# with .NET framework detection."""
        self._extract_csharp_with_framework(source, node, symbols, current_class)
    
    def _extract_csharp_with_framework(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract C# with .NET framework detection."""
        node_type = node.type
        
        if node_type in ("method_declaration", "local_function_statement"):
            name = self._get_node_name(node, source)
            if name:
                params = self._extract_params(node, source, node_type)
                calls = self._extract_calls(node, source)
                
                symbols.append({
                    "name": name,
                    "type": "method",
                    "line": node.start_point.row + 1,
                    "params": params,
                    "calls": calls,
                    "class": current_class,
                })
        
        elif node_type == "class_declaration":
            name = self._get_node_name(node, source)
            if name:
                methods = []
                class_calls = []
                
                for child in node.children:
                    if child.type == "method_declaration":
                        method_name = self._get_node_name(child, source)
                        if method_name:
                            params = self._extract_params(child, source, child.type)
                            method_calls = self._extract_calls(child, source)
                            methods.append({
                                "name": method_name,
                                "type": "method",
                                "line": child.start_point.row + 1,
                                "params": params,
                                "calls": method_calls,
                            })
                            class_calls.extend(method_calls)
                
                framework = self._detect_csharp_framework(name, node, source)
                
                symbols.append({
                    "name": name,
                    "type": "class",
                    "line": node.start_point.row + 1,
                    "methods": methods,
                    "calls": list(set(class_calls)),
                    "framework": framework,
                })
                
                current_class = name
        
        elif node_type == "interface_declaration":
            name = self._get_node_name(node, source)
            if name:
                symbols.append({
                    "name": name,
                    "type": "interface",
                    "line": node.start_point.row + 1,
                })
        
        for child in node.children:
            self._extract_csharp_with_framework(source, child, symbols, current_class)
    
    def _detect_csharp_framework(self, name: str, node, source: str) -> str | None:
        """Detect .NET framework patterns."""
        source_bytes = node.text if hasattr(node, 'text') else b''
        source_str = source_bytes.decode("utf-8", errors="ignore")
        
        if "[ApiController]" in source_str or "ControllerBase" in source_str:
            return "aspnet-controller"
        elif "[Route(" in source_str or "[HttpGet]" in source_str or "[HttpPost]" in source_str:
            return "aspnet-webapi"
        elif "[DataContract]" in source_str or "[DataMember]" in source_str:
            return "wcf-service"
        elif "DbContext" in source_str or "DbSet<" in source_str:
            return "ef-entity"
        
        return None
    
    def _extract_kotlin(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Kotlin symbols with Android framework detection."""
        self._extract_kotlin_recursive(source, node, symbols, current_class)
    
    def _extract_kotlin_recursive(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Recursively extract Kotlin symbols."""
        node_type = node.type
        
        if node_type == "function_declaration":
            name = self._get_node_name(node, source)
            if name:
                params = self._extract_params(node, source, node_type)
                calls = self._extract_calls(node, source)
                framework = self._detect_kotlin_framework(name, node, source)
                sym_type = "method" if current_class else "function"
                symbols.append({
                    "name": name, "type": sym_type,
                    "line": node.start_point.row + 1,
                    "params": params, "calls": calls,
                    "class": current_class, "framework": framework,
                })
        
        elif node_type == "class_declaration":
            name = self._get_node_name(node, source)
            if name:
                methods = []
                class_calls = []
                for child in node.children:
                    if child.type == "class_body":
                        for member in child.children:
                            if member.type == "function_declaration":
                                m_name = self._get_node_name(member, source)
                                if m_name:
                                    m_params = self._extract_params(member, source, member.type)
                                    m_calls = self._extract_calls(member, source)
                                    methods.append({"name": m_name, "type": "method", "line": member.start_point.row + 1, "params": m_params, "calls": m_calls})
                                    class_calls.extend(m_calls)
                
                framework = self._detect_kotlin_framework(name, node, source)
                symbols.append({
                    "name": name, "type": "class",
                    "line": node.start_point.row + 1,
                    "methods": methods, "calls": list(set(class_calls)),
                    "framework": framework,
                })
                current_class = name
        
        elif node_type == "object_declaration":
            name = self._get_node_name(node, source)
            if name:
                symbols.append({
                    "name": name, "type": "class",
                    "line": node.start_point.row + 1,
                    "framework": self._detect_kotlin_framework(name, node, source),
                })
        
        for child in node.children:
            self._extract_kotlin_recursive(source, child, symbols, current_class)
    
    def _detect_kotlin_framework(self, name: str, node, source: str) -> str | None:
        """Detect Android/Compose/Ktor framework patterns in Kotlin."""
        src = node.text.decode("utf-8", errors="ignore") if hasattr(node, 'text') else ""
        
        # Jetpack Compose
        if "@Composable" in src:
            return "compose-ui"
        if "@Preview" in src:
            return "compose-preview"
        # Android Activity/Fragment/ViewModel
        if ": AppCompatActivity()" in src or ": Activity()" in src or ": ComponentActivity()" in src:
            return "android-activity"
        if ": Fragment()" in src or ": DialogFragment()" in src:
            return "android-fragment"
        if ": ViewModel()" in src or ": AndroidViewModel(" in src:
            return "android-viewmodel"
        if ": Service()" in src or ": IntentService(" in src:
            return "android-service"
        if ": BroadcastReceiver()" in src:
            return "android-receiver"
        if ": ContentProvider()" in src:
            return "android-provider"
        # Ktor
        if "routing {" in src or "get(" in src and "call.respond" in src:
            return "ktor-route"
        # Room database
        if "@Entity" in src or "@Dao" in src:
            return "android-room"
        if "@Database" in src:
            return "android-room-db"
        # Hilt/Dagger
        if "@HiltViewModel" in src or "@HiltAndroidApp" in src:
            return "android-hilt"
        if "@Inject" in src or "@Module" in src:
            return "android-di"
        
        return None
    
    def _extract_swift(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Extract Swift symbols with iOS framework detection."""
        self._extract_swift_recursive(source, node, symbols, current_class)
    
    def _extract_swift_recursive(self, source: str, node, symbols: list, current_class: str | None) -> None:
        """Recursively extract Swift symbols."""
        node_type = node.type
        
        if node_type == "function_declaration":
            name = self._get_node_name(node, source)
            if name:
                params = self._extract_params(node, source, node_type)
                calls = self._extract_calls(node, source)
                framework = self._detect_swift_framework(name, node, source)
                sym_type = "method" if current_class else "function"
                symbols.append({
                    "name": name, "type": sym_type,
                    "line": node.start_point.row + 1,
                    "params": params, "calls": calls,
                    "class": current_class, "framework": framework,
                })
        
        elif node_type == "class_declaration":
            name = self._get_node_name(node, source)
            if name:
                methods = []
                class_calls = []
                for child in node.children:
                    if child.type == "class_body":
                        for member in child.children:
                            if member.type == "function_declaration":
                                m_name = self._get_node_name(member, source)
                                if m_name:
                                    m_params = self._extract_params(member, source, member.type)
                                    m_calls = self._extract_calls(member, source)
                                    methods.append({"name": m_name, "type": "method", "line": member.start_point.row + 1, "params": m_params, "calls": m_calls})
                                    class_calls.extend(m_calls)
                
                framework = self._detect_swift_framework(name, node, source)
                symbols.append({
                    "name": name, "type": "class",
                    "line": node.start_point.row + 1,
                    "methods": methods, "calls": list(set(class_calls)),
                    "framework": framework,
                })
                current_class = name
        
        elif node_type == "protocol_declaration":
            name = self._get_node_name(node, source)
            if name:
                symbols.append({
                    "name": name, "type": "interface",
                    "line": node.start_point.row + 1,
                    "framework": "swift",
                })
        
        elif node_type in ("struct_declaration",):
            name = self._get_node_name(node, source)
            if name:
                framework = self._detect_swift_framework(name, node, source)
                symbols.append({
                    "name": name, "type": "class",
                    "line": node.start_point.row + 1,
                    "framework": framework,
                })
        
        elif node_type == "enum_declaration":
            name = self._get_node_name(node, source)
            if name:
                symbols.append({
                    "name": name, "type": "enum",
                    "line": node.start_point.row + 1,
                })
        
        for child in node.children:
            self._extract_swift_recursive(source, child, symbols, current_class)
    
    def _detect_swift_framework(self, name: str, node, source: str) -> str | None:
        """Detect iOS/SwiftUI/UIKit framework patterns."""
        src = node.text.decode("utf-8", errors="ignore") if hasattr(node, 'text') else ""
        
        # SwiftUI
        if ": View" in src and "var body:" in src:
            return "swiftui-view"
        if "@ObservedObject" in src or "@StateObject" in src or "@EnvironmentObject" in src:
            return "swiftui-view"
        if "ObservableObject" in src:
            return "swiftui-observable"
        if "@State " in src or "@Binding " in src:
            return "swiftui-state"
        if "@main" in src and "App" in name:
            return "swiftui-app"
        # UIKit
        if ": UIViewController" in src:
            return "uikit-viewcontroller"
        if ": UITableViewDelegate" in src or ": UITableViewDataSource" in src:
            return "uikit-tableview"
        if ": UICollectionViewDelegate" in src:
            return "uikit-collectionview"
        if ": UIView" in src and ": UIViewController" not in src:
            return "uikit-view"
        # Combine
        if "AnyPublisher" in src or "@Published" in src or "sink(" in src:
            return "combine"
        # Core Data
        if ": NSManagedObject" in src or "@NSManaged" in src:
            return "coredata-entity"
        if "NSPersistentContainer" in src:
            return "coredata"
        # Vapor (server-side Swift)
        if "req.content" in src or "app.get(" in src or "app.post(" in src:
            return "vapor-route"
        
        return None
    
    def _extract_regex(self, source: str, ext: str, rel_path: str) -> list[dict[str, Any]]:
        """Regex-based symbol extraction for languages without tree-sitter (Dart)."""
        if ext == ".dart":
            return self._extract_dart_regex(source, rel_path)
        return []
    
    def _extract_dart_regex(self, source: str, rel_path: str) -> list[dict[str, Any]]:
        """Extract Dart/Flutter symbols using regex."""
        symbols = []
        lines = source.split("\n")
        
        # Class pattern: class Name extends/implements/with ... {
        class_re = re.compile(r'^\s*(?:abstract\s+)?class\s+(\w+)')
        # Function pattern: ReturnType name(params) { or => 
        func_re = re.compile(r'^\s*(?:static\s+)?(?:Future<[^>]*>|void|int|double|String|bool|dynamic|List<[^>]*>|Map<[^>]*>|Widget|State<[^>]*>|\w+)\s+(\w+)\s*\(')
        # Top-level function: type name(
        top_func_re = re.compile(r'^(?:Future<[^>]*>|void|int|double|String|bool|dynamic|Widget|State<[^>]*>|\w+)\s+(\w+)\s*\(')
        # Enum
        enum_re = re.compile(r'^\s*enum\s+(\w+)')
        # Mixin
        mixin_re = re.compile(r'^\s*mixin\s+(\w+)')
        # Extension
        ext_re = re.compile(r'^\s*extension\s+(\w+)')
        
        current_class = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Class
            m = class_re.match(stripped)
            if m:
                name = m.group(1)
                framework = self._detect_dart_framework(name, stripped, source)
                symbols.append({
                    "name": name, "type": "class",
                    "line": i + 1,
                    "framework": framework,
                    "calls": self._extract_dart_calls(source, i),
                })
                current_class = name
                continue
            
            # Enum
            m = enum_re.match(stripped)
            if m:
                symbols.append({"name": m.group(1), "type": "enum", "line": i + 1})
                continue
            
            # Mixin
            m = mixin_re.match(stripped)
            if m:
                symbols.append({"name": m.group(1), "type": "class", "line": i + 1, "framework": "dart-mixin"})
                continue
            
            # Extension
            m = ext_re.match(stripped)
            if m:
                symbols.append({"name": m.group(1), "type": "class", "line": i + 1, "framework": "dart-extension"})
                continue
            
            # Function/method
            m = func_re.match(stripped)
            if m:
                name = m.group(1)
                if name not in ("if", "while", "for", "switch", "catch", "class", "return"):
                    params = self._extract_dart_params(stripped)
                    sym_type = "method" if current_class and line.startswith("  ") else "function"
                    framework = self._detect_dart_framework(name, stripped, source)
                    symbols.append({
                        "name": name, "type": sym_type,
                        "line": i + 1, "params": params,
                        "class": current_class if sym_type == "method" else None,
                        "framework": framework,
                        "calls": self._extract_dart_calls(source, i),
                    })
            elif not line.startswith(" "):
                # Top-level function
                m = top_func_re.match(stripped)
                if m:
                    name = m.group(1)
                    if name not in ("if", "while", "for", "switch", "catch", "class", "return", "import"):
                        symbols.append({
                            "name": name, "type": "function",
                            "line": i + 1,
                            "params": self._extract_dart_params(stripped),
                            "calls": self._extract_dart_calls(source, i),
                            "framework": self._detect_dart_framework(name, stripped, source),
                        })
                current_class = None
        
        return symbols
    
    def _extract_dart_params(self, line: str) -> list[str]:
        """Extract parameters from a Dart function line."""
        m = re.search(r'\(([^)]*)\)', line)
        if not m:
            return []
        params_str = m.group(1).strip()
        if not params_str:
            return []
        params = []
        for p in params_str.split(","):
            p = p.strip().rstrip("?")
            parts = p.split()
            if len(parts) >= 2:
                params.append(parts[-1])
            elif parts:
                params.append(parts[0])
        return params[:8]
    
    def _extract_dart_calls(self, source: str, line_idx: int) -> list[str]:
        """Extract function calls near a Dart function definition."""
        calls = set()
        lines = source.split("\n")
        # Scan next 30 lines for calls
        for i in range(line_idx + 1, min(line_idx + 30, len(lines))):
            line = lines[i].strip()
            if line.startswith("class ") or line.startswith("enum "):
                break
            for m in re.finditer(r'(\w+)\s*\(', line):
                name = m.group(1)
                if name not in ("if", "while", "for", "switch", "catch", "return", "print"):
                    calls.add(name)
        return list(calls)[:10]
    
    def _detect_dart_framework(self, name: str, line: str, source: str) -> str | None:
        """Detect Flutter/Dart framework patterns."""
        # Flutter widgets
        if "extends StatelessWidget" in line or "extends StatelessWidget" in source[max(0,source.find(name)-10):source.find(name)+200]:
            return "flutter-widget"
        if "extends StatefulWidget" in line:
            return "flutter-stateful"
        if "extends State<" in line:
            return "flutter-state"
        # Flutter specific
        if "Widget build(" in line:
            return "flutter-build"
        if "@override" in source[max(0,source.find(name)-30):source.find(name)+5]:
            pass  # Could be any override
        # Check class body for Flutter patterns
        ctx = source[max(0,source.find(f"class {name}")):source.find(f"class {name}")+500] if f"class {name}" in source else ""
        if "extends ChangeNotifier" in ctx:
            return "flutter-provider"
        if "extends GetxController" in ctx or "extends GetxService" in ctx:
            return "flutter-getx"
        if "extends Bloc<" in ctx or "extends Cubit<" in ctx:
            return "flutter-bloc"
        if "extends Equatable" in ctx:
            return "dart-equatable"
        # Firebase
        if "FirebaseAuth" in ctx or "FirebaseFirestore" in ctx or "FirebaseMessaging" in ctx:
            return "flutter-firebase"
        # Dio/HTTP
        if "Dio()" in ctx or "http.get" in ctx or "http.post" in ctx:
            return "dart-http"
        # Riverpod
        if "extends StateNotifier" in ctx or "extends AsyncNotifier" in ctx:
            return "flutter-riverpod"
        if "extends ConsumerWidget" in ctx or "extends ConsumerStatefulWidget" in ctx:
            return "flutter-riverpod"
        
        return None
    
    def _extract_imports_regex(self, source: str, ext: str) -> list[dict]:
        """Extract imports using regex for non-tree-sitter languages."""
        imports = []
        if ext == ".dart":
            for m in re.finditer(r"import\s+'([^']+)'", source):
                module = m.group(1)
                imports.append({"module": module, "imported": []})
        return imports
    
    def _extract_generic(self, source: str, node, symbols: list, current_class: str | None, 
                         func_types: str, class_types: str, *extra_types: str) -> None:
        """Generic symbol extraction for multiple node types."""
        node_type = node.type
        
        func_type_set = {func_types} if isinstance(func_types, str) else set(func_types)
        class_type_set = {class_types} if isinstance(class_types, str) else set(class_types)
        all_type_set = func_type_set | class_type_set | set(extra_types)
        
        if node_type in func_type_set:
            name = self._get_node_name(node, source)
            if name:
                params = self._extract_params(node, source, node_type)
                calls = self._extract_calls(node, source)
                doc = self._extract_docstring(node, source)
                
                sym_type = "function"
                if current_class:
                    sym_type = "method"
                
                sym = {
                    "name": name,
                    "type": sym_type,
                    "line": node.start_point.row + 1,
                    "params": params,
                    "calls": calls,
                    "class": current_class,
                }
                if doc:
                    sym["doc"] = doc
                symbols.append(sym)
        
        elif node_type in class_type_set:
            name = self._get_node_name(node, source)
            if name:
                methods = []
                class_calls = []
                doc = self._extract_docstring(node, source)
                
                for child in node.children:
                    if child.type in func_type_set or (extra_types and child.type in extra_types):
                        method_name = self._get_node_name(child, source)
                        if method_name:
                            params = self._extract_params(child, source, child.type)
                            method_calls = self._extract_calls(child, source)
                            method_doc = self._extract_docstring(child, source)
                            m = {
                                "name": method_name,
                                "type": "method",
                                "line": child.start_point.row + 1,
                                "params": params,
                                "calls": method_calls,
                            }
                            if method_doc:
                                m["doc"] = method_doc
                            methods.append(m)
                            class_calls.extend(method_calls)
                
                sym = {
                    "name": name,
                    "type": "class",
                    "line": node.start_point.row + 1,
                    "methods": methods,
                    "calls": list(set(class_calls)),
                }
                if doc:
                    sym["doc"] = doc
                symbols.append(sym)
                
                current_class = name
        
        for child in node.children:
            self._extract_generic(source, child, symbols, current_class, func_types, class_types, *extra_types)
    
    def _get_node_name(self, node, source: str) -> str | None:
        """Get name from definition node."""
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode("utf-8")
        return None
    
    def _extract_params(self, func_node, source: str, node_type: str) -> list[str]:
        """Extract function parameters."""
        params = []
        
        for child in func_node.children:
            if child.type == "parameters":
                for param in child.children:
                    if param.type == "identifier":
                        params.append(param.text.decode("utf-8"))
                    elif param.type in ("optional_parameter", "rest_parameter", "spread_element",
                                        "typed_parameter", "default_parameter", "keyword_argument",
                                        "parameter", "receiver"):
                        for p in param.children:
                            if p.type == "identifier":
                                params.append(p.text.decode("utf-8"))
                                break
        
        return params
    
    def _extract_calls(self, func_node, source: str) -> list[str]:
        """Extract function calls within a function body."""
        calls = []
        self._find_calls_recursive(func_node, calls)
        return list(set(calls))
    
    def _find_calls_recursive(self, node, calls: list) -> None:
        """Recursively find function calls."""
        if node.type in ("call", "call_expression"):
            # Get the function being called
            func = node.child_by_field_name("function") or (node.children[0] if node.children else None)
            if func:
                if func.type == "identifier":
                    calls.append(func.text.decode("utf-8"))
                elif func.type in ("member_expression", "attribute"):
                    # obj.method() — extract method name
                    prop = func.child_by_field_name("property") or func.child_by_field_name("attribute")
                    if prop:
                        calls.append(prop.text.decode("utf-8"))
                    else:
                        # Fallback: last identifier child
                        for child in reversed(func.children):
                            if child.type == "identifier" or child.type == "property_identifier":
                                calls.append(child.text.decode("utf-8"))
                                break
                elif func.type == "attribute_expression":
                    attr = func.child_by_field_name("attribute")
                    if attr:
                        calls.append(attr.text.decode("utf-8"))
        
        for child in node.children:
            self._find_calls_recursive(child, calls)
    
    def _extract_imports(self, source: str, node, ext: str) -> list[dict[str, Any]]:
        """Extract import statements."""
        imports = []
        
        if ext in (".js", ".jsx", ".ts", ".tsx"):
            self._find_js_imports(node, imports)
        elif ext == ".py":
            self._find_python_imports(node, imports)
        
        return imports
    
    def _find_js_imports(self, node, imports: list) -> None:
        """Find JavaScript/TypeScript imports."""
        if node.type == "import_statement":
            module_name = None
            imported = []
            
            for child in node.children:
                if child.type == "string":
                    module_name = child.text.decode("utf-8").strip('"\'')
                elif child.type == "import_clause":
                    for c in child.children:
                        if c.type == "identifier":
                            imported.append(c.text.decode("utf-8"))
                        elif c.type == "named_imports":
                            for ic in c.children:
                                if ic.type == "import_specifier":
                                    name = ic.child_by_field_name("name")
                                    if name:
                                        imported.append(name.text.decode("utf-8"))
            
            if module_name:
                imports.append({
                    "module": module_name,
                    "imported": imported,
                    "default": imported[0] if imported else None,
                })
        
        for child in node.children:
            self._find_js_imports(child, imports)
    
    def _find_python_imports(self, node, imports: list) -> None:
        """Find Python imports."""
        if node.type in ("import_statement", "import_from_statement"):
            module_name = None
            imported = []
            
            for child in node.children:
                if child.type == "dotted_name":
                    module_name = child.text.decode("utf-8")
                elif child.type == "aliased_import":
                    for c in child.children:
                        if c.type == "identifier":
                            imported.append(c.text.decode("utf-8"))
                elif child.type == "wildcard_import":
                    imported.append("*")
                elif child.type == "dotted_name" and node.type == "import_from_statement":
                    for c in child.children:
                        if c.type == "identifier":
                            imported.append(c.text.decode("utf-8"))
            
            if module_name:
                imports.append({
                    "module": module_name,
                    "imported": imported,
                })
        
        for child in node.children:
            self._find_python_imports(child, imports)
    
    def _extract_exports(self, source: str, node, ext: str) -> list[dict[str, Any]]:
        """Extract export statements."""
        exports = []
        
        if ext in (".js", ".jsx", ".ts", ".tsx"):
            self._find_js_exports(node, exports)
        elif ext == ".py":
            self._find_python_exports(node, exports)
        
        return exports
    
    def _find_js_exports(self, node, exports: list) -> None:
        """Find JavaScript/TypeScript exports."""
        if node.type == "export_statement":
            for child in node.children:
                if child.type == "named_export":
                    for c in child.children:
                        if c.type == "export_clause":
                            for ec in c.children:
                                if ec.type == "export_specifier":
                                    name = ec.child_by_field_name("name")
                                    if name:
                                        exports.append({"name": name.text.decode("utf-8"), "type": "named"})
                elif child.type == "variable_declaration":
                    for c in child.children:
                        if c.type == "variable_declarator":
                            name_node = c.child_by_field_name("name")
                            if name_node:
                                exports.append({"name": name_node.text.decode("utf-8"), "type": "variable"})
                elif child.type == "class_declaration":
                    name_node = self._get_node_name(child, "")
                    if name_node:
                        exports.append({"name": name_node, "type": "class"})
                elif child.type == "function_declaration":
                    name_node = self._get_node_name(child, "")
                    if name_node:
                        exports.append({"name": name_node, "type": "function"})
        
        for child in node.children:
            self._find_js_exports(child, exports)
    
    def _find_python_exports(self, node, exports: list) -> None:
        """Find Python __all__ exports."""
        if node.type == "assignment_statement":
            for child in node.children:
                if child.type == "attribute" and child.text.decode("utf-8") == "__all__":
                    for c in child.children:
                        if c.type == "list":
                            for lc in c.children:
                                if lc.type == "string":
                                    exports.append({"name": lc.text.decode("utf-8").strip('"\''), "type": "explicit"})
        
        for child in node.children:
            self._find_python_exports(child, exports)
    
    def _extract_api_routes(self, source: str, node, ext: str) -> list[dict[str, Any]]:
        """Extract API routes/endpoints."""
        routes = []
        
        if ext in (".js", ".jsx", ".ts", ".tsx"):
            self._find_js_routes(node, routes)
        
        return routes
    
    def _find_js_routes(self, node, routes: list) -> None:
        """Find JavaScript/TypeScript API routes."""
        source_bytes = node.text if hasattr(node, 'text') else b''
        source_str = source_bytes.decode("utf-8", errors="ignore")
        
        import re
        
        patterns = [
            (r'["\'](GET|POST|PUT|DELETE|PATCH)\s+["\']([^"\']+)["\']', 'express'),
            (r'@Get\(["\']([^"\']+)["\']\)', 'nestjs'),
            (r'@Post\(["\']([^"\']+)["\']\)', 'nestjs'),
            (r'@Put\(["\']([^"\']+)["\']\)', 'nestjs'),
            (r'@Delete\(["\']([^"\']+)["\']\)', 'nestjs'),
            (r'@RequestMapping\(["\']([^"\']+)["\']', 'spring'),
            (r'router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'express'),
            (r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', 'express'),
        ]
        
        for pattern, framework in patterns:
            matches = re.findall(pattern, source_str)
            for match in matches:
                if len(match) == 2:
                    method = match[0] if match[0] in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] else framework
                    path = match[1] if match[0] in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] else match[1]
                    routes.append({"method": method.upper(), "path": path, "framework": framework})
        
        for child in node.children:
            self._find_js_routes(child, routes)
    
    def _extract_entities(self, source: str, node, ext: str) -> list[dict[str, Any]]:
        """Extract database entities/models."""
        entities = []
        
        if ext in (".js", ".jsx", ".ts", ".tsx"):
            self._find_js_entities(node, entities, source)
        elif ext == ".py":
            self._find_python_entities(node, entities, source)
        
        return entities
    
    def _find_js_entities(self, node, entities: list, source: str) -> None:
        """Find JavaScript/TypeScript entities/models."""
        source_bytes = node.text if hasattr(node, 'text') else b''
        source_str = source_bytes.decode("utf-8", errors="ignore")
        
        if node.type == "class_declaration":
            name = self._get_node_name(node, source_str)
            if name:
                entity_type = "unknown"
                if "@Entity" in source_str:
                    entity_type = "typeorm"
                elif "sequelize" in source_str.lower() or "Model" in name:
                    entity_type = "sequelize"
                elif "prisma" in source_str.lower() or "@Model" in source_str:
                    entity_type = "prisma"
                
                fields = []
                for child in node.children:
                    if child.type == "class_body":
                        for cb in child.children:
                            if cb.type == "field_definition":
                                field_name = self._get_node_name(cb, source_str)
                                if field_name:
                                    fields.append(field_name)
                
                entities.append({
                    "name": name,
                    "type": entity_type,
                    "fields": fields,
                })
        
        for child in node.children:
            self._find_js_entities(child, entities, source_str)
    
    def _find_python_entities(self, node, entities: list, source: str) -> None:
        """Find Python entities/models."""
        source_bytes = node.text if hasattr(node, 'text') else b''
        source_str = source_bytes.decode("utf-8", errors="ignore")
        
        if node.type == "class_definition":
            name = self._get_node_name(node, source_str)
            if name:
                entity_type = "unknown"
                if "SQLModel" in source_str or "Base" in source_str:
                    entity_type = "sqlmodel"
                elif "Flask" in source_str or "SQLAlchemy" in source_str:
                    entity_type = "sqlalchemy"
                elif "Django" in source_str:
                    entity_type = "django"
                elif "Pydantic" in source_str:
                    entity_type = "pydantic"
                
                fields = []
                for child in node.children:
                    if child.type == "block":
                        for bc in child.children:
                            if bc.type == "expression_statement":
                                for bcc in bc.children:
                                    if bcc.type == "assignment":
                                        for bcca in bcc.children:
                                            if bcca.type == "identifier":
                                                fields.append(bcca.text.decode("utf-8"))
                
                entities.append({
                    "name": name,
                    "type": entity_type,
                    "fields": fields,
                })
        
        for child in node.children:
            self._find_python_entities(child, entities, source_str)
    
    def _extract_docstring(self, node, source: str) -> str | None:
        """Extract Python docstring from a function/class body."""
        # Look for the first expression_statement in the body that is a string
        for child in node.children:
            if child.type == "block":
                for bc in child.children:
                    if bc.type == "expression_statement":
                        for bcc in bc.children:
                            if bcc.type == "string":
                                doc = bcc.text.decode("utf-8", errors="ignore")
                                # Strip triple quotes
                                doc = doc.strip('"').strip("'").strip()
                                if doc:
                                    # Truncate long docstrings
                                    return doc[:200] + "..." if len(doc) > 200 else doc
                        break  # Only check first statement
                break
        return None
    
    def _extract_jsdoc(self, node, source: str) -> str | None:
        """Extract JSDoc comment preceding a node."""
        # Check for comment node preceding this node
        start_line = node.start_point.row
        source_lines = source.split("\n")
        
        # Walk backwards from the node to find a JSDoc comment
        doc_lines = []
        in_jsdoc = False
        for i in range(start_line - 1, max(start_line - 15, -1), -1):
            if i < 0 or i >= len(source_lines):
                break
            line = source_lines[i].strip()
            
            if line.endswith("*/"):
                in_jsdoc = True
                line = line[:-2].strip()
                if line:
                    doc_lines.insert(0, line.lstrip("* "))
            elif in_jsdoc:
                if line.startswith("/**"):
                    line = line[3:].strip()
                    if line:
                        doc_lines.insert(0, line.lstrip("* "))
                    break
                elif line.startswith("/*"):
                    line = line[2:].strip()
                    if line:
                        doc_lines.insert(0, line.lstrip("* "))
                    break
                elif line.startswith("*"):
                    line = line[1:].strip()
                    if line and not line.startswith("@"):
                        doc_lines.insert(0, line)
                else:
                    break
            elif line.startswith("//"):
                # Single-line comment
                doc_lines.insert(0, line[2:].strip())
            elif line == "":
                if doc_lines:
                    break
                continue
            else:
                break
        
        if doc_lines:
            doc = " ".join(doc_lines).strip()
            return doc[:200] + "..." if len(doc) > 200 else doc
        return None
    
    def _build_index(self, root: Path) -> dict[str, Any]:
        """Build the final index structure."""
        languages = set()
        for file_path in self.file_symbols.keys():
            ext = Path(file_path).suffix.lower()
            lang_info = LANGUAGE_MAP.get(ext)
            if lang_info:
                languages.add(lang_info[0])
            elif ext in REGEX_LANGUAGES:
                languages.add(REGEX_LANGUAGES[ext])
            else:
                languages.add(ext.lstrip("."))
        
        # Build file dependency graph from imports
        file_deps = self._build_file_dependencies()
        
        # Build cross-file type map
        type_map = self._build_type_map()
        
        result = {
            "project_root": str(root),
            "last_indexed": self._timestamp(),
            "files": self.file_symbols,
            "call_graph": self.call_graph,
            "file_dependencies": file_deps,
            "file_hashes": self._compute_hashes(root),
            "languages": list(languages),
        }
        
        if type_map:
            result["type_map"] = type_map
        
        # Run plugin post-processors
        result = plugin_registry.run_post_processors(result)
        
        return result
    
    def _build_type_map(self) -> dict[str, dict[str, Any]]:
        """Build a cross-file type map: symbol name -> definition location + type info.
        
        This resolves imported symbols to their source definitions, so an AI agent
        can look up where a type/function is actually defined even when it's imported.
        """
        # Step 1: Build export registry — what each file exports
        export_registry: dict[str, dict[str, str]] = {}  # symbol_name -> {file, type, line}
        for rel_path, file_data in self.file_symbols.items():
            if not isinstance(file_data, dict):
                continue
            
            # Register all top-level symbols as potential exports
            for sym in file_data.get("symbols", []):
                name = sym.get("name")
                if name and not sym.get("class"):  # Only top-level
                    export_registry[name] = {
                        "defined_in": rel_path,
                        "type": sym.get("type"),
                        "line": sym.get("line"),
                    }
            
            # Register explicit exports
            for exp in file_data.get("exports", []):
                name = exp.get("name")
                if name and name not in export_registry:
                    export_registry[name] = {
                        "defined_in": rel_path,
                        "type": exp.get("type", "export"),
                    }
        
        # Step 2: Resolve imports to definitions
        type_map: dict[str, dict[str, Any]] = {}
        for rel_path, file_data in self.file_symbols.items():
            if not isinstance(file_data, dict):
                continue
            
            for imp in file_data.get("imports", []):
                imported_names = imp.get("imported", [])
                for imported_name in imported_names:
                    if imported_name in export_registry:
                        defn = export_registry[imported_name]
                        if defn["defined_in"] != rel_path:
                            key = f"{rel_path}:{imported_name}"
                            type_map[key] = {
                                "imported_in": rel_path,
                                "name": imported_name,
                                "defined_in": defn["defined_in"],
                                "type": defn.get("type"),
                                "line": defn.get("line"),
                            }
        
        return type_map
    
    def _build_file_dependencies(self) -> dict[str, list[str]]:
        """Build a graph of which files import from which other files."""
        deps = {}
        
        # Map module names to files for resolution
        module_to_file = {}
        for rel_path in self.file_symbols:
            # Register by filename stem and path variants
            stem = Path(rel_path).stem
            module_to_file[stem] = rel_path
            # Also register without extension
            no_ext = str(Path(rel_path).with_suffix(""))
            module_to_file[no_ext] = rel_path
            module_to_file[no_ext.replace("\\", "/")] = rel_path
        
        for rel_path, file_data in self.file_symbols.items():
            if not isinstance(file_data, dict):
                continue
            imports = file_data.get("imports", [])
            if not imports:
                continue
            
            dep_files = []
            for imp in imports:
                module = imp.get("module", "")
                if not module:
                    continue
                
                # Skip external packages (no relative path prefix, no /)
                if module.startswith("."):
                    # Resolve relative import
                    base_dir = str(Path(rel_path).parent)
                    resolved = module.lstrip("./")
                    candidate = f"{base_dir}/{resolved}" if base_dir != "." else resolved
                    
                    # Try to find matching file
                    for ext in (".ts", ".tsx", ".js", ".jsx", ".py"):
                        key = candidate + ext
                        if key.replace("\\", "/") in {k.replace("\\", "/") for k in self.file_symbols}:
                            dep_files.append(key.replace("\\", "/"))
                            break
                    else:
                        # Try index file
                        for ext in (".ts", ".tsx", ".js", ".jsx"):
                            key = f"{candidate}/index{ext}"
                            if key.replace("\\", "/") in {k.replace("\\", "/") for k in self.file_symbols}:
                                dep_files.append(key.replace("\\", "/"))
                                break
                else:
                    # Absolute import — try to match against known files
                    clean = module.replace("@/", "src/").replace("~/", "")
                    if clean in module_to_file:
                        dep_files.append(module_to_file[clean])
            
            if dep_files:
                deps[rel_path] = list(set(dep_files))
        
        return deps
    
    def _timestamp(self) -> str:
        """Get current ISO timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def _compute_hashes(self, root: Path) -> dict[str, str]:
        """Compute SHA-256 hashes for all indexed files."""
        hashes = {}
        for rel_path in self.file_symbols:
            file_path = root / rel_path
            try:
                content = file_path.read_bytes()
                hashes[rel_path] = hashlib.sha256(content).hexdigest()
            except OSError:
                pass
        return hashes


def index_directory(path: str | Path, incremental: bool = False) -> dict[str, Any]:
    """Convenience function to index a directory."""
    indexer = CodeIndexer()
    return indexer.index_directory(Path(path), incremental=incremental)


def save_index(index: dict[str, Any], output_path: Path) -> None:
    """Save index to JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def load_index(index_path: Path) -> dict[str, Any]:
    """Load index from JSON file."""
    return json.loads(index_path.read_text(encoding="utf-8"))
