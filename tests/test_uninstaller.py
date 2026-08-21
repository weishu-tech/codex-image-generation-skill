from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "ccws-image-generation-installer"
MACOS_UNINSTALLER = PACKAGE_ROOT / "uninstall-macos.command"
WINDOWS_UNINSTALLER = PACKAGE_ROOT / "uninstall-windows.ps1"
WINDOWS_BATCH = PACKAGE_ROOT / "uninstall-windows.bat"
MACOS_INSTALLER = PACKAGE_ROOT / "install-macos.command"
WINDOWS_INSTALLER = PACKAGE_ROOT / "install-windows.ps1"
RUNTIME_MARKER = ".ccws-managed-python-runtime"
PYTHON_VERSION = "3.12.10"


def _write_skill(path: Path, version: str = "1.2.0") -> None:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        "---\nname: ccws-image-generation\ndescription: test fixture\n---\n",
        encoding="utf-8",
    )
    (path / "VERSION").write_text(f"{version}\n", encoding="utf-8")


def _powershell() -> str | None:
    configured = os.environ.get("CCWS_TEST_PWSH", "").strip()
    if configured and Path(configured).is_file():
        return configured
    return shutil.which("pwsh")


class UninstallerTests(unittest.TestCase):
    def test_package_contains_double_click_uninstallers_and_runtime_markers(self) -> None:
        self.assertTrue(MACOS_UNINSTALLER.is_file())
        self.assertTrue(os.access(MACOS_UNINSTALLER, os.X_OK))
        self.assertTrue(WINDOWS_BATCH.is_file())
        self.assertTrue(WINDOWS_UNINSTALLER.is_file())
        self.assertIn("uninstall-windows.ps1", WINDOWS_BATCH.read_text(encoding="utf-8"))

        marker_literal = ".ccws-managed-python-runtime"
        self.assertIn(marker_literal, MACOS_INSTALLER.read_text(encoding="utf-8"))
        self.assertIn(marker_literal, WINDOWS_INSTALLER.read_text(encoding="utf-8-sig"))
        self.assertIn(marker_literal, MACOS_UNINSTALLER.read_text(encoding="utf-8"))
        self.assertIn(marker_literal, WINDOWS_UNINSTALLER.read_text(encoding="utf-8-sig"))

    @unittest.skipUnless(sys.platform == "darwin", "macOS uninstaller test")
    def test_macos_uninstall_removes_active_install_and_preserves_backups(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            modern_skill = root / ".agents" / "skills" / "ccws-image-generation"
            legacy_skill = root / ".codex" / "skills" / "ccws-image-generation"
            codex_home = root / "custom-codex"
            codex_skill = codex_home / "skills" / "ccws-image-generation"
            other_skill = root / ".agents" / "skills" / "other-skill"
            modern_backup = root / ".agents" / "skill-backups" / "ccws-image-generation.backup-test"
            legacy_backup = root / ".codex" / "skill-backups" / "ccws-image-generation.backup-test"
            config_file = root / "Library" / "Application Support" / "CCWS" / "image-generation.json"
            runtime_root = root / "Library" / "Application Support" / "CCWS" / "Python" / PYTHON_VERSION
            unrelated_file = root / "Library" / "Application Support" / "CCWS" / "keep-me.txt"
            api_key = "uninstall-test-secret"

            for skill in (modern_skill, legacy_skill, codex_skill):
                _write_skill(skill)
            _write_skill(other_skill)
            _write_skill(modern_backup, version="1.0.0")
            _write_skill(legacy_backup, version="1.0.0")
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(
                json.dumps({"api_url": "https://api.example.com/v1", "api_key": api_key, "model": "gpt-image-2"}),
                encoding="utf-8",
            )
            runtime_root.mkdir(parents=True)
            (runtime_root / "python-fixture").write_text("managed runtime\n", encoding="utf-8")
            unrelated_file.write_text("preserve\n", encoding="utf-8")

            env = os.environ.copy()
            env["HOME"] = str(root)
            env["USERPROFILE"] = str(root)
            env["CODEX_HOME"] = str(codex_home)
            env.pop("CCWS_IMAGE_CONFIG", None)
            env.pop("CCWS_PYTHON_RUNTIME_ROOT", None)

            result = subprocess.run(
                [str(MACOS_UNINSTALLER), "--yes"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            combined_output = result.stdout + result.stderr
            self.assertNotIn(api_key, combined_output)
            self.assertIn("卸载完成", combined_output)
            for removed in (modern_skill, legacy_skill, codex_skill, config_file, runtime_root):
                self.assertFalse(removed.exists(), removed)
            for preserved in (other_skill, modern_backup, legacy_backup, unrelated_file):
                self.assertTrue(preserved.exists(), preserved)

    @unittest.skipUnless(sys.platform == "darwin", "macOS uninstaller test")
    def test_macos_uninstall_defaults_to_cancel(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            skill = root / ".agents" / "skills" / "ccws-image-generation"
            _write_skill(skill)
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["USERPROFILE"] = str(root)
            env.pop("CODEX_HOME", None)
            env.pop("CCWS_IMAGE_CONFIG", None)
            env.pop("CCWS_PYTHON_RUNTIME_ROOT", None)

            result = subprocess.run(
                [str(MACOS_UNINSTALLER)],
                input="\n",
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertIn("已取消卸载", result.stdout + result.stderr)
            self.assertTrue(skill.exists())

    @unittest.skipUnless(sys.platform == "darwin", "macOS uninstaller test")
    def test_macos_custom_targets_require_ccws_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            custom_config = root / "custom" / "settings.json"
            custom_runtime = root / "custom" / "python"
            custom_config.parent.mkdir(parents=True)
            custom_config.write_text(json.dumps({"model": "gpt-image-2", "api_key": "secret"}), encoding="utf-8")
            custom_runtime.mkdir(parents=True)
            (custom_runtime / RUNTIME_MARKER).write_text(
                f"ccws-image-generation:{PYTHON_VERSION}\n",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["HOME"] = str(root)
            env["USERPROFILE"] = str(root)
            env["CCWS_IMAGE_CONFIG"] = str(custom_config)
            env["CCWS_PYTHON_RUNTIME_ROOT"] = str(custom_runtime)
            env.pop("CODEX_HOME", None)

            subprocess.run(
                [str(MACOS_UNINSTALLER), "--yes"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertFalse(custom_config.exists())
            self.assertFalse(custom_runtime.exists())

            unsafe_runtime = root / "custom" / "unmarked-python"
            unsafe_runtime.mkdir(parents=True)
            env["CCWS_IMAGE_CONFIG"] = str(root / "missing-config.json")
            env["CCWS_PYTHON_RUNTIME_ROOT"] = str(unsafe_runtime)
            refused = subprocess.run(
                [str(MACOS_UNINSTALLER), "--yes"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("安全标记", refused.stdout + refused.stderr)
            self.assertTrue(unsafe_runtime.exists())

    @unittest.skipUnless(_powershell(), "PowerShell 7 is not available")
    def test_windows_uninstaller_parses(self) -> None:
        powershell = _powershell()
        assert powershell is not None
        escaped_path = str(WINDOWS_UNINSTALLER).replace("'", "''")
        command = (
            "$tokens=$null; $errors=$null; "
            f"[System.Management.Automation.Language.Parser]::ParseFile('{escaped_path}', [ref]$tokens, [ref]$errors) | Out-Null; "
            "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"
        )
        subprocess.run(
            [powershell, "-NoLogo", "-NoProfile", "-Command", command],
            check=True,
            capture_output=True,
            text=True,
        )

    @unittest.skipUnless(_powershell(), "PowerShell 7 is not available")
    def test_windows_uninstall_removes_active_install_and_preserves_backups(self) -> None:
        powershell = _powershell()
        assert powershell is not None
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            app_data = root / "AppData" / "Roaming"
            local_app_data = root / "AppData" / "Local"
            codex_home = root / "custom-codex"
            modern_skill = root / ".agents" / "skills" / "ccws-image-generation"
            legacy_skill = root / ".codex" / "skills" / "ccws-image-generation"
            codex_skill = codex_home / "skills" / "ccws-image-generation"
            backup = root / ".agents" / "skill-backups" / "ccws-image-generation.backup-test"
            other_skill = root / ".agents" / "skills" / "other-skill"
            config_file = app_data / "CCWS" / "image-generation.json"
            runtime_root = local_app_data / "CCWS" / "Python" / PYTHON_VERSION
            unrelated_file = app_data / "CCWS" / "keep-me.txt"
            api_key = "windows-uninstall-test-secret"

            for skill in (modern_skill, legacy_skill, codex_skill, other_skill):
                _write_skill(skill)
            _write_skill(backup, version="1.0.0")
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(
                json.dumps({"api_url": "https://api.example.com/v1", "api_key": api_key, "model": "gpt-image-2"}),
                encoding="utf-8",
            )
            runtime_root.mkdir(parents=True)
            (runtime_root / "python.exe").write_text("fixture\n", encoding="utf-8")
            unrelated_file.write_text("preserve\n", encoding="utf-8")

            env = os.environ.copy()
            env["USERPROFILE"] = str(root)
            env["APPDATA"] = str(app_data)
            env["LOCALAPPDATA"] = str(local_app_data)
            env["CODEX_HOME"] = str(codex_home)
            env.pop("CCWS_IMAGE_CONFIG", None)
            env.pop("CCWS_PYTHON_RUNTIME_ROOT", None)

            result = subprocess.run(
                [powershell, "-NoLogo", "-NoProfile", "-File", str(WINDOWS_UNINSTALLER), "--yes"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            combined_output = result.stdout + result.stderr
            self.assertNotIn(api_key, combined_output)
            self.assertIn("卸载完成", combined_output)
            for removed in (modern_skill, legacy_skill, codex_skill, config_file, runtime_root):
                self.assertFalse(removed.exists(), removed)
            for preserved in (backup, other_skill, unrelated_file):
                self.assertTrue(preserved.exists(), preserved)


if __name__ == "__main__":
    unittest.main()
