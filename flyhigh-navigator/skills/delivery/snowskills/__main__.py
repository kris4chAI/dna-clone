"""CLI: python -m snowskills list | run <skill> [--params file.json] [--out dir]"""
import argparse
import json
import pathlib

from . import REGISTRY, run

ap = argparse.ArgumentParser(prog="snowskills")
sub = ap.add_subparsers(dest="cmd", required=True)
sub.add_parser("list")
r = sub.add_parser("run")
r.add_argument("skill")
r.add_argument("--params", help="JSON file with parameters (defaults are used for anything missing)")
r.add_argument("--out", default="out")
a = ap.parse_args()
if a.cmd == "list":
    for s in REGISTRY.values():
        print(f"/{s.name:34} {s.stage:11} {s.title}")
else:
    params = json.loads(pathlib.Path(a.params).read_text()) if a.params else {}
    res = run(a.skill, params)
    for name, body in res["files"].items():
        f = pathlib.Path(a.out) / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body)
        print("wrote", f)
    print(res["summary"])
    for n in res["notes"]:
        print("note:", n)
