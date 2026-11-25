"""Validate Apache Ossie documents against the core JSON schema, plus the naming rules the schema can't express.

    python3 -m venv /tmp/ossie-venv && /tmp/ossie-venv/bin/pip install pyyaml jsonschema
    curl -sLo /tmp/ossie-schema.json https://raw.githubusercontent.com/apache/ossie/main/core-spec/ossie-schema.json
    /tmp/ossie-venv/bin/python tools/ossie-check/check.py --schema /tmp/ossie-schema.json models/*/ossie/*.ossie.yaml

Checks: JSON Schema 2020-12 validation; unique dataset names; within a dataset, field and metric names share one
namespace; model metric names unique and not reused by a dataset metric; relationship datasets and columns exist;
primary keys name declared fields. It does not parse the SQL as OSSIE_SQL_2026. Exit code 1 on any failure.
"""
import argparse, json, sys

import yaml
from jsonschema import Draft202012Validator


def names_ok(doc):
    errs = []
    ds = doc.get("datasets", [])
    dnames = [d["name"] for d in ds]
    for n in {n for n in dnames if dnames.count(n) > 1}:
        errs.append(f"dataset name repeated: {n}")
    fields_of = {}
    dataset_metrics = set()
    for d in ds:
        fnames = [f["name"] for f in d.get("fields", [])]
        mnames = [m["name"] for m in d.get("metrics", [])]
        both = fnames + mnames
        for n in {n for n in both if both.count(n) > 1}:
            errs.append(f"{d['name']}: field/metric name repeated: {n}")
        for k in d.get("primary_key", []):
            if k not in fnames:
                errs.append(f"{d['name']}: primary key {k} is not a field")
        fields_of[d["name"]] = set(fnames)
        dataset_metrics |= set(mnames)
    mm = [m["name"] for m in doc.get("metrics", [])]
    for n in {n for n in mm if mm.count(n) > 1}:
        errs.append(f"model metric name repeated: {n}")
    for n in set(mm) & dataset_metrics:
        errs.append(f"model metric also a dataset metric: {n}")
    rn = [r["name"] for r in doc.get("relationships", [])]
    for n in {n for n in rn if rn.count(n) > 1}:
        errs.append(f"relationship name repeated: {n}")
    for r in doc.get("relationships", []):
        for side, cols in (("from", "from_columns"), ("to", "to_columns")):
            if r[side] not in fields_of:
                errs.append(f"{r['name']}: unknown dataset {r[side]}")
                continue
            for c in r[cols]:
                if c not in fields_of[r[side]]:
                    errs.append(f"{r['name']}: {r[side]} has no field {c}")
        if len(r["from_columns"]) != len(r["to_columns"]):
            errs.append(f"{r['name']}: column counts differ")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    schema = json.load(open(a.schema))
    Draft202012Validator.check_schema(schema)
    v = Draft202012Validator(schema)
    version = schema["properties"]["version"].get("const")
    bad = 0
    for f in a.files:
        doc = yaml.safe_load(open(f))
        errs = [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in v.iter_errors(doc)]
        if not errs:
            errs = names_ok(doc)
        n_ds = len(doc.get("datasets", []))
        n_m = sum(len(d.get("metrics", [])) for d in doc.get("datasets", [])) + len(doc.get("metrics", []))
        if errs:
            bad += 1
            print(f"FAIL {f}")
            for e in errs[:20]:
                print("   ", e)
        else:
            print(f"ok   {f}  (schema {version}; {n_ds} datasets, {len(doc.get('relationships', []))} relationships, {n_m} metrics)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
