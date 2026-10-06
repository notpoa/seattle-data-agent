"""Noninteractive VS Code setup, using the same pinned dependencies as CI."""

from pathlib import Path
import subprocess
import sys
import venv


def main() -> int:
    if sys.version_info < (3, 12):
        print("Install Python 3.12 or newer. On Windows, run: py -3.12 scripts/setup_dev.py", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parents[1]
    environment = root / ".venv"
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    try:
        if not python.exists():
            print("Creating the project's .venv...", flush=True)
            venv.EnvBuilder(with_pip=True).create(environment)
        commands = [
            ["-m", "pip", "install", "-r", "requirements-dev.txt"],
            ["-m", "pip", "install", "--no-deps", "--no-build-isolation", "-e", "."],
            ["-m", "pip", "check"],
        ]
        for arguments in commands:
            subprocess.run([str(python), *arguments], cwd=root, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Setup failed: {exc}. See the command output above for the cause.", file=sys.stderr)
        return 1
    print("Setup complete. Run the 'Seattle: Run tests' task, then 'Seattle: Run backend'.")
    print("This starts the foundation API only; live Seattle data and the website are not implemented yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
