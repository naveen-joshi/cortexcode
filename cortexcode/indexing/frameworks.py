from typing import Any


def detect_framework(name: str, node: Any, source: str) -> str | None:
    source_bytes = node.text if hasattr(node, "text") else b""
    source_str = source_bytes.decode("utf-8", errors="ignore")

    if any(rn in source_str for rn in ("useNavigation", "useRoute", "useAnimatedStyle", "useSharedValue")):
        return "react-native-hook"
    if any(rn in source_str for rn in ("StyleSheet.create", "Dimensions.get", "PixelRatio")):
        return "react-native-util"

    rn_components = ("View", "Text", "TouchableOpacity", "FlatList", "ScrollView", "SafeAreaView", "StatusBar", "Alert", "Modal")
    if name and name[0].isupper() and any(f"<{component}" in source_str or f"{component}>" in source_str for component in rn_components):
        return "react-native-component"

    if any(expo in source_str for expo in ("expo-", "usePermissions", "useCameraPermissions", "useAssets", "Notifications.schedule")):
        return "expo"
    if "expo-router" in source_str or "useLocalSearchParams" in source_str or "useGlobalSearchParams" in source_str:
        return "expo-router"

    if "useState" in source_str or "useEffect" in source_str or "useContext" in source_str or "useReducer" in source_str or "useMemo" in source_str:
        if name and name[0].isupper():
            return "react-component"
        if name and name.startswith("use"):
            return "react-hook"
        return "react-hook"

    if name in ("generateMetadata", "generateStaticParams"):
        return "nextjs-app-router"
    if "'use server'" in source_str or '"use server"' in source_str:
        return "nextjs-server-action"
    if "'use client'" in source_str or '"use client"' in source_str:
        return "nextjs-client"

    if "getServerSideProps" in name or "getStaticProps" in name or "getStaticPaths" in name:
        return "nextjs-ssg"
    if "getServerSideProps" in source_str or "getStaticProps" in source_str:
        return "nextjs-page"

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

    if "app.get(" in source_str or "app.post(" in source_str or "router.get(" in source_str or "router.post(" in source_str:
        return "express-route"
    if "app.use(" in source_str and "router" not in name:
        return "express-middleware"

    if "@app.get(" in source_str or "@app.post(" in source_str or "@router.get(" in source_str or "@router.post(" in source_str:
        return "fastapi-endpoint"
    if "Depends(" in source_str and ("async def" in source_str or "def " in source_str):
        return "fastapi-dependency"

    if "request.method" in source_str or "HttpResponse" in source_str or "JsonResponse" in source_str:
        return "django-view"
    if "@api_view" in source_str or "APIView" in source_str:
        return "django-rest"

    if "@app.route(" in source_str or "@blueprint.route(" in source_str:
        return "flask-route"

    if name in ("loader", "action") and ("json(" in source_str or "redirect(" in source_str):
        return "remix-loader"

    if name and name[0].isupper() and ("return" in source_str or "=>" in source_str):
        if "<" in source_str:
            return "react-component"

    return None


def detect_class_framework(name: str, node: Any, source: str) -> str | None:
    source_bytes = node.text if hasattr(node, "text") else b""
    source_str = source_bytes.decode("utf-8", errors="ignore")

    if "@Component" in source_str:
        return "angular-component"
    if "@Injectable" in source_str:
        return "angular-service"
    if "@NgModule" in source_str:
        return "angular-module"
    if "@Directive" in source_str:
        return "angular-directive"
    if "@Pipe" in source_str and "PipeTransform" in source_str:
        return "angular-pipe"

    if "extends Component" in source_str or "extends PureComponent" in source_str:
        rn_indicators = ("View", "Text", "TouchableOpacity", "FlatList", "StyleSheet")
        if any(ind in source_str for ind in rn_indicators):
            return "react-native-component"
        return "react-class-component"

    if "@Controller" in source_str:
        return "nestjs-controller"
    if "@Injectable" in source_str and "nestjs" not in source_str.lower():
        return "nestjs-service"
    if "@Module" in source_str and "imports:" in source_str:
        return "nestjs-module"

    if "@Controller" in source_str or "@RestController" in source_str:
        return "spring-boot"

    return None


def detect_java_framework(name: str, node: Any, source: str) -> str | None:
    source_bytes = node.text if hasattr(node, "text") else b""
    source_str = source_bytes.decode("utf-8", errors="ignore")

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

    if "@Entity" in source_str or "@Table" in source_str:
        return "spring-entity"
    if "@Repository" in source_str:
        return "spring-repository"
    if "@Service" in source_str:
        return "spring-service"
    if "@Controller" in source_str or "@RestController" in source_str:
        return "spring-controller"
    if "@Component" in source_str:
        return "spring-component"
    if "@Configuration" in source_str:
        return "spring-config"

    return None


def detect_csharp_framework(name: str, node: Any, source: str) -> str | None:
    source_bytes = node.text if hasattr(node, "text") else b""
    source_str = source_bytes.decode("utf-8", errors="ignore")

    if "[ApiController]" in source_str or "ControllerBase" in source_str:
        return "aspnet-controller"
    if "[Route(" in source_str or "[HttpGet]" in source_str or "[HttpPost]" in source_str:
        return "aspnet-webapi"
    if "[DataContract]" in source_str or "[DataMember]" in source_str:
        return "wcf-service"
    if "DbContext" in source_str or "DbSet<" in source_str:
        return "ef-entity"

    return None


def detect_kotlin_framework(name: str, node: Any, source: str) -> str | None:
    src = node.text.decode("utf-8", errors="ignore") if hasattr(node, "text") else ""

    if "@Composable" in src:
        return "compose-ui"
    if "@Preview" in src:
        return "compose-preview"
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
    if "routing {" in src or "get(" in src and "call.respond" in src:
        return "ktor-route"
    if "@Entity" in src or "@Dao" in src:
        return "android-room"
    if "@Database" in src:
        return "android-room-db"
    if "@HiltViewModel" in src or "@HiltAndroidApp" in src:
        return "android-hilt"
    if "@Inject" in src or "@Module" in src:
        return "android-di"

    return None


def detect_swift_framework(name: str, node: Any, source: str) -> str | None:
    src = node.text.decode("utf-8", errors="ignore") if hasattr(node, "text") else ""

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
    if ": UIViewController" in src:
        return "uikit-viewcontroller"
    if ": UITableViewDelegate" in src or ": UITableViewDataSource" in src:
        return "uikit-tableview"
    if ": UICollectionViewDelegate" in src:
        return "uikit-collectionview"
    if ": UIView" in src and ": UIViewController" not in src:
        return "uikit-view"
    if "AnyPublisher" in src or "@Published" in src or "sink(" in src:
        return "combine"
    if ": NSManagedObject" in src or "@NSManaged" in src:
        return "coredata-entity"
    if "NSPersistentContainer" in src:
        return "coredata"
    if "req.content" in src or "app.get(" in src or "app.post(" in src:
        return "vapor-route"

    return None
