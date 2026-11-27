#!/usr/bin/env python3
"""Validate the INTEND ontology project.

Parses every Turtle file individually (so a syntax error names its own
file rather than an opaque combined-graph error), then loads the
ontology + extensions + example instance data into one data graph and
validates it against the SHACL shapes with pyshacl. Optionally also runs
every query in queries/ against the loaded data.

Usage:
    python scripts/validate.py
    python scripts/validate.py --queries
    python scripts/validate.py --skip-shacl
"""

import argparse
import glob
import os
import sys

from rdflib import Graph
from pyshacl import validate as shacl_validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ONTOLOGY_FILES = [
    "ontology/external/tio-reference.ttl",
    "ontology/modules/intend-intent.ttl",
    "ontology/modules/intend-user.ttl",
    "ontology/modules/intend-resource.ttl",
    "ontology/modules/intend-application.ttl",
    "ontology/modules/intend-workflow.ttl",
    "ontology/intend.ttl",
    "extensions/intend-fill-extension.ttl",
    "extensions/intend-telenor-extension.ttl",
    "extensions/intend-gate-extension.ttl",
]
EXAMPLE_FILES = [
    "examples/fill-catalog-data.ttl",
    "examples/fill-instance-data.ttl",
    "examples/telenor-network-data.ttl",
    "examples/gate-microservices-data.ttl",
]
SHAPE_FILES = sorted(glob.glob(os.path.join(ROOT, "shapes", "*.ttl")))
QUERY_FILES = sorted(glob.glob(os.path.join(ROOT, "queries", "*.rq")))


def _abs(rel_or_abs_path):
    return rel_or_abs_path if os.path.isabs(rel_or_abs_path) else os.path.join(ROOT, rel_or_abs_path)


def parse_each(paths):
    """Parse each file individually and report per-file success/failure."""
    all_ok = True
    for rel in paths:
        path = _abs(rel)
        g = Graph()
        try:
            g.parse(path, format="turtle")
            print(f"  OK    {os.path.relpath(path, ROOT)}  ({len(g)} triples)")
        except Exception as exc:  # noqa: BLE001 - report and continue so all errors surface at once
            all_ok = False
            print(f"  FAIL  {os.path.relpath(path, ROOT)}: {exc}")
    return all_ok


def load_all(paths):
    g = Graph()
    for rel in paths:
        g.parse(_abs(rel), format="turtle")
    return g


def run_queries(data_graph):
    print("\n== Running competency-question queries ==")
    for qpath in QUERY_FILES:
        name = os.path.relpath(qpath, ROOT)
        with open(qpath, "r", encoding="utf-8") as f:
            query_text = f.read()
        print(f"\n--- {name} ---")
        try:
            rows = list(data_graph.query(query_text))
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR running query: {exc}")
            continue
        if not rows:
            print("  (no results)")
        for row in rows:
            print("  " + " | ".join("" if v is None else str(v) for v in row))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", action="store_true", help="also run every query in queries/ against the full data graph")
    parser.add_argument("--skip-shacl", action="store_true", help="skip SHACL validation (parsing checks only)")
    args = parser.parse_args()

    print("== Parsing ontology + extension files ==")
    ok1 = parse_each(ONTOLOGY_FILES)
    print("\n== Parsing example instance data ==")
    ok2 = parse_each(EXAMPLE_FILES)
    print("\n== Parsing SHACL shape files ==")
    ok3 = parse_each(SHAPE_FILES)

    if not (ok1 and ok2 and ok3):
        print("\nOne or more files failed to parse. Fix the errors above before continuing.")
        sys.exit(1)

    data_graph = load_all(ONTOLOGY_FILES + EXAMPLE_FILES)
    print(f"\nCombined data graph: {len(data_graph)} triples.")

    if not args.skip_shacl:
        shapes_graph = load_all(SHAPE_FILES)
        print(f"Combined shapes graph: {len(shapes_graph)} triples.")

        print("\n== Running SHACL validation (pyshacl) ==")
        # inference='none': every individual in examples/fill-instance-data.ttl is
        # explicitly typed with rdf:type, so sh:class checks do not need RDFS/OWL
        # entailment to fire. Keeping inference off makes failures easier to read.
        conforms, _results_graph, results_text = shacl_validate(
            data_graph=data_graph,
            shacl_graph=shapes_graph,
            inference="none",
            abort_on_first=False,
            allow_infos=True,
            allow_warnings=True,
        )
        print(results_text)
        if conforms:
            print("SHACL validation: CONFORMS")
        else:
            print("SHACL validation: DOES NOT CONFORM (see violations above)")
            sys.exit(2)

    if args.queries:
        run_queries(data_graph)

    print("\nDone.")


if __name__ == "__main__":
    main()
