"""Push a JSON-LD knowledge graph to inChat's knowledge graph (Onlim API).

For every top-level node of the KG, in order:
  1. DELETE the node from the Onlim KG (so the new version replaces it, no merge);
  2. POST it to the Onlim import endpoint;
  3. wait DELAY_SECONDS before the next node.

This is the logic of the original InGraphInChatComunication.py script, made to
work with the KG files of this project:
  - accepts {"@context": ..., "@graph": [...]} documents (every KG in this repo)
    as well as a bare array of nodes (the format the original script expected);
  - sends each node together with the document's @context, so compact IRIs
    such as data:EC_3 still mean something on the Onlim side;
  - derives the namespace / local name for the DELETE call from each node's IRI
    (split at the last '#' or '/') instead of a namespace hard-coded to GATE.

Credentials are read, in this order, from the environment variables
INCHAT_API_KEY / INCHAT_PUBLISHER / INCHAT_DATASOURCE, or from the variables
API_KEY / PUBLISHER / DATASOURCE in a config.py next to this file (gitignored;
see config.example.py). Without all three, nothing is sent: callers check
load_config()'s `missing` list first.

Used by inGraphApp.py (POST /inchat/sync, run as a background job) and by the
command-line script InGraphInChatComunication.py.
"""

import importlib.util
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin

import requests

logger = logging.getLogger(__name__)

DEFAULT_API_BASE_URL = "https://proxy.onlim.com/api/ts/v1/kg/things"

# Pause between two nodes, as in the original script. Kept fixed on purpose:
# do not lower it without checking Onlim's rate limits first.
DELAY_SECONDS = 10

REQUEST_TIMEOUT_SECONDS = 60
MAX_KEPT_JOBS = 20

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")

# (key used in code, environment variable, variable name in config.py)
_SETTINGS = (
    ("api_key", "INCHAT_API_KEY", "API_KEY"),
    ("publisher", "INCHAT_PUBLISHER", "PUBLISHER"),
    ("datasource", "INCHAT_DATASOURCE", "DATASOURCE"),
)


class JobAlreadyRunning(Exception):
    """Raised when a sync is requested while another one is still running."""

    def __init__(self, job_id: str):
        super().__init__(f"An inChat sync is already running (job {job_id})")
        self.job_id = job_id


class CredentialsRejected(Exception):
    """Onlim answered 401/403: the credentials (or their permissions) are wrong,
    so every further request would fail the same way."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_config() -> Tuple[Dict[str, str], List[str], Dict[str, str]]:
    """Return (config, missing, sources).

    config  -- api_key / publisher / datasource that are set, plus api_base_url
    missing -- environment variable names of the settings that are not set
    sources -- for each setting that is set, where it came from: "env" or "config.py"

    Read on every call, so creating config.py or changing it needs no restart.
    Never log or return the values themselves outside this module's callers.
    """
    file_values: Dict[str, Any] = {}
    if os.path.isfile(CONFIG_FILE):
        try:
            spec = importlib.util.spec_from_file_location("inchat_local_config", CONFIG_FILE)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            file_values = {name: getattr(module, name, "") for _, _, name in _SETTINGS}
        except Exception as e:  # a broken config.py must not take the app down
            logger.warning(f"Could not read {CONFIG_FILE}: {e}")

    config: Dict[str, str] = {}
    missing: List[str] = []
    sources: Dict[str, str] = {}
    for key, env_name, file_name in _SETTINGS:
        value = (os.getenv(env_name) or "").strip()
        source = "env"
        if not value:
            value = str(file_values.get(file_name) or "").strip()
            source = "config.py"
        if value:
            config[key] = value
            sources[key] = source
        else:
            missing.append(env_name)

    config["api_base_url"] = (os.getenv("INCHAT_API_BASE_URL") or DEFAULT_API_BASE_URL).rstrip("/")
    return config, missing, sources


# ---------------------------------------------------------------------------
# Turning a JSON-LD document into the list of nodes to send
# ---------------------------------------------------------------------------

def _context_dict(context: Any) -> Dict[str, Any]:
    """Merge the object parts of a JSON-LD @context (dict, or list of dicts and
    remote-context URLs) into one dict. Remote contexts are not fetched."""
    if isinstance(context, dict):
        return dict(context)
    merged: Dict[str, Any] = {}
    if isinstance(context, list):
        for part in context:
            if isinstance(part, dict):
                merged.update(part)
    return merged


def _id_keys(context: Dict[str, Any]) -> List[str]:
    """"@id" plus any alias of it declared in the context (e.g. "id": "@id")."""
    return ["@id"] + [key for key, value in context.items() if value == "@id"]


def _expand_iri(value: Any, context: Dict[str, Any]) -> Optional[str]:
    """Expand a node identifier to a full IRI. Returns None for blank nodes."""
    if not isinstance(value, str) or not value or value.startswith("_:"):
        return None
    if ":" in value:
        prefix, _, suffix = value.partition(":")
        if not suffix.startswith("//"):
            mapping = context.get(prefix)
            if isinstance(mapping, dict):
                mapping = mapping.get("@id")
            if isinstance(mapping, str):
                return mapping + suffix
        return value  # already absolute: http(s)://..., urn:..., ...
    base = context.get("@base")
    return urljoin(base, value) if isinstance(base, str) else value


def _split_iri(iri: str) -> Tuple[str, str]:
    """Split an IRI into (namespace, local name) at its last '#' or '/'."""
    cut = max(iri.rfind("#"), iri.rfind("/"))
    if cut == -1:
        return "", iri
    return iri[:cut + 1], iri[cut + 1:]


def _blank_id(node: Any, id_keys: List[str]) -> Optional[str]:
    if isinstance(node, dict):
        for key in id_keys:
            value = node.get(key)
            if isinstance(value, str) and value.startswith("_:"):
                return value
    return None


def _embed_blank_nodes(value: Any, blank_nodes: Dict[str, Dict[str, Any]], id_keys: List[str],
                       used: set, stack: Tuple[str, ...] = ()) -> Any:
    """Return a copy of `value` where every reference to a top-level blank node
    ({"@id": "_:x"}) is replaced by that node's content, recursively."""
    if isinstance(value, list):
        return [_embed_blank_nodes(item, blank_nodes, id_keys, used, stack) for item in value]
    if not isinstance(value, dict):
        return value
    ref = _blank_id(value, id_keys)
    if ref in blank_nodes and len(value) == 1 and ref not in stack:
        used.add(ref)
        target = {k: v for k, v in blank_nodes[ref].items() if k not in id_keys}
        return _embed_blank_nodes(target, blank_nodes, id_keys, used, stack + (ref,))
    return {k: (v if k == "@context" else _embed_blank_nodes(v, blank_nodes, id_keys, used, stack))
            for k, v in value.items()}


def prepare_elements(data: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Turn a parsed JSON-LD document into the nodes to send.

    Returns (elements, skipped). Each element is
      {"id": full IRI, "namespace": ..., "local_name": ..., "payload": [node]}
    where payload is exactly what is POSTed to the import endpoint.

    Blank nodes that a serializer put at the top level (e.g. the Turtle
    `[ a tio:Expectation ; ... ]` of the FILL intents) are embedded into the
    node that references them: blank node labels only mean something inside
    one document, so a reference to one could not survive being sent in a
    separate request. A blank node referenced by several nodes is copied into
    each. Nodes that cannot be sent on their own (blank nodes nobody
    references, IRIs without a local name) are listed in `skipped` with the
    reason, and not sent at all.

    Raises ValueError if the document is not a JSON-LD object or array.
    """
    if isinstance(data, list):
        nodes, top_context = data, None
    elif isinstance(data, dict) and "@graph" in data:
        nodes, top_context = data["@graph"], data.get("@context")
    elif isinstance(data, dict):
        nodes, top_context = [data], None  # a single node, keeping its own @context
    else:
        raise ValueError("Expected a JSON-LD object or an array of nodes")
    if isinstance(nodes, dict):
        nodes = [nodes]
    if not isinstance(nodes, list):
        raise ValueError("@graph must be an array of nodes")

    base_context = _context_dict(top_context)
    id_keys = _id_keys(base_context)
    blank_nodes = {_blank_id(node, id_keys): node for node in nodes if _blank_id(node, id_keys)}
    used_blank_nodes: set = set()
    elements: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    unidentified: List[int] = []

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            skipped.append({"index": index, "reason": "not a JSON object"})
            continue

        context = dict(base_context)
        context.update(_context_dict(node.get("@context")))
        raw_id = next((node[key] for key in _id_keys(context) if key in node), None)
        iri = _expand_iri(raw_id, context)
        if iri is None:
            unidentified.append(index)  # decided after the loop: it may get embedded
            continue

        namespace, local_name = _split_iri(iri)
        if not namespace or not local_name:
            skipped.append({"index": index, "id": iri,
                            "reason": "cannot split the IRI into namespace and local name for the DELETE call"})
            continue

        node = _embed_blank_nodes(node, blank_nodes, id_keys, used_blank_nodes)
        if top_context is not None and "@context" not in node:
            payload_node = {"@context": top_context, **node}
        else:
            payload_node = node
        elements.append({"id": iri, "namespace": namespace, "local_name": local_name,
                         "payload": [payload_node]})

    for index in unidentified:
        if _blank_id(nodes[index], id_keys) not in used_blank_nodes:
            skipped.append({"index": index, "reason": "node without an IRI that no other node references: "
                                                      "it cannot be deleted before re-import, so it is not sent"})
    skipped.sort(key=lambda item: item["index"])
    return elements, skipped


# ---------------------------------------------------------------------------
# Onlim API calls
# ---------------------------------------------------------------------------

def delete_request_parts(config: Dict[str, str], element: Dict[str, Any]) -> Tuple[str, Dict[str, str]]:
    """URL and query parameters of the DELETE call for one element."""
    url = f"{config['api_base_url']}/{quote(element['local_name'], safe='')}"
    params = {"ns": element["namespace"], "dryRun": "false", "force": "true"}
    return url, params


def delete_url(config: Dict[str, str], element: Dict[str, Any]) -> str:
    """Full DELETE URL (query string encoded), for previews and logs."""
    url, params = delete_request_parts(config, element)
    return requests.Request("DELETE", url, params=params).prepare().url


def import_url(config: Dict[str, str]) -> str:
    return f"{config['api_base_url']}/imports"


def _short(text: str, limit: int = 500) -> str:
    return text if len(text) <= limit else text[:limit] + "..."


def sync_element(session: requests.Session, config: Dict[str, str], element: Dict[str, Any]) -> Dict[str, Any]:
    """Delete then re-import one element. Returns a result record.

    A 404 on DELETE is fine (the node is not in inChat yet). As in the original
    script, the import is attempted even if the DELETE failed.
    Raises CredentialsRejected on 401/403 from either call; network errors
    (requests.RequestException) are left to the caller.
    """
    result: Dict[str, Any] = {"id": element["id"], "ok": False}

    url, params = delete_request_parts(config, element)
    response = session.delete(url, params=params, headers={"x-api-key": config["api_key"]},
                              timeout=REQUEST_TIMEOUT_SECONDS)
    result["delete_status"] = response.status_code
    if response.status_code in (401, 403):
        raise CredentialsRejected(f"DELETE answered {response.status_code}: {_short(response.text)}")
    delete_ok = response.status_code in (200, 202, 204, 404)
    if not delete_ok:
        result["delete_error"] = _short(response.text)

    response = session.post(
        import_url(config),
        headers={
            "x-api-key": config["api_key"],
            "x-publisher": config["publisher"],
            "x-datasource": config["datasource"],
            "Content-Type": "application/ld+json",
        },
        json=element["payload"],
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    result["import_status"] = response.status_code
    if response.status_code in (401, 403):
        raise CredentialsRejected(f"Import answered {response.status_code}: {_short(response.text)}")
    if response.status_code in (200, 201):
        result["ok"] = delete_ok
    else:
        result["import_error"] = _short(response.text)
    return result


# ---------------------------------------------------------------------------
# Sync jobs
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SyncJob:
    """One run over a list of prepared elements. run() blocks; the web API runs
    it in a background thread, the command-line script in the foreground."""

    def __init__(self, filename: str, elements: List[Dict[str, Any]],
                 skipped: List[Dict[str, Any]], config: Dict[str, str]):
        self.id = uuid.uuid4().hex[:12]
        self.filename = filename
        self.elements = elements
        self.skipped = skipped
        self._config = config
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self.state = "queued"  # queued | running | cancelling | completed | cancelled | failed
        self.processed = 0
        self.succeeded = 0
        self.failed = 0
        self.current: Optional[str] = None
        self.errors: List[Dict[str, Any]] = []
        self.error: Optional[str] = None
        self.created_at = _now()
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None

    @property
    def active(self) -> bool:
        return self.state in ("queued", "running", "cancelling")

    def cancel(self) -> None:
        """Ask the job to stop. It finishes the element in progress (if any) and stops."""
        with self._lock:
            if self.active:
                self.state = "cancelling"
                self._cancel.set()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self.elements)
            remaining = total - self.processed
            return {
                "job_id": self.id,
                "state": self.state,
                "filename": self.filename,
                "total_elements": total,
                "processed": self.processed,
                "succeeded": self.succeeded,
                "failed": self.failed,
                "skipped": self.skipped,
                "current_element": self.current if self.active else None,
                "delay_seconds": DELAY_SECONDS,
                "estimated_remaining_seconds": max(remaining - 1, 0) * DELAY_SECONDS if self.active else 0,
                "created_at": self.created_at,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "error": self.error,
                "errors": list(self.errors),
            }

    def run(self, on_result: Optional[Callable[[int, Dict[str, Any]], None]] = None) -> None:
        with self._lock:
            if self._cancel.is_set():
                self.state = "cancelled"
                self.finished_at = _now()
                return
            self.state = "running"
            self.started_at = _now()

        session = requests.Session()
        last = len(self.elements) - 1
        try:
            for index, element in enumerate(self.elements):
                if self._cancel.is_set():
                    break
                with self._lock:
                    self.current = element["id"]

                try:
                    result = sync_element(session, self._config, element)
                except requests.RequestException as e:
                    result = {"id": element["id"], "ok": False, "network_error": str(e)}

                with self._lock:
                    self.processed += 1
                    if result["ok"]:
                        self.succeeded += 1
                    else:
                        self.failed += 1
                        self.errors.append(result)
                logger.info(f"inChat sync {self.id}: {index + 1}/{last + 1} {element['id']} "
                            f"-> {'ok' if result['ok'] else 'FAILED'}")
                if on_result:
                    on_result(index, result)

                if index < last and self._cancel.wait(DELAY_SECONDS):
                    break

            with self._lock:
                self.state = "cancelled" if self._cancel.is_set() else "completed"
        except CredentialsRejected as e:
            with self._lock:
                self.state = "failed"
                self.error = f"Onlim rejected the credentials or their permissions, stopped: {e}"
        except Exception as e:  # never let a background thread die silently
            logger.exception(f"inChat sync {self.id} crashed")
            with self._lock:
                self.state = "failed"
                self.error = f"Unexpected error, stopped: {e}"
        finally:
            with self._lock:
                self.current = None
                self.finished_at = _now()
            session.close()


class JobManager:
    """In-memory registry of sync jobs, at most one running at a time (so the
    DELAY_SECONDS pause actually limits the request rate towards Onlim).
    Jobs live in this process only: an app restart, or a Flask debug reload,
    loses them, and a running job stops with the process."""

    def __init__(self):
        self._jobs: Dict[str, SyncJob] = {}
        self._lock = threading.Lock()

    def start(self, filename: str, elements: List[Dict[str, Any]],
              skipped: List[Dict[str, Any]], config: Dict[str, str]) -> SyncJob:
        with self._lock:
            running = self._active_job()
            if running:
                raise JobAlreadyRunning(running.id)
            job = SyncJob(filename, elements, skipped, config)
            self._jobs[job.id] = job
            for old_id in list(self._jobs)[:-MAX_KEPT_JOBS]:
                if not self._jobs[old_id].active:
                    del self._jobs[old_id]
        threading.Thread(target=job.run, name=f"inchat-sync-{job.id}", daemon=True).start()
        return job

    def get(self, job_id: str) -> Optional[SyncJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def _active_job(self) -> Optional[SyncJob]:
        return next((job for job in self._jobs.values() if job.active), None)

    def active_job_id(self) -> Optional[str]:
        with self._lock:
            job = self._active_job()
            return job.id if job else None

    def summaries(self) -> List[Dict[str, Any]]:
        with self._lock:
            jobs = list(self._jobs.values())
        return [{key: job.to_dict()[key] for key in
                 ("job_id", "state", "filename", "total_elements", "processed", "succeeded", "failed",
                  "created_at", "finished_at")}
                for job in reversed(jobs)]
