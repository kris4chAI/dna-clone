"""Build and release skills: artefact builds, linting, PR templates, promotion, rollback, changelog and release notes."""
import re
from datetime import date

from . import Field, header, ident, lit, skill

ENVS = Field("envs", "Environments in promotion order", "lines", "DEV\nSTG\nPRD")


@skill(name="build-artifacts", stage="release", agent="Build Agent", title="Build Snowflake artefacts",
       description="Scaffold the repository for Snowflake as code (schemachange migrations, dbt, policies) and a GitHub Actions build that validates every change against a zero-copy clone.",
       snowflake=["schemachange", "Snowflake CLI (snow)", "Zero-copy clone for PR validation", "dbt-snowflake"],
       fields=[Field("repo", "Repository name", "text", "flyhigh-snowflake"), Field("database", "Database validated per PR", "text", "FLYHIGH_DEV_SILVER")],
       steps=["Create the layout and commit it.", "Add SNOWFLAKE_* secrets in GitHub (key-pair).", "Every PR clones the DEV database, deploys into the clone, runs tests and drops it."],
       gate="Build must be green before review")
def build_artifacts(p, sk):
    db = ident(p.s("database"))
    layout = f"""# {p.s('repo')}
migrations/            # schemachange V__/R__/A__ scripts (from /gen-migration)
policies/              # masking, row access, network (from /gen-masking, /gen-rls)
rbac/                  # grants (from /gen-grants)
dbt/                   # models, tests (from /convert-etl, /gen-unit-tests)
tests/sql/             # assertions, reconciliation, golden queries
docs/adr/ docs/runbooks/
.github/workflows/build.yml
.sqlfluff
"""
    wf = f"""name: build
on: [pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    env:
      SNOWFLAKE_ACCOUNT: ${{{{ secrets.SNOWFLAKE_ACCOUNT }}}}
      SNOWFLAKE_USER: ${{{{ secrets.SNOWFLAKE_USER }}}}
      SNOWFLAKE_PRIVATE_KEY_RAW: ${{{{ secrets.SNOWFLAKE_PRIVATE_KEY }}}}
      SNOWFLAKE_ROLE: FR_CICD
      SNOWFLAKE_WAREHOUSE: WH_CICD
      CLONE_DB: {db}_PR_${{{{ github.event.number }}}}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {{ python-version: "3.11" }}
      - run: pip install schemachange snowflake-cli sqlfluff dbt-snowflake
      - name: Lint
        run: sqlfluff lint migrations policies rbac --dialect snowflake
      - name: Clone DEV for this PR
        run: snow sql --temporary-connection -q "CREATE OR REPLACE DATABASE $CLONE_DB CLONE {db}"
      - name: Deploy into the clone
        run: schemachange deploy -f migrations -d $CLONE_DB -c $CLONE_DB.SCHEMACHANGE.CHANGE_HISTORY --create-change-history-table
      - name: Assertions
        run: for f in tests/sql/*.sql; do snow sql --temporary-connection -f "$f" --database $CLONE_DB; done
      - name: Drop clone
        if: always()
        run: snow sql --temporary-connection -q "DROP DATABASE IF EXISTS $CLONE_DB"
"""
    return {"files": {"REPO_LAYOUT.md": layout, ".github/workflows/build.yml": wf}, "summary": "Repo layout and PR build with a zero-copy clone.",
            "notes": ["Check schemachange and Snowflake CLI flag names against the versions you pin."]}


@skill(name="lint-sql", stage="release", agent="Quality Gate", title="Lint SQL",
       description="Enforce one SQL standard with SQLFluff (Snowflake dialect), a pre-commit hook and a quick check of a pasted script for common Snowflake anti-patterns.",
       snowflake=["SQLFluff snowflake dialect", "Anti-pattern checks (SELECT *, ORDER BY without LIMIT, CREATE OR REPLACE on tables)"],
       fields=[Field("sql", "SQL to check (optional)", "textarea", "create or replace table FLYHIGH_PRD_GOLD.WAREHOUSE.T as select * from X order by 1;"),
               Field("max_line", "Max line length", "number", "140")],
       steps=["Commit .sqlfluff and .pre-commit-config.yaml.", "Fix every finding or justify it in the PR."],
       gate="Quality gate: lint must pass on every PR")
def lint_sql(p, sk):
    cfg = f"""[sqlfluff]
dialect = snowflake
templater = jinja
max_line_length = {int(p.n('max_line', 140))}
exclude_rules = LT05

[sqlfluff:rules:capitalisation.keywords]
capitalisation_policy = upper
[sqlfluff:rules:capitalisation.identifiers]
extended_capitalisation_policy = upper
"""
    pc = "repos:\n  - repo: https://github.com/sqlfluff/sqlfluff\n    rev: 3.2.5\n    hooks:\n      - id: sqlfluff-lint\n        args: [--dialect, snowflake]\n"
    s, f = p.s("sql"), []
    checks = [(r"select\s+\*", "SELECT * in shipped code: list columns"), (r"order\s+by(?![\s\S]*limit)", "ORDER BY without LIMIT in a table build wastes compute"),
              (r"create\s+or\s+replace\s+table", "CREATE OR REPLACE TABLE drops history and grants; use CREATE TABLE IF NOT EXISTS + ALTER, or COPY GRANTS"),
              (r"\bdelete\s+from\s+\S+\s*;", "DELETE without WHERE"), (r"\bprd\b|_prd_", "Hard-coded PRD environment: parameterize the database")]
    for pat, msg in checks:
        if re.search(pat, s, re.I):
            f.append(msg)
    if s and s == s.lower():
        f.append("Keywords should be upper case (capitalisation.keywords)")
    rep = "# Lint findings\n\n" + ("\n".join(f"- {x}" for x in f) if f else "- No findings") + "\n"
    return {"files": {".sqlfluff": cfg, ".pre-commit-config.yaml": pc, "findings.md": rep}, "summary": f"{len(f)} findings.", "notes": f}


@skill(name="pr-template", stage="release", agent="Quality Gate", title="Pull request template",
       description="Pull request and CODEOWNERS templates that carry the gate evidence: tests, reconciliation, rollback, access changes and stamps.",
       snowflake=["Evidence links to Snowflake query IDs and recon tables"],
       fields=[Field("owners", "Code owners (path | team)", "lines", "/policies/ | @flyhigh/security\n/rbac/ | @flyhigh/security\n/migrations/ | @flyhigh/platform\n/dbt/ | @flyhigh/data-eng")],
       steps=["Commit both files to .github/.", "Branch protection: require code-owner review and the build check."],
       gate="Release manager enforces the template")
def pr_template(p, sk):
    t = """## What changes
<!-- objects, models, policies -->

## Why
<!-- ticket, PRD / design link -->

## Evidence
- [ ] Build green (lint, clone deploy, assertions)
- [ ] Unit tests / DMFs added or updated
- [ ] Reconciliation or golden queries: link to RECON_RESULT / GOLDEN_RUN
- [ ] Access changes reviewed by security (grants, masking, row access)
- [ ] Rollback written (rollback.sql or Time Travel steps)
- [ ] Runbook / ADR updated if behaviour changed
- [ ] Unvalidated items stamped (ILLUSTRATIVE / INDICATIVE / FOR JOINT REVIEW)
"""
    co = "".join(f"{a.strip()} {b.strip()}\n" for a, _, b in (l.partition("|") for l in p.lines("owners")))
    return {"files": {".github/pull_request_template.md": t, ".github/CODEOWNERS": co}, "summary": "PR template and CODEOWNERS."}


@skill(name="promote", stage="release", agent="Promotion Agent", title="Promote dev → stage → prod",
       description="Promote the same artefacts through environments with GitHub environment approvals, schemachange per environment and post-deploy checks.",
       snowflake=["schemachange per environment", "Snowflake CLI", "Golden queries after deploy"],
       fields=[ENVS, Field("prefix", "Database prefix", "text", "FLYHIGH"), Field("approvers", "Approvers for production", "text", "release-manager")],
       steps=["Create GitHub environments with required reviewers (STG, PRD).", "Tag a release; the workflow deploys DEV → STG → PRD with approval at each step.", "Golden queries must pass before the next environment."],
       gate="Release manager approves each promotion")
def promote(p, sk):
    envs = [ident(e) for e in p.lines("envs")]
    jobs, prev = [], None
    for e in envs:
        jobs.append(f"""  deploy_{e.lower()}:
    runs-on: ubuntu-latest
    environment: {e.lower()}{chr(10) + '    needs: deploy_' + prev.lower() if prev else ''}
    env:
      SNOWFLAKE_ACCOUNT: ${{{{ secrets.SNOWFLAKE_ACCOUNT }}}}
      SNOWFLAKE_USER: ${{{{ secrets.SNOWFLAKE_USER }}}}
      SNOWFLAKE_PRIVATE_KEY_RAW: ${{{{ secrets.SNOWFLAKE_PRIVATE_KEY }}}}
      SNOWFLAKE_ROLE: FR_CICD_{e}
    steps:
      - uses: actions/checkout@v4
      - run: pip install schemachange snowflake-cli
      - run: schemachange deploy -f migrations --vars '{{"env": "{e}"}}' -c {ident(p.s('prefix'))}_{e}_SILVER.SCHEMACHANGE.CHANGE_HISTORY
      - run: snow sql --temporary-connection -q "CALL {ident(p.s('prefix'))}_{e}_GOLD.QA.SP_RUN_GOLDEN(FALSE)"
""")
        prev = e
    wf = "name: promote\non:\n  push:\n    tags: ['v*']\njobs:\n" + "".join(jobs)
    md = ["# Promotion", "", "| Environment | Approval | Check |", "|---|---|---|"] + [
        f"| {e} | {'automatic' if i == 0 else p.s('approvers')} | schemachange + golden queries |" for i, e in enumerate(envs)]
    return {"files": {".github/workflows/promote.yml": wf, "promotion.md": "\n".join(md) + "\n"}, "summary": f"{' → '.join(envs)} with approvals."}


@skill(name="rollback", stage="release", agent="Promotion Agent", title="Roll back a release",
       description="Generate rollback steps per object using Time Travel (clone at timestamp, UNDROP) and a forward-fix template, with verification queries.",
       snowflake=["Time Travel AT (TIMESTAMP)", "UNDROP", "Zero-copy clone", "Fail-safe awareness"],
       fields=[Field("release_ts", "Release start timestamp (UTC)", "text", "2026-11-05 22:00:00"),
               Field("objects", "Objects changed (type | name)", "lines", "TABLE | FLYHIGH_PRD_GOLD.WAREHOUSE.FACT_WAREHOUSE_TASK\nVIEW | FLYHIGH_PRD_GOLD.WAREHOUSE.V_SITE_OPS\nDROPPED TABLE | FLYHIGH_PRD_GOLD.WAREHOUSE.FACT_LABOR_OLD")],
       steps=["Decide rollback vs forward fix with the release manager.", "Run rollback.sql object by object; verify counts.", "Record the incident and update the runbook."],
       gate="Release manager authorizes production rollback")
def rollback(p, sk):
    ts = lit(p.s("release_ts"))
    out = [header(sk, f"rollback to before {p.s('release_ts')}"), f"SET before_release = {ts}::TIMESTAMP_LTZ;"]
    for l in p.lines("objects"):
        typ, _, name = [x.strip() for x in l.partition("|")]
        if typ.upper() == "TABLE":
            out.append(f"""-- {name}: restore data and structure as of the release start
CREATE OR REPLACE TABLE {name}_RESTORE CLONE {name} AT (TIMESTAMP => $before_release);
SELECT (SELECT COUNT(*) FROM {name}) AS current_rows, (SELECT COUNT(*) FROM {name}_RESTORE) AS restored_rows;
ALTER TABLE {name} SWAP WITH {name}_RESTORE;   -- keeps grants on the original name
-- DROP TABLE {name}_RESTORE;  -- after sign-off""")
        elif typ.upper() == "DROPPED TABLE":
            out.append(f"-- {name}: was dropped by the release\nUNDROP TABLE {name};")
        else:
            out.append(f"-- {name}: re-run the previous version of the R__ script from git (views/procedures have no Time Travel)\n-- git show <previous_tag>:migrations/R__<name>.sql > restore.sql && snow sql -f restore.sql")
    out.append("-- Time Travel only reaches back DATA_RETENTION_TIME_IN_DAYS; after that the data is in Fail-safe (Snowflake support only).")
    return {"files": {"rollback.sql": "\n\n".join(out) + "\n"}, "summary": f"Rollback for {len(p.lines('objects'))} objects."}


@skill(name="gen-changelog", stage="release", agent="Release Agent", title="Generate changelog",
       description="Turn conventional commits since the last tag into a CHANGELOG.md section and the next semantic version.",
       snowflake=["Release metadata for schemachange versions"],
       fields=[Field("last_version", "Last version", "text", "1.2.0"),
               Field("commits", "Commits since last tag (one per line)", "lines",
                     "feat(gold): add FACT_WAVE_PROGRESS [FH-212]\nfix(rls): include wildcard entitlement [FH-219]\nfeat(semantic): SV_SITE_OPS with UPH and pick accuracy [FH-220]\nchore(ci): pin schemachange\nfeat!: rename DIM_SITE.REGION to REGION_CODE [FH-230]")],
       steps=["Paste `git log --pretty=%s vLAST..HEAD`.", "Commit the section on the release branch; tag the version."],
       gate="Release agent output reviewed by the release manager")
def gen_changelog(p, sk):
    groups = {"Breaking changes": [], "Features": [], "Fixes": [], "Other": []}
    major = minor = patch = False
    for c in p.lines("commits"):
        m = re.match(r"(\w+)(\([^)]*\))?(!)?:\s*(.+)", c)
        if not m:
            groups["Other"].append(c); continue
        typ, scope, bang, msg = m.groups()
        line = f"- {('**' + scope.strip('()') + '**: ') if scope else ''}{msg}"
        if bang or "BREAKING" in c:
            groups["Breaking changes"].append(line); major = True
        elif typ == "feat":
            groups["Features"].append(line); minor = True
        elif typ == "fix":
            groups["Fixes"].append(line); patch = True
        else:
            groups["Other"].append(line)
    a, b, c_ = [int(x) for x in p.s("last_version").split(".")]
    nxt = f"{a+1}.0.0" if major else f"{a}.{b+1}.0" if minor else f"{a}.{b}.{c_+1}"
    md = [f"## [{nxt}] - {date.today()}", ""]
    for k, v in groups.items():
        if v:
            md += [f"### {k}", *v, ""]
    return {"files": {"CHANGELOG_SECTION.md": "\n".join(md)}, "summary": f"Next version {nxt}."}


@skill(name="release-notes", stage="release", agent="Release Agent", title="Release notes",
       description="Write business-readable release notes from the changelog with Snowflake objects changed, evidence and rollback pointer.",
       snowflake=["Objects changed", "Evidence: GOLDEN_RUN, RECON_RESULT query IDs"],
       fields=[Field("version", "Version", "text", "2.0.0"),
               Field("highlights", "Highlights for users (one per line)", "lines", "Site Daily Operations shows live UPH by zone\nCustomer portal shows only each shipper's orders"),
               Field("objects", "Snowflake objects changed", "lines", "FLYHIGH_PRD_GOLD.WAREHOUSE.FACT_WAVE_PROGRESS (new)\nFLYHIGH_PRD_GOLD.WAREHOUSE.SV_SITE_OPS (new)\nGOVERNANCE.POLICIES.RAP_CUSTOMER_ID (changed)"),
               Field("evidence", "Evidence links", "lines", "Golden queries: 14/14 PASS\nReconciliation wave 2: 0 open variances")],
       steps=["Generate after the changelog.", "Attach to the GitHub release and the change ticket."],
       gate="Release manager publishes after production approval")
def release_notes(p, sk):
    md = [f"# Release {p.s('version')} · {date.today()}", "", "## What's new", *[f"- {x}" for x in p.lines("highlights")], "",
          "## Snowflake objects", *[f"- `{x}`" for x in p.lines("objects")], "", "## Evidence", *[f"- {x}" for x in p.lines("evidence")], "",
          "## Rollback", "- See rollback.sql in this release (generated by /rollback).", ""]
    return {"files": {f"release-notes-{p.s('version')}.md": "\n".join(md)}, "summary": "Release notes drafted."}
