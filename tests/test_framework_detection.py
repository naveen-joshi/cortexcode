"""Tests for cortexcode.indexing.frameworks — framework detection logic."""
from unittest.mock import MagicMock

import pytest

from cortexcode.indexing.frameworks import (
    detect_class_framework,
    detect_csharp_framework,
    detect_framework,
    detect_java_framework,
)


def _node(text: str):
    """Return a minimal AST-node-like mock with a text attribute."""
    node = MagicMock()
    node.text = text.encode("utf-8")
    return node


# ── detect_framework (JS/TS) ──────────────────────────────────────────────────

def test_detect_react_hook():
    node = _node("function useCounter() { const [n, setN] = useState(0); }")
    result = detect_framework("useCounter", node, "")
    assert result == "react-hook"


def test_detect_react_component():
    node = _node("function Button() { return <button>Click</button>; }")
    result = detect_framework("Button", node, "")
    assert result == "react-component"


def test_detect_nextjs_app_router():
    node = _node("export async function generateMetadata() {}")
    result = detect_framework("generateMetadata", node, "")
    assert result == "nextjs-app-router"


def test_detect_nextjs_server_action():
    node = _node("'use server'\nexport async function submitForm() {}")
    result = detect_framework("submitForm", node, "")
    assert result == "nextjs-server-action"


def test_detect_nextjs_client():
    node = _node("'use client'\nexport function MyComponent() {}")
    result = detect_framework("MyComponent", node, "")
    assert result == "nextjs-client"


def test_detect_nextjs_ssg():
    node = _node("export async function getStaticProps() {}")
    result = detect_framework("getStaticProps", node, "")
    assert result == "nextjs-ssg"


def test_detect_nestjs_controller():
    node = _node("@Controller('users')\n@Get('/:id')\ngetUser() {}")
    result = detect_framework("getUser", node, "")
    assert result == "nestjs-controller"


def test_detect_nestjs_service():
    node = _node("@Injectable()\nclass UserService {}")
    result = detect_framework("UserService", node, "")
    assert result == "nestjs-service"


def test_detect_express_route():
    node = _node("app.get('/users', handler)")
    result = detect_framework("handler", node, "")
    assert result == "express-route"


def test_detect_fastapi_endpoint():
    node = _node("@app.get('/items')\nasync def get_items():")
    result = detect_framework("get_items", node, "")
    assert result == "fastapi-endpoint"


def test_detect_react_native_component():
    node = _node("function Screen() { return <View><Text>hi</Text></View>; }")
    result = detect_framework("Screen", node, "")
    assert result == "react-native-component"


def test_detect_expo():
    node = _node("import { useCameraPermissions } from 'expo-camera';")
    result = detect_framework("takePhoto", node, "")
    assert result == "expo"


def test_detect_no_framework():
    node = _node("function add(a, b) { return a + b; }")
    result = detect_framework("add", node, "")
    assert result is None


# ── detect_class_framework ────────────────────────────────────────────────────

def test_detect_angular_component():
    node = _node("@Component({ selector: 'app-root' })\nclass AppComponent {}")
    result = detect_class_framework("AppComponent", node, "")
    assert result == "angular-component"


def test_detect_angular_service():
    node = _node("@Injectable()\nclass DataService {}")
    result = detect_class_framework("DataService", node, "")
    assert result == "angular-service"


def test_detect_no_class_framework():
    node = _node("class MyClass {}")
    result = detect_class_framework("MyClass", node, "")
    assert result is None


# ── detect_java_framework ────────────────────────────────────────────────────

def test_detect_spring_controller():
    source = "@RestController\n@RequestMapping('/api')\npublic class ApiController {}"
    result = detect_java_framework("ApiController", _node(source), source)
    assert result == "spring-controller"


def test_detect_spring_service():
    source = "@Service\npublic class UserService {}"
    result = detect_java_framework("UserService", _node(source), source)
    assert result == "spring-service"


def test_detect_spring_repository():
    source = "@Repository\npublic interface UserRepo {}"
    result = detect_java_framework("UserRepo", _node(source), source)
    assert result == "spring-repository"


def test_detect_java_no_framework():
    source = "public class Util {}"
    result = detect_java_framework("Util", _node(source), source)
    assert result is None


# ── detect_csharp_framework ───────────────────────────────────────────────────

def test_detect_aspnet_controller():
    source = "[ApiController]\npublic class UsersController : ControllerBase {}"
    result = detect_csharp_framework("UsersController", _node(source), source)
    assert result in ("aspnet-controller", "aspnet-api-controller")


def test_detect_csharp_no_framework():
    source = "public class Helper {}"
    result = detect_csharp_framework("Helper", _node(source), source)
    assert result is None
