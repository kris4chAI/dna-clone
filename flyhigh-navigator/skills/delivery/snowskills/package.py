"""Package delivery skills as .skill files (zip: <package>/SKILL.md, scripts/, examples/params.json)."""
import pathlib
import sys
import zipfile

from . import REGISTRY
from .skillmd import example_params, render

LIB = pathlib.Path(__file__).parent

RUNNER = '''"""Run {package} (/{name}). Usage: python scripts/run.py [--params params.json] [--out out]"""
import argparse, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from snowskills import run

ap = argparse.ArgumentParser()
ap.add_argument("--params"); ap.add_argument("--out", default="out")
a = ap.parse_args()
res = run("{name}", json.loads(pathlib.Path(a.params).read_text()) if a.params else {{}})
for f, body in res["files"].items():
    t = pathlib.Path(a.out) / f; t.parent.mkdir(parents=True, exist_ok=True); t.write_text(body); print("wrote", t)
print(res["summary"]); [print("note:", n) for n in res["notes"]]
'''


def add_to_zip(z: zipfile.ZipFile, sk) -> str:
    root = sk.package
    z.writestr(f"{root}/SKILL.md", render(sk))
    z.writestr(f"{root}/examples/params.json", example_params(sk))
    z.writestr(f"{root}/scripts/run.py", RUNNER.format(package=sk.package, name=sk.name))
    for f in LIB.glob("*.py"):
        if f.name not in ("package.py", "__main__.py"):
            z.write(f, f"{root}/scripts/snowskills/{f.name}")
    return f"{root}.skill"


if __name__ == "__main__":
    print("Use tools/package_skills.py from the FlyHigh Navigator root to rebuild packages.")
