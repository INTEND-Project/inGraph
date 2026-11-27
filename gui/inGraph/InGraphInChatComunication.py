"""Send a JSON-LD knowledge graph to inChat (Onlim KG) from the command line.

Same logic as the API endpoint POST /inchat/sync (see inchat_sync.py): for each
node, DELETE it from the Onlim KG, import it again, then wait 10 seconds.

Credentials: INCHAT_API_KEY / INCHAT_PUBLISHER / INCHAT_DATASOURCE environment
variables, or a config.py next to this file (copy config.example.py; config.py
is gitignored). Without them the script refuses to send anything.

Usage:
    python InGraphInChatComunication.py KG/gateKG_fixed.jsonld --dry-run   # show what would be sent
    python InGraphInChatComunication.py KG/gateKG_fixed.jsonld             # send it
"""

import argparse
import json
import sys

import inchat_sync


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a JSON-LD KG to inChat (Onlim), node by node.")
    parser.add_argument("file", help="JSON-LD file: {'@context', '@graph'} document or array of nodes")
    parser.add_argument("--dry-run", action="store_true", help="only print what would be sent")
    args = parser.parse_args()

    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)
    elements, skipped = inchat_sync.prepare_elements(data)
    config, missing, sources = inchat_sync.load_config()

    for item in skipped:
        print(f"skipped node #{item['index']}: {item['reason']}")
    minutes = (len(elements) - 1) * inchat_sync.DELAY_SECONDS / 60 if elements else 0
    print(f"{len(elements)} nodes to send, ~{minutes:.0f} min with a {inchat_sync.DELAY_SECONDS} s pause between them")
    if not elements:
        return 1

    if args.dry_run:
        print(f"import URL: {inchat_sync.import_url(config)}")
        for element in elements:
            print(f"  {element['id']}\n    DELETE {inchat_sync.delete_url(config, element)}")
        print("first payload:")
        print(json.dumps(elements[0]["payload"], indent=2, ensure_ascii=False)[:2000])
        if missing:
            print(f"\nNOTE: not configured (missing {', '.join(missing)}): a real run would refuse to start.")
        return 0

    if missing:
        print(f"Not configured, nothing sent. Missing: {', '.join(missing)}. "
              "Set the environment variables or create config.py from config.example.py.", file=sys.stderr)
        return 1
    print("credentials from: " + ", ".join(f"{key}={source}" for key, source in sources.items()))

    job = inchat_sync.SyncJob(args.file, elements, skipped, config)

    def report(index, result):
        status = "ok" if result["ok"] else f"FAILED {json.dumps({k: v for k, v in result.items() if k not in ('id', 'ok')})}"
        print(f"[{index + 1}/{len(elements)}] {result['id']}: {status}", flush=True)

    try:
        job.run(on_result=report)
    except KeyboardInterrupt:
        print("\ninterrupted: the nodes already sent stay in inChat", file=sys.stderr)
        return 130

    summary = job.to_dict()
    print(f"\n{summary['state']}: {summary['succeeded']} ok, {summary['failed']} failed, "
          f"{len(summary['skipped'])} skipped")
    if summary["error"]:
        print(summary["error"], file=sys.stderr)
    return 0 if summary["state"] == "completed" and summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
