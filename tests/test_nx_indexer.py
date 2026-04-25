"""End-to-end test for Nx monorepo indexing."""
import json
import tempfile
from pathlib import Path

from cortexcode.indexer import index_directory


def test_index_nx_workspace():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "nx.json").write_text(json.dumps({"nxVersion": "16.0.0"}))

        app_dir = root / "apps" / "store" / "src" / "app"
        app_dir.mkdir(parents=True)
        (app_dir / "main.tsx").write_text(
            "import { Button } from '@nx-example/shared/ui';\nexport function App() { return <Button />; }\n"
        )
        (root / "apps" / "store" / "project.json").write_text(json.dumps({
            "name": "store",
            "projectType": "application",
            "sourceRoot": "apps/store/src",
        }))

        lib_dir = root / "libs" / "shared" / "ui" / "src" / "lib"
        lib_dir.mkdir(parents=True)
        (lib_dir / "button.tsx").write_text(
            "export function Button() { return <button>Click</button>; }\n"
        )
        (root / "libs" / "shared" / "ui" / "src" / "index.ts").write_text(
            "export { Button } from './lib/button';\n"
        )
        (root / "libs" / "shared" / "ui" / "project.json").write_text(json.dumps({
            "name": "shared-ui",
            "projectType": "library",
            "sourceRoot": "libs/shared/ui/src",
            "tags": ["ui"],
            "implicitDependencies": [],
        }))

        (root / "tsconfig.base.json").write_text(json.dumps({
            "compilerOptions": {
                "paths": {
                    "@nx-example/shared/ui": ["libs/shared/ui/src/index.ts"],
                }
            }
        }))

        index = index_directory(root, incremental=False, filter_opts={"include_tests": True})

        assert "files" in index
        assert "project_profile" in index
        assert "nx_workspace" in index

        ws = index["nx_workspace"]
        assert ws is not None
        assert "store" in ws["projects"]
        assert "shared-ui" in ws["projects"]

        file_deps = index.get("file_dependencies", {})
        app_main = "apps/store/src/app/main.tsx"
        assert app_main in file_deps
        # Should resolve the @nx-example/shared/ui alias to the lib
        assert len(file_deps[app_main]) > 0

        type_map = index.get("type_map", {})
        assert f"{app_main}:Button" in type_map

        profile = index["project_profile"]
        assert "shared-ui" in profile.get("nx_projects", [])


if __name__ == "__main__":
    test_index_nx_workspace()
    print("Nx indexer e2e test passed!")
