"""`secondchance setup tau2`: install tau2-bench at the pinned commit (code) and download its data/ folder; prints the TAU2_DATA_DIR to use.
tau2-bench is not distributed on PyPI, so it is installed from its repository at the exact commit of the evaluation."""
from __future__ import annotations

import io
import os
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

from secondchance import PINS


def tau2(dest=None):
    pin = PINS["tau2_bench"]
    url = f"git+{pin['repo']}@{pin['commit']}"
    subprocess.check_call([sys.executable, "-m", "pip", "install", f"tau2 @ {url}"])
    dest = Path(dest or Path.home() / ".cache" / "secondchance" / f"tau2-bench-{pin['commit'][:7]}")
    if not (dest / "data").exists():
        tgz = f"{pin['repo']}/archive/{pin['commit']}.tar.gz"
        with urllib.request.urlopen(tgz) as r:
            data = r.read()
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
            members = [m for m in t.getmembers() if m.name.split("/", 1)[-1].startswith("data/")]
            for m in members:
                m.name = m.name.split("/", 1)[1]
            t.extractall(dest, members=members, filter="data")
    print(f"tau2-bench {pin['commit'][:7]} installed; data in {dest / 'data'}")
    print(f"export TAU2_DATA_DIR={dest / 'data'}")
    return dest / "data"


def data_dir():
    """TAU2_DATA_DIR, or the folder `secondchance setup tau2` downloaded"""
    if os.environ.get("TAU2_DATA_DIR"):
        return os.environ["TAU2_DATA_DIR"]
    d = Path.home() / ".cache" / "secondchance" / f"tau2-bench-{PINS['tau2_bench']['commit'][:7]}" / "data"
    if d.exists():
        os.environ["TAU2_DATA_DIR"] = str(d)
        return str(d)
    return None
