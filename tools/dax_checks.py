"""Run a model's DAX checks against a deployed semantic model through the Fabric CLI.

usage: python3 -I tools/dax_checks.py <workspace id> <dataset id> <checks.dax>

Queries in the .dax file are separated by blank-line-preceded `// ` comment headers; each EVALUATE block is sent
to the Power BI executeQueries REST API (one query per call) and printed as a table.
"""
import json, os, re, subprocess, sys, tempfile

ws, ds, path = sys.argv[1:4]
fab = os.path.expanduser("~/.local/bin/fab")
text = open(path).read()
blocks = [b.strip() for b in re.split(r"\n(?=// \d+\.)", text) if "EVALUATE" in b]

for block in blocks:
    title = block.splitlines()[0]
    query = "\n".join(l for l in block.splitlines() if not l.startswith("//"))
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"queries": [{"query": query}], "serializerSettings": {"includeNulls": True}}, f)
    out = subprocess.run([fab, "api", "-A", "powerbi", "-X", "post",
                          f"groups/{ws}/datasets/{ds}/executeQueries", "-i", f.name],
                         capture_output=True, text=True).stdout
    os.unlink(f.name)
    print(title)
    try:
        body = json.loads(out)["text"]
        rows = body["results"][0]["tables"][0]["rows"]
    except Exception:
        print(out[:2000]); continue
    cols = list(rows[0].keys()) if rows else []
    short = [re.sub(r"^.*\[(.*)\]$", r"\1", c) for c in cols]
    print(" | ".join(short))
    for r in rows:
        vals = []
        for c in cols:
            v = r[c]
            vals.append(f"{v:.4f}" if isinstance(v, float) else str(v))
        print(" | ".join(vals))
    print()
