"""Rebuild every skill package and the skills catalog from source.

    python tools/package_skills.py

Sources:  skills/pursuit/<name>/SKILL.md          (9 pursuit skills)
          skills/delivery/snowskills/              (46 Snowflake delivery skill generators)
Outputs:  skills/packages/pursuit/<name>.skill
          skills/packages/delivery/sf-<name>.skill  (SKILL.md + scripts/run.py + scripts/snowskills + examples/params.json)
          skills/delivery/catalog/sf-<name>/SKILL.md and examples/params.json   (readable copies)
          skills/README.md                          (catalog)
"""
import pathlib
import re
import shutil
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SK = ROOT / "skills"
sys.path.insert(0, str(SK / "delivery"))
from snowskills import REGISTRY  # noqa: E402
from snowskills.package import add_to_zip  # noqa: E402
from snowskills.skillmd import example_params, render  # noqa: E402

STAGE_ORDER = ["discover", "design", "foundation", "migration", "assurance", "release", "monitor"]
STAGE_NAME = {"discover": "1 Discover", "design": "2 Design", "foundation": "4 Foundation build", "migration": "6 Platform migration",
              "assurance": "8 Platform assurance", "release": "9 Build & release", "monitor": "10 Operate & monitor"}


def main():
    pk = SK / "packages"
    shutil.rmtree(pk, ignore_errors=True)
    (pk / "pursuit").mkdir(parents=True)
    (pk / "delivery").mkdir(parents=True)
    cat = SK / "delivery" / "catalog"
    shutil.rmtree(cat, ignore_errors=True)

    pursuit_rows = []
    for d in sorted(p for p in (SK / "pursuit").iterdir() if p.is_dir()):
        with zipfile.ZipFile(pk / "pursuit" / f"{d.name}.skill", "w", zipfile.ZIP_DEFLATED) as z:
            for f in d.rglob("*"):
                if f.is_file():
                    z.write(f, f"{d.name}/{f.relative_to(d)}")
        desc = re.search(r'description:\s*"(.*?)"', (d / "SKILL.md").read_text())
        pursuit_rows.append(f"| `{d.name}` | {desc.group(1) if desc else ''} | [SKILL.md](pursuit/{d.name}/SKILL.md) · [package](packages/pursuit/{d.name}.skill) |")

    delivery_rows = []
    for sk in sorted(REGISTRY.values(), key=lambda s: (STAGE_ORDER.index(s.stage), s.name)):
        with zipfile.ZipFile(pk / "delivery" / f"{sk.package}.skill", "w", zipfile.ZIP_DEFLATED) as z:
            add_to_zip(z, sk)
        c = cat / sk.package
        (c / "examples").mkdir(parents=True)
        (c / "SKILL.md").write_text(render(sk))
        (c / "examples" / "params.json").write_text(example_params(sk))
        delivery_rows.append(f"| {STAGE_NAME[sk.stage]} | `/{sk.name}` | {sk.title} · {sk.agent} | {', '.join(sk.snowflake[:3])} | "
                             f"[SKILL.md](delivery/catalog/{sk.package}/SKILL.md) · [package](packages/delivery/{sk.package}.skill) |")

    (SK / "README.md").write_text(f"""# Skills

Everything FlyHigh Navigator knows how to *do* lives in this folder. The app loads these files at runtime; the
`.skill` packages are the same skills packaged for Claude (Settings → Skills → upload) or for running standalone.

| Folder | What it holds |
|---|---|
| `pursuit/<name>/SKILL.md` | The {len(pursuit_rows)} AI Native Sales Engineering pursuit skills (source of truth) |
| `delivery/snowskills/` | The Snowflake generator library behind the {len(delivery_rows)} delivery skills (pure Python, stdlib only) |
| `delivery/catalog/sf-*/` | Readable SKILL.md and example parameters per delivery skill |
| `packages/pursuit/*.skill`, `packages/delivery/*.skill` | Packaged skills (zip format) |

Rebuild packages and this catalog after editing a skill: `python tools/package_skills.py`.

Run a delivery skill without the app:

```bash
cd skills/delivery && python -m snowskills list
python -m snowskills run gen-grants --params catalog/sf-gen-grants/examples/params.json --out /tmp/out
```

## Pursuit skills ({len(pursuit_rows)})

| Skill | Purpose | Files |
|---|---|---|
{chr(10).join(pursuit_rows)}

## Snowflake delivery skills ({len(delivery_rows)})

| Stage | Skill | What · agent | Snowflake features | Files |
|---|---|---|---|---|
{chr(10).join(delivery_rows)}
""")
    print(f"{len(pursuit_rows)} pursuit + {len(delivery_rows)} delivery packages; catalog at skills/README.md")


if __name__ == "__main__":
    main()
