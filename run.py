from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
RELAUNCH_ENV = "MAGISTER_RUNPY_RELAUNCHED"

BANNER = r"""
 _    _  ____   _____ _    _ __  __             _     _             _____ _____ _____
| |  | |/ __ \ / ____| |  | |  \/  |           (_)   | |           |  _  |  __ \_   _|
| |  | | |  | | (___ | |__| | \  / | __ _  __ _ _ ___| |_ ___ _ __ | |_| | |__) || |
| |  | | |  | |\___ \|  __  | |\/| |/ _` |/ _` | / __| __/ _ \ '__||  _  |  ___/ | |
| |__| | |__| |____) | |  | | |  | | (_| | (_| | \__ \ ||  __/ |   | | | | |    _| |_
 \____/ \____/|_____/|_|  |_|_|  |_|\__,_|\__, |_|___/\__\___|_|   \_| |_|_|   |_____|
                                           __/ |
                                          |___/
      Unofficial Selfhosted Magister API
"""


def _pause(message: str = "Press Enter to close...") -> None:
    try:
        input(message)
    except EOFError:
        pass


def _set_project_dir() -> None:
    os.chdir(PROJECT_DIR)
    project_dir = str(PROJECT_DIR)
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)


def _find_venv_dir() -> Path | None:
    for candidate in (PROJECT_DIR / ".venv", PROJECT_DIR / "venv", PROJECT_DIR / "env"):
        if candidate.exists():
            return candidate
    return None


def _read_venv_version() -> tuple[int, int] | None:
    venv_dir = _find_venv_dir()
    if not venv_dir:
        return None
    pyvenv_cfg = venv_dir / "pyvenv.cfg"
    if not pyvenv_cfg.exists():
        return None
    for line in pyvenv_cfg.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.lower().startswith("version ="):
            version_text = line.split("=", 1)[1].strip()
            parts = version_text.split(".")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                return int(parts[0]), int(parts[1])
    return None


def _add_venv_site_packages() -> bool:
    venv_version = _read_venv_version()
    if venv_version and venv_version != sys.version_info[:2]:
        return False
    for candidate in (
        PROJECT_DIR / ".venv" / "Lib" / "site-packages",
        PROJECT_DIR / "venv" / "Lib" / "site-packages",
        PROJECT_DIR / "env" / "Lib" / "site-packages",
    ):
        if candidate.exists():
            site_packages = str(candidate)
            if site_packages not in sys.path:
                sys.path.insert(0, site_packages)
            return True
    return False


def _find_venv_python() -> Path | None:
    venv_dir = _find_venv_dir()
    if not venv_dir:
        return None
    candidate = venv_dir / "Scripts" / "python.exe"
    return candidate if candidate.exists() else None


def _using_local_venv() -> bool:
    current_python = Path(sys.executable).resolve()
    venv_python = _find_venv_python()
    return bool(venv_python and current_python == venv_python.resolve())


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _can_run_python(python_path: Path) -> bool:
    try:
        completed = subprocess.run(
            [str(python_path), "-c", "import sys"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except OSError:
        return False
    except subprocess.SubprocessError:
        return False
    return completed.returncode == 0


def _ensure_local_venv() -> None:
    venv_python = _find_venv_python()
    if not venv_python or _using_local_venv() or os.environ.get(RELAUNCH_ENV) == "1":
        return
    if not _can_run_python(venv_python):
        return
    env = os.environ.copy()
    env[RELAUNCH_ENV] = "1"
    completed = subprocess.run([str(venv_python), str(PROJECT_DIR / "run.py"), *sys.argv[1:]], env=env)
    sys.exit(completed.returncode)


def _powershell(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )


def _looks_like_project_server(pid: int) -> bool:
    completed = _powershell(
        f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\"; "
        f"if ($null -eq $p) {{ '' }} else {{ \"$($p.Name)`n$($p.CommandLine)\" }}"
    )
    if completed.returncode != 0:
        return False

    output = completed.stdout.strip().lower()
    if not output:
        return False

    project_markers = (
        str(PROJECT_DIR).lower(),
        str(PROJECT_DIR / "run.py").lower(),
        "app.main:app",
        "uoshmagisterapi",
    )
    return any(marker in output for marker in project_markers)


def _kill_process_tree(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _stop_existing_servers(port: int) -> None:
    completed = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return

    pids: set[int] = set()
    port_suffix = f":{port}"
    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local_address = parts[1]
        pid_text = parts[-1]
        if not local_address.endswith(port_suffix):
            continue
        if not pid_text.isdigit():
            continue
        pid = int(pid_text)
        if pid == os.getpid():
            continue
        pids.add(pid)

    for pid in pids:
        if _looks_like_project_server(pid):
            _kill_process_tree(pid)

    if pids:
        time.sleep(1)


def main() -> None:
    _set_project_dir()
    added_venv_site_packages = _add_venv_site_packages()
    _ensure_local_venv()

    missing_modules = [name for name in ("uvicorn", "fastapi", "playwright") if not _module_available(name)]
    if missing_modules:
        venv_python = _find_venv_python()
        joined = ", ".join(missing_modules)
        venv_version = _read_venv_version()
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        venv_version_text = f"{venv_version[0]}.{venv_version[1]}" if venv_version else "unknown"
        version_note = ""
        if venv_version and venv_version != sys.version_info[:2]:
            version_note = f" The local virtual environment targets Python {venv_version_text}, but you are running Python {current_version}."
        elif venv_python and not added_venv_site_packages:
            version_note = " The local virtual environment was found, but its packages could not be loaded safely."
        raise RuntimeError(
            f"Missing Python packages: {joined}. Run the project with the local virtual environment"
            f"{f' ({venv_python})' if venv_python else ''} or install requirements there.{version_note}"
        )

    import uvicorn
    from app.config import settings

    host = settings.api_host
    port = settings.api_port

    _stop_existing_servers(port)

    print(BANNER)
    print(f"UOSHMagisterAPI -> http://{host}:{port}/docs")
    print("Use /ui for the browser dashboard.")
    print("Open the URL manually; the launcher keeps this console in the foreground.")
    print(f"Python: {sys.executable}")

    uvicorn.run("app.main:app", host=host, port=port, reload=False, log_level="info")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        _pause()
