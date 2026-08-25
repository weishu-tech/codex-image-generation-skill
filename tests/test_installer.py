from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "image-generation-installer"
INSTALLER = PACKAGE_ROOT / "install.py"
PYTHON_RUNTIME_MANIFEST = PACKAGE_ROOT / "python-runtime.json"
MACOS_INSTALLER = PACKAGE_ROOT / "install-macos.command"


def _load_installer_module():
    spec = importlib.util.spec_from_file_location("image_installer", INSTALLER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load installer module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallerTests(unittest.TestCase):
    def test_api_url_normalization(self) -> None:
        installer = _load_installer_module()
        self.assertEqual(
            installer._normalize_api_url("api.example.com"),
            "https://api.example.com/v1",
        )
        self.assertEqual(
            installer._normalize_api_url("https://api.example.com/openai"),
            "https://api.example.com/openai/v1",
        )
        self.assertEqual(
            installer._normalize_api_url("api.example.com/v1/"),
            "https://api.example.com/v1",
        )
        self.assertEqual(
            installer._normalize_api_url("https://api.example.com/V1/"),
            "https://api.example.com/v1",
        )
        self.assertEqual(
            installer._normalize_api_url("https://api.example.com/v1/images/generations"),
            "https://api.example.com/v1",
        )
        with self.assertRaises(ValueError):
            installer._normalize_api_url("ftp://api.example.com/v1")

    def test_api_prompt_has_no_default_and_rejects_empty_first_install(self) -> None:
        installer = _load_installer_module()
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=["", "api.example.com"]) as mocked_input:
            with contextlib.redirect_stdout(output):
                api_url = installer._prompt_api_url("")

        self.assertEqual(api_url, "https://api.example.com/v1")
        self.assertEqual(mocked_input.call_args_list[0].args[0], "API 地址: ")
        self.assertIn("API 地址不能为空", output.getvalue())

    def test_non_interactive_install_requires_api_address(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "--yes",
                    "--non-interactive",
                    "--skills-dir",
                    str(root / "skills"),
                    "--config-file",
                    str(root / "config.json"),
                    "--api-key",
                    "missing-address-test-key",
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing API address", result.stdout + result.stderr)
            self.assertFalse((root / "skills").exists())

    def test_non_interactive_install_and_cli_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            skills_dir = root / "skills"
            config_file = root / "config" / "image-generation.json"
            api_key = "test-secret-value"

            result = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "--yes",
                    "--non-interactive",
                    "--skills-dir",
                    str(skills_dir),
                    "--config-file",
                    str(config_file),
                    "--api-url",
                    "https://api.example.com",
                    "--api-key",
                    api_key,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            combined_output = result.stdout + result.stderr
            self.assertNotIn(api_key, combined_output)

            installed_skill = skills_dir / "custom-image-generation"
            self.assertTrue((installed_skill / "SKILL.md").is_file())
            self.assertEqual((installed_skill / "VERSION").read_text(encoding="utf-8").strip(), "2.0.0")

            config = json.loads(config_file.read_text(encoding="utf-8"))
            self.assertEqual(config["api_url"], "https://api.example.com/v1")
            self.assertEqual(config["api_key"], api_key)
            self.assertEqual(config["model"], "gpt-image-2")
            self.assertEqual(Path(config["python_executable"]), Path(sys.executable).resolve())
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(config_file.stat().st_mode), 0o600)

            cli = installed_skill / "scripts" / "image_generation.py"
            dry_run = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "generate",
                    "--config-file",
                    str(config_file),
                    "--prompt",
                    "test prompt",
                    "--dry-run",
                    "--out",
                    str(root / "output.png"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertNotIn(api_key, dry_run.stdout + dry_run.stderr)
            payload = json.loads(dry_run.stdout)
            self.assertEqual(payload["url"], "https://api.example.com/v1/images/generations")
            self.assertEqual(payload["payload"]["model"], "gpt-image-2")

    def test_fresh_install_uses_current_user_skill_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            config_file = root / "image-generation.json"
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["USERPROFILE"] = str(root)
            env.pop("CODEX_HOME", None)
            env.pop("IMAGE_GENERATION_CONFIG", None)

            subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "--yes",
                    "--non-interactive",
                    "--config-file",
                    str(config_file),
                    "--api-url",
                    "https://api.example.com/v1",
                    "--api-key",
                    "fresh-install-test-key",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertTrue((root / ".agents" / "skills" / "custom-image-generation" / "SKILL.md").is_file())
            self.assertFalse((root / ".codex" / "skills" / "custom-image-generation").exists())

    def test_existing_legacy_install_is_upgraded_and_backed_up_outside_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            legacy_skill = root / ".codex" / "skills" / "ccws-image-generation"
            legacy_skill.mkdir(parents=True)
            (legacy_skill / "SKILL.md").write_text(
                "---\nname: ccws-image-generation\ndescription: old\n---\n",
                encoding="utf-8",
            )
            (legacy_skill / "VERSION").write_text("0.0.1\n", encoding="utf-8")
            config_file = root / "image-generation.json"
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["USERPROFILE"] = str(root)
            env.pop("CODEX_HOME", None)
            env.pop("IMAGE_GENERATION_CONFIG", None)

            subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "--yes",
                    "--non-interactive",
                    "--config-file",
                    str(config_file),
                    "--api-url",
                    "https://api.example.com/v1",
                    "--api-key",
                    "legacy-upgrade-test-key",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            installed_skill = root / ".codex" / "skills" / "custom-image-generation"
            self.assertEqual((installed_skill / "VERSION").read_text(encoding="utf-8").strip(), "2.0.0")
            self.assertFalse(legacy_skill.exists())
            backups = list((root / ".codex" / "skill-backups").glob("custom-image-generation-legacy.backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "VERSION").read_text(encoding="utf-8").strip(), "0.0.1")
            self.assertFalse(any((root / ".codex" / "skills").glob("*.backup-*")))

    @unittest.skipUnless(sys.platform == "darwin", "macOS legacy config migration test")
    def test_legacy_config_values_are_migrated_without_printing_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            legacy_config = root / "Library" / "Application Support" / "CCWS" / "image-generation.json"
            new_config = root / "Library" / "Application Support" / "Codex Image Generation" / "image-generation.json"
            api_key = "legacy-config-secret"
            legacy_config.parent.mkdir(parents=True)
            legacy_config.write_text(
                json.dumps({"api_url": "https://legacy.example.com", "api_key": api_key, "model": "gpt-image-2"}),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["USERPROFILE"] = str(root)
            env.pop("CODEX_HOME", None)
            env.pop("IMAGE_GENERATION_CONFIG", None)

            result = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "--yes",
                    "--non-interactive",
                    "--python-executable",
                    sys.executable,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertNotIn(api_key, result.stdout + result.stderr)
            migrated = json.loads(new_config.read_text(encoding="utf-8"))
            self.assertEqual(migrated["api_url"], "https://legacy.example.com/v1")
            self.assertEqual(migrated["api_key"], api_key)

    def test_environment_overrides_saved_api_url_and_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            config_file = root / "image-generation.json"
            config_file.write_text(
                json.dumps(
                    {
                        "api_url": "https://saved.example.com/v1",
                        "api_key": "saved-secret-value",
                        "model": "gpt-image-2",
                    }
                ),
                encoding="utf-8",
            )
            cli = PACKAGE_ROOT / "skill" / "custom-image-generation" / "scripts" / "image_generation.py"
            env = os.environ.copy()
            env["IMAGE_GENERATION_API_URL"] = "https://override.example.com/openai"
            env["IMAGE_GENERATION_API_KEY"] = "override-secret-value"

            result = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "generate",
                    "--config-file",
                    str(config_file),
                    "--prompt",
                    "test prompt",
                    "--dry-run",
                    "--out",
                    str(root / "output.png"),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["url"], "https://override.example.com/openai/v1/images/generations")
            self.assertNotIn("saved-secret-value", result.stdout + result.stderr)
            self.assertNotIn("override-secret-value", result.stdout + result.stderr)

    def test_cli_has_no_builtin_api_address_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            config_file = root / "image-generation.json"
            api_key = "missing-cli-address-secret"
            config_file.write_text(
                json.dumps({"api_key": api_key, "model": "gpt-image-2"}),
                encoding="utf-8",
            )
            cli = PACKAGE_ROOT / "skill" / "custom-image-generation" / "scripts" / "image_generation.py"

            result = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "generate",
                    "--config-file",
                    str(config_file),
                    "--prompt",
                    "test prompt",
                    "--dry-run",
                    "--out",
                    str(root / "output.png"),
                ],
                capture_output=True,
                text=True,
            )

            combined_output = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing API address", combined_output)
            self.assertNotIn(api_key, combined_output)

    def test_python_runtime_manifest_pins_mirrors_and_hashes(self) -> None:
        manifest = json.loads(PYTHON_RUNTIME_MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(manifest["version"], "3.12.10")
        self.assertEqual(
            manifest["download_url_templates"],
            [
                "https://mirrors.tuna.tsinghua.edu.cn/python/{version}/{filename}",
                "https://repo.huaweicloud.com/python/{version}/{filename}",
                "https://registry.npmmirror.com/-/binary/python/{version}/{filename}",
                "https://www.python.org/ftp/python/{version}/{filename}",
            ],
        )
        self.assertEqual(
            manifest["macos"]["sha256"],
            "8373e58da4ea146b3eb1c1f9834f19a319440b6b679b06050b1f9ee3237aa8e4",
        )
        self.assertEqual(
            manifest["windows"]["amd64"]["sha256"],
            "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3",
        )
        self.assertEqual(
            manifest["windows"]["arm64"]["sha256"],
            "3065efc3d382d1cda66757ac71ade11904fa6e350f5a97eb74811acd71ba5532",
        )

    @unittest.skipUnless(sys.platform == "darwin", "macOS launcher test")
    def test_installed_macos_launcher_uses_saved_python_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            skills_dir = root / "skills"
            config_file = root / "config" / "image-generation.json"
            api_key = "launcher-test-secret"

            subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "--yes",
                    "--non-interactive",
                    "--skills-dir",
                    str(skills_dir),
                    "--config-file",
                    str(config_file),
                    "--api-url",
                    "https://api.example.com/v1",
                    "--api-key",
                    api_key,
                    "--python-executable",
                    sys.executable,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            launcher = skills_dir / "custom-image-generation" / "scripts" / "run-image-generation.command"
            self.assertTrue(os.access(launcher, os.X_OK))
            env = os.environ.copy()
            env["IMAGE_GENERATION_CONFIG"] = str(config_file)
            result = subprocess.run(
                [
                    str(launcher),
                    "generate",
                    "--prompt",
                    "test prompt",
                    "--dry-run",
                    "--out",
                    str(root / "output.png"),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertNotIn(api_key, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["payload"]["model"], "gpt-image-2")

    @unittest.skipUnless(sys.platform == "darwin", "macOS bootstrap test")
    def test_macos_bootstrap_rejects_bad_python_archive_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            bad_archive = root / "bad-python.pkg"
            bad_archive.write_bytes(b"not a Python package")
            env = os.environ.copy()
            env["IMAGE_GENERATION_PYTHON_DOWNLOAD_URL"] = str(bad_archive)
            env["IMAGE_GENERATION_PYTHON_RUNTIME_ROOT"] = str(root / "runtime")

            result = subprocess.run(
                [
                    str(MACOS_INSTALLER),
                    "--non-interactive",
                    "--skills-dir",
                    str(root / "skills"),
                    "--config-file",
                    str(root / "config.json"),
                    "--api-url",
                    "https://api.example.com/v1",
                    "--api-key",
                    "hash-rejection-test-key",
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA256", result.stdout + result.stderr)
            self.assertFalse((root / "runtime").exists())

    @unittest.skipUnless(
        sys.platform == "darwin" and bool(os.environ.get("IMAGE_GENERATION_TEST_MACOS_PYTHON_PKG")),
        "set IMAGE_GENERATION_TEST_MACOS_PYTHON_PKG to run the full macOS Python bootstrap",
    )
    def test_full_macos_python_bootstrap_and_skill_launcher(self) -> None:
        python_package = Path(os.environ["IMAGE_GENERATION_TEST_MACOS_PYTHON_PKG"]).resolve()
        self.assertTrue(python_package.is_file())

        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            runtime_root = root / "runtime" / "3.12.10"
            skills_dir = root / "skills"
            config_file = root / "config" / "image-generation.json"
            api_key = "full-bootstrap-test-secret"
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["USERPROFILE"] = str(root)
            env["IMAGE_GENERATION_PYTHON_DOWNLOAD_URL"] = str(python_package)
            env["IMAGE_GENERATION_PYTHON_RUNTIME_ROOT"] = str(runtime_root)
            env["PATH"] = ""

            result = subprocess.run(
                [
                    str(MACOS_INSTALLER),
                    "--non-interactive",
                    "--skills-dir",
                    str(skills_dir),
                    "--config-file",
                    str(config_file),
                    "--api-url",
                    "https://api.example.com/v1",
                    "--api-key",
                    api_key,
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
                timeout=180,
            )
            self.assertNotIn(api_key, result.stdout + result.stderr)

            config = json.loads(config_file.read_text(encoding="utf-8"))
            managed_python = runtime_root / "Python.framework" / "Versions" / "3.12" / "bin" / "python3"
            self.assertEqual(Path(config["python_executable"]), managed_python.resolve())
            self.assertEqual(Path(config["ssl_cert_file"]), (runtime_root / "cert.pem").resolve())
            self.assertEqual(
                (runtime_root / ".codex-image-generation-managed-python-runtime").read_text(encoding="utf-8").strip(),
                "custom-image-generation:3.12.10",
            )

            launcher = skills_dir / "custom-image-generation" / "scripts" / "run-image-generation.command"
            launcher_env = env.copy()
            launcher_env["IMAGE_GENERATION_CONFIG"] = str(config_file)
            dry_run = subprocess.run(
                [
                    str(launcher),
                    "generate",
                    "--prompt",
                    "test prompt",
                    "--dry-run",
                    "--out",
                    str(root / "output.png"),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=launcher_env,
                timeout=30,
            )
            self.assertNotIn(api_key, dry_run.stdout + dry_run.stderr)
            payload = json.loads(dry_run.stdout)
            self.assertEqual(payload["payload"]["model"], "gpt-image-2")


if __name__ == "__main__":
    unittest.main()
