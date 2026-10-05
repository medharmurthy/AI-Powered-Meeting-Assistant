from __future__ import annotations

import argparse
import os
import platform
from pathlib import Path
import sys
import threading
import time
import webbrowser

# Add backend directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def prepare_environment() -> None:
    system = platform.system().lower()
    from verbatim.gpu import prepare_cuda

    cuda_dirs = prepare_cuda()
    if system == "linux" and cuda_dirs:
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        needed = [d for d in cuda_dirs if d not in current_ld.split(":")]
        if needed:
            new_ld = ":".join(needed + ([current_ld] if current_ld else []))
            os.environ["LD_LIBRARY_PATH"] = new_ld
            if os.environ.get("_VERBATIM_REEXEC") != "1":
                os.environ["_VERBATIM_REEXEC"] = "1"
                os.execv(sys.executable, [sys.executable] + sys.argv)


def open_browser_delayed(url: str, delay: float = 1.2) -> None:
    def _open():
        time.sleep(delay)
        webbrowser.open(url)

    t = threading.Thread(target=_open, daemon=True)
    t.start()


def main():
    parser = argparse.ArgumentParser(description="Start the Verbatim server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn auto-reload")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    prepare_environment()

    import uvicorn

    url = f"http://{args.host}:{args.port}"
    print(f"\nStarting Verbatim at {url} ...\n")

    if not args.no_browser and not args.reload:
        open_browser_delayed(url)

    uvicorn.run(
        "verbatim.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
