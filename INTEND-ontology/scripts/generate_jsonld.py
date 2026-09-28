#!/usr/bin/env python3
"""Generate a JSON-LD clone of every Turtle file in the project.

Mirrors ontology/, extensions/, shapes/, examples/ and everything.ttl into
jsonld/ with the same relative paths (.ttl -> .jsonld). Turtle remains the
canonical source; this script is safe to re-run any time the .ttl files
change — it always regenerates jsonld/ from scratch.

Each output file's @context uses exactly the prefixes declared in its own
source .ttl file (extracted directly from the file's @prefix lines), so the
JSON-LD comes out compact and readable instead of rdflib's default fully-
expanded form.

After generating, verifies every file round-trips: re-parses the generated
.jsonld and checks it is graph-isomorphic to a fresh parse of the source
.ttl (isomorphism, not raw triple-set equality, because the SHACL shape
files use blank nodes) -- after normalizing away the one benign, spec-
correct difference JSON-LD compaction introduces: an explicitly
^^xsd:string-typed literal in Turtle round-trips as a plain (datatype-less)
literal via JSON-LD, because RDF 1.1 defines a language-less, datatype-less
"simple literal" to already BE an xsd:string (JSON-LD's compaction drops
the now-redundant annotation when serializing such a value as a plain JSON
string). Both forms are the same RDF term per spec; comparing them without
normalizing first would report ~1000+ false "mismatches" on the larger
example files purely from this cosmetic difference, so both graphs are
normalized to the bare-literal form before the isomorphism check. Every
other datatype (decimal, double, boolean, integer, anyURI) was verified
during development to round-trip byte-for-byte identical with no
normalization needed.

Usage:
    python scripts/generate_jsonld.py
"""

import os
import re
import sys

from rdflib import Graph, Literal, XSD
from rdflib.compare import isomorphic


def _normalize_plain_strings(g):
    """Return a copy of g with every ^^xsd:string literal rewritten as a
    plain (datatype-less) literal, so RDF-1.1-equivalent graphs that differ
    only in this redundant annotation compare as isomorphic."""
    out = Graph()
    for s, p, o in g:
        if isinstance(o, Literal) and o.datatype == XSD.string:
            o = Literal(str(o))
        out.add((s, p, o))
    return out

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TTL_FILES = [
    "ontology/intend.ttl",
    "ontology/modules/intend-intent.ttl",
    "ontology/modules/intend-user.ttl",
    "ontology/modules/intend-resource.ttl",
    "ontology/modules/intend-application.ttl",
    "ontology/modules/intend-workflow.ttl",
    "ontology/external/tio-reference.ttl",
    "extensions/intend-fill-extension.ttl",
    "extensions/intend-telenor-extension.ttl",
    "extensions/intend-gate-extension.ttl",
    "shapes/intend-shapes-intent.ttl",
    "shapes/intend-shapes-user.ttl",
    "shapes/intend-shapes-resource.ttl",
    "shapes/intend-shapes-application.ttl",
    "shapes/intend-shapes-workflow.ttl",
    "shapes/intend-shapes-fill-extension.ttl",
    "shapes/intend-shapes-telenor-extension.ttl",
    "shapes/intend-shapes-gate-extension.ttl",
    "examples/fill-catalog-data.ttl",
    "examples/fill-instance-data.ttl",
    "examples/telenor-network-data.ttl",
    "examples/gate-microservices-data.ttl",
    "everything.ttl",
]

PREFIX_RE = re.compile(r'^@prefix\s+([\w-]*):\s*<([^>]+)>\s*\.', re.MULTILINE)


def extract_prefixes(path):
    text = open(path, encoding="utf-8").read()
    return {m.group(1): m.group(2) for m in PREFIX_RE.finditer(text)}


def main():
    ok = True
    for rel in TTL_FILES:
        src = os.path.join(ROOT, rel)
        dst = os.path.join(ROOT, "jsonld", rel[:-4] + ".jsonld")
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        context = extract_prefixes(src)
        g = Graph()
        g.parse(src, format="turtle")

        out = g.serialize(format="json-ld", indent=2, context=context)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(out)

        # Round-trip verification: re-parse what we just wrote and compare
        # by graph isomorphism (not raw triple-set equality) since the
        # shapes files use blank nodes.
        g2 = Graph()
        g2.parse(dst, format="json-ld")
        same = isomorphic(_normalize_plain_strings(g), _normalize_plain_strings(g2))
        status = "OK" if same else "MISMATCH"
        if not same:
            ok = False
        print(f"  {status:8s} {rel:55s} -> jsonld/{rel[:-4]}.jsonld  ({len(g)} triples)")

    if not ok:
        print("\nOne or more files did NOT round-trip identically. Investigate before trusting jsonld/.")
        sys.exit(1)
    print("\nAll files round-trip identically (graph-isomorphic) between .ttl and generated .jsonld.")


if __name__ == "__main__":
    main()
