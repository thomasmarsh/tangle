"""Bounded, read-only help for the single ``tangle`` command.

Two layers keep the skill's guidance discoverable without loading all of it:

- Per-verb help states the operands, output fields, exit meanings, and
  command-specific hazards the verb owns. It needs no vault and no sidecar, so
  an agent can ask before acting.
- Topical help renders one installed Markdown reference. The reference files
  under ``references/`` are the canonical prose; this module locates and prints
  them instead of duplicating their text in Python strings.

The command and topic index stays in :func:`tangle.main._print_usage`; this
module is the bounded detail behind it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .toon import field, table

__all__ = [
    "REFERENCE_DIRECTORY",
    "REFERENCE_TOPICS",
    "TOPIC_PURPOSES",
    "help_command",
    "render_verb",
    "topic_rows",
    "verb_key",
    "wants_help",
]

# The directory name is installed beside ``SKILL.md`` at the same revision as
# the command, so a rendered topic always matches the installed revision.
REFERENCE_DIRECTORY = "references"

# Ordering places the opt-in asynchronous protocol before the existing
# coordination, dependency, and authoring details.
REFERENCE_TOPICS: tuple[str, ...] = (
    "change-intake",
    "coordination",
    "dependencies",
    "authoring",
)

TOPIC_PURPOSES: dict[str, str] = {
    "change-intake": "sealed proposals, reconciliation, acceptance, recovery",
    "coordination": "claims, leases, parallel worktrees, handoff, integration",
    "dependencies": "pins, gates, revision bumps, staged staleness, reversals",
    "authoring": "node bodies, capture commands, feedback nodes, decomposition",
}

# A help request never reaches a command body, so it is safe to detect it from
# the raw arguments before dispatch.
_HELP_FLAGS = frozenset({"-h", "--help"})

# Commands whose second token names a subcommand with its own help entry.
_GROUP_COMMANDS = frozenset({"node", "feedback", "semantic", "benchmark", "project"})


@dataclass(frozen=True)
class Verb:
    """The bounded help one public verb publishes."""

    usage: str
    purpose: str
    operands: tuple[tuple[str, str], ...] = ()
    outputs: tuple[tuple[str, str], ...] = ()
    exits: tuple[tuple[str, str], ...] = ()
    hazards: tuple[str, ...] = ()
    topic: str = ""


_EXITS = (
    ("0", "the answer was produced"),
    ("1", "the request could not be answered (missing node, absent vault, findings)"),
    ("2", "the command line is malformed"),
)

_COORDINATION_TOPIC = "coordination"
_DEPENDENCIES_TOPIC = "dependencies"
_AUTHORING_TOPIC = "authoring"

# The four read-only graph-question verbs share one pre-check: an unfinished node
# that cannot reach a hub is warned about on stderr before the verb answers.
_ORPHAN_WARNING_HAZARD = (
    "An orphaned unfinished node is warned about on stderr; the answer and exit "
    "code are unchanged."
)


def _verb(
    purpose: str,
    *,
    operands: tuple[tuple[str, str], ...] = (),
    outputs: tuple[tuple[str, str], ...] = (),
    hazards: tuple[str, ...] = (),
    topic: str = "",
    usage: str,
) -> Verb:
    return Verb(
        usage=usage,
        purpose=purpose,
        operands=operands,
        outputs=outputs,
        exits=_EXITS,
        hazards=hazards,
        topic=topic,
    )


VERBS: dict[str, Verb] = {
    "status": _verb(
        "Show the current coordination state for this project.",
        usage="tangle status",
        outputs=(
            ("project_id", "stable identity shared by every worktree"),
            ("sidecar", "absolute path of the local coordination state"),
            ("initialized", "whether that state exists"),
            ("active_claims", "leases currently recorded"),
            ("views", "generated page state: current, stale, or unavailable"),
            ("reservations", "prefix,next rows for allocated ids"),
        ),
        hazards=(
            "Reports state only; it never writes or repairs the local state.",
            _ORPHAN_WARNING_HAZARD,
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "location": _verb(
        "Show the stable project identity and state path.",
        usage="tangle location",
        outputs=(
            ("project_uid", "committed clone-stable project identity"),
            ("project_id", "local coordination key derived from the Git common directory"),
            ("sidecar", "absolute path of the local coordination state"),
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "init": _verb(
        "Create or repair the local coordination state.",
        usage="tangle init",
        operands=(
            ("(none)", "run from the project root; the location is derived"),
        ),
        outputs=(
            ("result", "always initialized"),
            ("project_id", "stable identity"),
            ("sidecar", "local state path created or repaired"),
        ),
        hazards=(
            "Rebuilds only derived state; never repair the local state by hand.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "migrate": _verb(
        "Rename a legacy nodes/ vault to .tangle/ in place.",
        usage="tangle migrate [ROOT]",
        operands=(
            ("ROOT", "project root holding the vault; defaults to the current directory"),
        ),
        outputs=(
            ("result", "migrated or no-op"),
            ("source/destination", "the rename when it happened"),
        ),
        hazards=(
            "Runs only when nodes/index-map.md exists and .tangle/ does not.",
            "Idempotent in-place rename; it never rewrites Markdown or the local state.",
        ),
        topic=_AUTHORING_TOPIC,
    ),
    "stationarize": _verb(
        "Move legacy status-directory nodes into the stationary canonical store.",
        usage="tangle stationarize [NODES] [--apply]",
        operands=(
            ("NODES", "vault directory; defaults to ./.tangle"),
            ("--apply", "perform the planned moves; default is a read-only plan"),
        ),
        outputs=(
            ("result", "planned, migrated, or no-op"),
            ("moves", "id,status,source,target rows for a plan"),
            ("moved/project_uid", "the applied move count and committed authority"),
        ),
        hazards=(
            "The default is a read-only plan; only --apply writes or moves files.",
            "Preserves identity, basename, and wikilinks; every plan is "
            "collision-checked before any write.",
            "A failed apply rolls every completed move back to its original bytes.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "allocate": _verb(
        "Atomically reserve PREFIX-NNN across worktrees.",
        usage="tangle allocate PREFIX [COUNT]",
        operands=(
            ("PREFIX", "uppercase letters, digits, underscores, or hyphens"),
            ("COUNT", "positive number of consecutive ids; default 1, no upper bound"),
        ),
        outputs=(
            ("id", "the reserved identity, for example TAS-106"),
            ("ids", "one row per reserved id when COUNT is greater than 1"),
        ),
        hazards=(
            "A reservation is not a node; a local find is collision detection only.",
            "New canonical ids come from entropy and need no reservation.",
            "A discarded allocation is burned permanently and never reused.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "reservations": _verb(
        "List allocated id prefixes and the burned ids no node uses.",
        usage="tangle reservations",
        outputs=(
            ("reservations", "prefix,next,burned rows for allocated ids"),
        ),
        hazards=(
            "Read-only; it writes no state and needs no local state.",
            "A burned id was allocated and discarded, so it is not a missing node.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "claim": _verb(
        "Acquire or renew an exclusive lease on one node.",
        usage="tangle claim NODE AGENT --base-hash HASH [--lease-seconds N]",
        operands=(
            ("NODE", "bare ID or full node name; a path is rejected"),
            ("AGENT", "claim owner; a repeat with the same hash renews"),
            ("--base-hash", "the bare 64-character content_hash digest"),
            ("--lease-seconds", "lease duration; default 900"),
        ),
        outputs=(
            ("result", "always claimed"),
            ("node", "the opaque claim key"),
            ("agent", "the recorded owner"),
            ("base_hash", "the recorded starting digest"),
            ("lease_expires_at", "absolute expiry"),
            ("lease_remaining_seconds", "seconds left on this call"),
        ),
        hazards=(
            "Never pass the two-line node:/content_hash: block; pass the bare digest.",
            "The frontier move belongs to the claimed edit, not the handoff.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "release": _verb(
        "Release the matching lease or report that it lapsed.",
        usage="tangle release NODE AGENT --base-hash HASH",
        operands=(
            ("NODE", "the same bare ID or full node name used to claim"),
            ("AGENT", "the recorded owner"),
            ("--base-hash", "the starting digest recorded by claim"),
        ),
        outputs=(
            ("result", "released, expired, or no-op"),
            ("node", "the claim key"),
            ("lease_remaining_seconds", "seconds left, or 0"),
        ),
        hazards=(
            "A hash or owner mismatch fails non-zero and refuses the release.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "index": _verb(
        "Repair or rebuild the derived index from Markdown.",
        usage="tangle index [NODES]",
        operands=(("NODES", "vault directory; defaults to ./.tangle"),),
        outputs=(
            ("nodes", "node rows indexed"),
            ("edges", "graph edges indexed"),
            ("root", "absolute nodes directory indexed"),
            ("views", "generated pages current or the count republished"),
        ),
        hazards=(
            "The index maintains itself on every interaction; run this only to "
            "repair or rebuild it.",
            "Also republishes the disposable Markdown views under views/.",
            "Derived state only; Markdown remains authoritative.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "search": _verb(
        "Full-text search derived Markdown content.",
        usage=(
            "tangle search QUERY [--limit N] [--status S] [--type T] "
            "[--priority P] [--parent REF] [--dependency REF]"
        ),
        operands=(
            ("QUERY", "search text"),
            ("--limit", "maximum rows; default 20"),
            ("--status", "proposed, active, blocked, or resolved"),
            ("--type", "uppercase type prefix such as TAS or DEF"),
            ("--priority", "P0 through P3"),
            ("--parent / --dependency", "filter by a stored relation target"),
        ),
        outputs=(
            ("nodes", "id,status,summary rows, or an explicit zero line"),
        ),
        hazards=("Updates the derived index first; filters read Markdown.",),
        topic=_COORDINATION_TOPIC,
    ),
    "similar": _verb(
        "Rank nodes by lexical similarity.",
        usage="tangle similar TEXT|--file PATH [--limit N]",
        operands=(
            ("TEXT", "query text, or"),
            ("--file", "UTF-8 file to read the query from"),
            ("--limit", "maximum rows; default 10"),
        ),
        outputs=(
            ("similar", "id,status,score,summary rows"),
        ),
        hazards=(
            "Never both TEXT and --file; the optional provider reranks when healthy.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "backlinks": _verb(
        "List derived incoming graph edges for one node.",
        usage="tangle backlinks NODE",
        operands=(("NODE", "bare ID or full node name"),),
        outputs=(
            ("backlinks", "source,status,relation,pinned_context_rev rows"),
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "hash": _verb(
        "Print the raw-content SHA-256 of a node file.",
        usage="tangle hash NODE",
        operands=(("NODE", "bare ID or full node name; a path is rejected"),),
        outputs=(
            ("node", "the operand echoed"),
            ("content_hash", "bare digest to pass as --base-hash"),
        ),
        hazards=(
            "Frontmatter is included; use the bare digest, never the labelled block.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "stale": _verb(
        "Find missing or outdated dependency pins.",
        usage="tangle stale",
        outputs=(
            ("stale", "source,status,target,pinned,current,relation,reason rows"),
        ),
        hazards=("Read-only diagnosis; reconcile each consumer deliberately.",),
        topic=_DEPENDENCIES_TOPIC,
    ),
    "frontier": _verb(
        "List frontier candidates, optionally clustered into advisory groups.",
        usage="tangle frontier [--group] [--limit N]",
        operands=(
            ("--group", "cluster candidates into advisory workstreams"),
            ("--limit", "maximum rows; requires --group"),
        ),
        outputs=(
            ("frontier", "id,status,priority,summary,next,stale rows"),
            ("frontier_groups", "grouped rows with the same fields"),
            ("advisory", "states that groups are not work claims"),
        ),
        hazards=(
            "Candidates are a superset of the frontier; resolve them through the coordinator.",
            _ORPHAN_WARNING_HAZARD,
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "node": _verb(
        "Show one node's frontmatter, route, edges, and backlinks.",
        usage="tangle node NODE",
        operands=(("NODE", "bare ID or full node name"),),
        outputs=(
            ("node/name/status/path", "identity and location"),
            ("frontmatter", "key,value rows"),
            ("route_relation/route", "primary Parent or Area edge"),
            ("context_edges", "relation,target,pinned,current,status,stale rows"),
            ("backlinks", "incoming edges"),
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "node record": _verb(
        "Create one routed, stamped node of a named type.",
        usage="tangle node record --type T --summary S --body B [OPTIONS]",
        operands=(
            ("--type", "THO, DEF, DEC, or TAS"),
            ("--summary", "frontmatter summary; one line of at most 96 characters"),
            ("--body", "node body text"),
            ("--status", "authoritative status field; defaults to proposed"),
            ("--next", "required for an unfinished TAS; omitted when resolved"),
            ("--route/--id/--slug/--nodes", "route and id overrides"),
        ),
        outputs=(
            ("path", "the written stationary node file"),
            ("id", "the generated lowercase identity"),
            ("warning", "present when an over-long summary was shortened"),
        ),
        hazards=(
            "Creates the node you already decided to admit; it does not judge admission.",
            "Generates the id from cryptographic entropy before writing the file.",
            "An over-long --summary is cut on a word boundary with a trailing "
            "... and warned about, never stored mid-phrase.",
        ),
        topic=_AUTHORING_TOPIC,
    ),
    "node decompose": _verb(
        "Write ordered direct children and advance the parent atomically.",
        usage="tangle node decompose --parent P --plan F [--nodes DIR] [--dry-run]",
        operands=(
            ("--parent", "existing unfinished node that becomes the children's route"),
            ("--plan", "JSON file with a non-empty children list"),
            ("--nodes", "vault directory override"),
            ("--dry-run", "validate and print the plan without writing or reserving"),
        ),
        outputs=(
            ("parent/next", "the parent and the first child it now routes to"),
            ("children", "id,status,filename rows for the children written"),
        ),
        hazards=(
            "Validates every child before generating an id or writing a file.",
            "A write failure removes the children already written and leaves the "
            "parent unchanged.",
            "The parent's # Done when and body are never rewritten; only its "
            "next and updated change.",
        ),
        topic=_AUTHORING_TOPIC,
    ),
    "node advance": _verb(
        "Advance one coordinating parent's next to a direct child.",
        usage="tangle node advance PARENT CHILD [--nodes DIR]",
        operands=(
            ("PARENT", "unfinished coordinating node"),
            ("CHILD", "direct child whose Parent route names PARENT"),
        ),
        outputs=(
            ("parent/next", "the parent and the child it now routes to"),
        ),
        hazards=(
            "Edits only the parent's next and updated lines; the child is unchanged.",
            "Refuses a child whose Parent route does not name PARENT.",
        ),
        topic=_AUTHORING_TOPIC,
    ),
    "node references": _verb(
        "Show one node with the reconnaissance it directly references.",
        usage="tangle node references NODE",
        operands=(("NODE", "bare ID or full node name"),),
        outputs=(
            ("node/name/status/path/summary", "identity and location"),
            ("route_relation/route", "primary Parent or Area edge"),
            ("references", "id,status,context_rev,summary rows for direct references"),
        ),
        hazards=(
            "Expands exactly one hop, so reference cycles terminate and output "
            "is bounded by the node's direct references.",
            "A reference with no target is reported as status missing; the "
            "structural failure is `tangle check`'s node-broken-link.",
            "The relation is non-pinned and changes no readiness, staleness, or "
            "routing answer.",
        ),
        topic=_AUTHORING_TOPIC,
    ),
    "impact": _verb(
        "List direct and transitive dependents of a node.",
        usage="tangle impact NODE",
        operands=(("NODE", "bare ID or full node name"),),
        outputs=(
            ("target/target_context_rev", "the resolved node and revision"),
            ("impact", "dependent,status,depth,relation,dependency,... rows"),
        ),
        hazards=("Traverses the whole chain; do not repeat it via backlinks.",),
        topic=_DEPENDENCIES_TOPIC,
    ),
    "orient": _verb(
        "Print a bounded orientation packet over the graph.",
        usage="tangle orient [--section NAME] [--limit N]",
        operands=(
            ("--section", "named packet section; repeatable"),
            ("--limit", "maximum rows per section; default 10"),
        ),
        outputs=(
            ("section/total", "per-section header and row count"),
            ("rows", "each section's documented columns"),
        ),
        hazards=(_ORPHAN_WARNING_HAZARD,),
        topic=_COORDINATION_TOPIC,
    ),
    "packet": _verb(
        "Print the one executable frontier node and its minimal context.",
        usage="tangle packet [NODE]",
        operands=(
            (
                "NODE",
                "optional bare ID or full node name; scopes the answer to that "
                "node's own next route",
            ),
        ),
        outputs=(
            ("result", "ready, blocked, ambiguous, or invalid"),
            ("id/name/path/status/summary/next", "the one routed node when ready"),
            ("route", "parent,relation,child rows from the root hub to the node"),
            ("dependencies", "relation,target,pinned,current,status,stale rows"),
            ("files", "kind,path,state rows; the node path plus manifest source/test entries"),
            ("verification", "gate rows; the required final gates plus manifest verify entries"),
            ("compat", "constraint rows; manifest compatibility entries"),
            ("record", "the operation that records progress on the node"),
            ("criteria", "criterion rows; the node's # Done when completion criteria"),
            ("terminals", "node,status,reason,summary,route,path rows when blocked"),
            ("candidates", "id,status,summary,next,route rows when ambiguous"),
            ("problems", "code,node,detail rows when invalid"),
        ),
        hazards=(
            "Read-only and strict: it selects no route heuristically, so more than one "
            "executable route is ambiguous and a structural failure is invalid.",
            "A NODE operand that resolves to no node is invalid with a scope-missing "
            "problem, never a silent whole-vault answer.",
            "A manifest source or test path that does not exist yet is absent intent, "
            "not a failure; a node with no # Manifest keeps its own path as the only file.",
            "A node with no # Done when reports zero criteria; a longer list is bounded "
            "and reports the overage explicitly.",
            "Exits 0 only for ready; blocked, ambiguous, and invalid exit 1.",
            _ORPHAN_WARNING_HAZARD,
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "manifest": _verb(
        "Print one node's authored execution surfaces and their resolution.",
        usage="tangle manifest NODE",
        operands=(("NODE", "bare ID or full node name"),),
        outputs=(
            ("result", "ready, empty, or invalid"),
            ("id/name/status", "the resolved node"),
            ("authored", "kind,value rows: source, test, verify, or compat"),
            ("derived", "kind,value,state,detail rows resolving each entry"),
            ("problems", "code,node,detail rows when an entry is malformed"),
        ),
        hazards=(
            "Read-only; a declared source or test path that does not exist is "
            "intent, reported as absent rather than as a failure.",
            "A node with no # Manifest section is empty, not invalid.",
        ),
        topic=_AUTHORING_TOPIC,
    ),
    "next": _verb(
        "Rank frontier candidates for the next actor.",
        usage="tangle next [--rank] [--limit N]",
        operands=(
            ("--rank", "accepted; ranking is the only mode"),
            ("--limit", "maximum rows; default 5"),
        ),
        outputs=(
            ("ranking", "the documented ordering rule"),
            ("total", "candidate count"),
            ("next", "rank,id,status,priority,blocking,updated,summary,next rows"),
        ),
        hazards=(
            "Candidates are advisory; the coordinator's next route resolves them.",
            _ORPHAN_WARNING_HAZARD,
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "clusters": _verb(
        "List advisory clusters, over-broad routes, and outlier nodes.",
        usage="tangle clusters [--limit N]",
        operands=(("--limit", "maximum rows per answer; default 10"),),
        outputs=(
            ("advisory", "states the answer is not a work claim"),
            ("space/method/params/stability", "the chosen fit and its evidence"),
            ("clusters/noise/outliers", "bounded member rows"),
        ),
        hazards=(
            "Needs the optional semantic capability; without it, one advisory line and exit 0.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "digest": _verb(
        "Digest one hub's or node's unresolved direct members.",
        usage="tangle digest NODE [--limit N]",
        operands=(
            ("NODE", "bare ID or full node name"),
            ("--limit", "maximum rows; default 20"),
        ),
        outputs=(
            ("target/status/total", "the resolved node and member count"),
            ("members", "id,status,priority,updated,summary,next rows"),
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "reconcile": _verb(
        "Plan duplicate, divergence, and stale-pin repairs from a Git change set.",
        usage="tangle reconcile [--base REF] [--head REF ...] [NODES]",
        operands=(
            ("--base", "comparison base; defaults to HEAD"),
            ("--head", "a ref to include; repeatable"),
            ("NODES", "vault directory; defaults to ./.tangle"),
        ),
        outputs=(
            ("base", "the resolved base ref"),
            ("head", "the refs compared"),
            ("steps", "action,depth,node,path,pinned,current,detail rows"),
        ),
        hazards=(
            "Plans repairs only; run inside the vault's Git repository.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "check": _verb(
        "Validate the vault; a legacy nodes/ layout is migrated first.",
        usage=(
            "tangle check [--allow-stale] [--allow-orphan NODE] "
            "[--allow-pending-advance NODE] [--format text|toon] [NODES]"
        ),
        operands=(
            ("--allow-stale", "relax only the revision equality of a pin"),
            ("--allow-orphan", "permit one named orphan; repeatable"),
            (
                "--allow-pending-advance",
                "permit one named parent-next advance a handoff still owes; repeatable",
            ),
            ("--format", "text diagnostics or the toon findings table"),
            ("NODES", "vault directory; defaults to ./.tangle"),
        ),
        outputs=(
            ("findings", "code,node,detail rows in toon format"),
            ("graph check", "a pass line with the node count in text format"),
        ),
        hazards=(
            "--allow-stale is sanctioned only for a deliberate staged-staleness commit.",
            "A pinned dependency to an unresolved target still fails.",
            "--allow-pending-advance sanctions a declared pending advance; "
            "the plain gate clears it.",
        ),
        topic=_AUTHORING_TOPIC,
    ),
    "external": _verb(
        "List durable cross-project references and their resolution state.",
        usage="tangle external [--unresolved]",
        operands=(
            (
                "--unresolved",
                "list only references whose target project cannot be resolved",
            ),
        ),
        outputs=(
            ("root", "absolute vault directory the references were read from"),
            ("unresolved", "how many references are not resolvable locally"),
            (
                "references",
                "source, project, node, alias, state, and detail rows",
            ),
        ),
        hazards=(
            "A canonical node cites an external target only as a bare "
            "tangle://<prj-uid>/node/<node-id> URI, never an Obsidian wikilink.",
            "An unregistered or unavailable project leaves the reference "
            "visible and unresolved; no local node is ever created for it.",
            "Read-only: it reports state and creates no canonical Markdown.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "census": _verb(
        "Report the last canonical-store hash census and the generated-view state.",
        usage="tangle census",
        outputs=(
            ("census", "reconciled, uninitialized, unavailable, busy, or failed"),
            ("root", "absolute vault directory the census read"),
            ("changes", "canonical node files the census found new or changed"),
            ("edges", "edge rows the reconciliation rewrote"),
            ("removed", "vanished node rows the reconciliation deleted"),
            ("views", "generated page state: current, updated N, failed, or unavailable"),
        ),
        hazards=(
            "A vault with no local state is reported without creating any.",
            "Hashes every canonical file's exact bytes, so a preserved-mtime "
            "edit is still detected; mtime and size are never a substitute.",
            "Republishes the disposable views from the reconciled snapshot; "
            "canonical Markdown is never written.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "project": _verb(
        "Register external projects for cross-project references.",
        usage="tangle project register ALIAS UID [--path PATH]",
        outputs=(
            ("registry", "the local projects.json the registration updated"),
        ),
        hazards=(
            "The registry is local state, excluded from canonical Markdown and Git.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "project register": _verb(
        "Register a lowercase alias for an external project UID and local vault.",
        usage="tangle project register ALIAS UID [--path PATH]",
        operands=(
            ("ALIAS", "lowercase letters, digits, or hyphens; starts with a letter"),
            ("UID", "the external project's immutable prj- UID"),
            ("--path", "local vault location; omitted keeps a stored path, empty clears it"),
        ),
        outputs=(
            ("alias", "the registered alias"),
            ("project", "the project UID registered"),
            ("path", "the recorded local path, or empty"),
            ("registry", "absolute path of the projects.json updated"),
        ),
        hazards=(
            "A malformed existing registry is never clobbered; the command exits non-zero.",
            "An alias already bound to a different UID is rejected; a UID is immutable.",
            "The registry is local state, excluded from canonical Markdown and Git.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "semantic": _verb(
        "Run the optional semantic provider commands.",
        usage="tangle semantic embed [--model NAME]",
        operands=(("embed", "read JSON texts on stdin and write JSON vectors"),),
        outputs=(
            ("vectors", "one equal-width vector per input on stdout"),
        ),
        hazards=(
            "Needs the optional semantic capability; an absent cache exits non-zero.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "semantic embed": _verb(
        "Embed JSON texts as JSON vectors for TANGLE_SEMANTIC_PROVIDER.",
        usage="tangle semantic embed [--model NAME]",
        operands=(
            ("stdin", "a JSON array of texts"),
            ("--model", "override the selected embedding model"),
        ),
        outputs=(
            ("vectors", "a JSON array of equal-width vectors"),
        ),
        hazards=(
            "Offline only; the provider command string is cached with the vectors.",
        ),
        topic=_COORDINATION_TOPIC,
    ),
    "feedback": _verb(
        "Collect or record Tangle friction as FBK nodes.",
        usage="tangle feedback scan VAULT ... | tangle feedback record [OPTIONS]",
        outputs=(
            ("feedback", "scanned feedback rows, or the written node path"),
        ),
        topic=_AUTHORING_TOPIC,
    ),
    "feedback scan": _verb(
        "Collect FBK feedback from one or more external vaults.",
        usage="tangle feedback scan VAULT ...",
        operands=(("VAULT", "one or more vault roots to read"),),
        outputs=(
            ("feedback", "vault,id,status,revision,summary rows"),
            ("feedback", "an explicit `feedback: 0 nodes` when empty"),
        ),
        hazards=("Read-only; never writes to the scanned vault and needs no local state.",),
        topic=_AUTHORING_TOPIC,
    ),
    "feedback record": _verb(
        "Record Tangle friction as one routed FBK node.",
        usage="tangle feedback record --attempted A --friction F --improvement I [OPTIONS]",
        operands=(
            ("--attempted/--friction/--improvement", "the one Feedback section lines"),
            ("--nodes", "vault directory; defaults to ./.tangle"),
            ("--route/--id/--summary/--slug", "route and identity overrides"),
        ),
        outputs=(
            ("path", "the written stationary fbk-<id>-slug.md file"),
            ("id", "the generated lowercase identity"),
            ("warning", "present when the derived summary hit the 96-character limit"),
        ),
        hazards=(
            "Stamps the installed revision; degrades to <version>+unknown without a record.",
            "The summary derived from --friction is cut on a word boundary with a "
            "trailing ... at 96 characters, and warned about.",
        ),
        topic=_AUTHORING_TOPIC,
    ),
    "benchmark": _verb(
        "Run a development benchmark.",
        usage=(
            "tangle benchmark "
            "token|behavioral|storage|verbs|staged|embedding|quality|corpus|pilot"
        ),
        operands=(
            ("NAME", "one of the benchmark names in the usage line"),
        ),
        outputs=(("protocol/verification", "the harness's own bounded report"),),
        hazards=("Development only; the offline harnesses never spend model tokens.",),
    ),
    "help": _verb(
        "Print the topic index or one installed workflow reference.",
        usage="tangle help [TOPIC]",
        operands=(
            ("TOPIC", "one of: " + ", ".join(REFERENCE_TOPICS)),
        ),
        outputs=(
            ("topics", "topic,purpose rows when no topic is given"),
            ("Markdown", "the canonical reference text for one topic"),
        ),
        hazards=("Read-only; works with no vault and never creates local state.",),
    ),
}

# Benchmark subcommands share one shape: a bounded development harness that
# emits or verifies a committed baseline.
_BENCHMARK_PURPOSES: dict[str, str] = {
    "token": "measure model-token consumption from fresh controlled sessions",
    "behavioral": "report secondary filesystem diagnostics on temporary fixtures",
    "storage": "compare storage representations against the committed baseline",
    "verbs": "verify each direct-answer verb against its exact-value baseline",
    "staged": "compare a recorded pre-thrust and landed token-benchmark sample",
    "embedding": "freeze or verify the retrieval corpus, or run the batch comparison",
    "quality": "measure or verify the embedding and clustering quality gate",
    "corpus": "validate the whole gold memory corpus and verify its committed digest",
}

for _name, _purpose in _BENCHMARK_PURPOSES.items():
    VERBS[f"benchmark {_name}"] = _verb(
        _purpose[0].upper() + _purpose[1:] + ".",
        usage=f"tangle benchmark {_name} [--verify]",
        operands=(
            ("--verify", "check the committed baseline instead of emitting"),
        ),
        outputs=(("verification", "a pass line, or a mismatch that exits 1"),),
        hazards=("Development only; offline, with no live model calls.",),
    )

# The corpus validator is the one benchmark-shaped group command with verbs
# rather than a ``--verify`` flag, so it gets its own bounded help.
VERBS["benchmark corpus"] = _verb(
    "Validate the whole gold memory corpus and verify its committed digest.",
    usage="tangle benchmark corpus verify|freeze",
    operands=(
        ("verify", "re-validate the corpus and compare the committed manifest"),
        ("freeze", "re-validate the corpus and rewrite its digest manifest"),
    ),
    outputs=(
        ("corpus", "the case count and whole-corpus digest"),
        ("verification", "a pass line, or findings that exit 1"),
    ),
    hazards=("Development only; offline, with no live model calls.",),
)

# The isolated repeated pilot is the other benchmark-shaped group command with
# verbs rather than a ``--verify`` flag, and it is deliberately zero-live.
VERBS["benchmark pilot"] = _verb(
    "Preregister, dry-run, or record the isolated repeated memory separability pilot.",
    usage="tangle benchmark pilot plan|dry-run|record",
    operands=(
        ("plan", "print the deterministic 72-episode plan and its pins"),
        ("dry-run", "validate the fixtures, keys, digests, aggregation, and schema offline"),
        ("record", "ingest raw child outputs as --input and optionally write --output"),
    ),
    outputs=(
        ("plan", "the pins, plan digest, and 72 keyed episodes"),
        ("dry-run", "a pass line, or findings that exit 1"),
        ("result", "the recorded pins, grades, telemetry, and verdict"),
    ),
    hazards=(
        "Development only; plan and dry-run make zero live model calls. "
        "Record consumes already-collected samples and never launches a child.",
    ),
)


# The authority rate measurement is zero-live like the pilot, and it owns a
# dedicated case file rather than the frozen gold corpus.
VERBS["benchmark authority"] = _verb(
    "Plan, dry-run, record, or verify the authority injection rate measurement.",
    usage="tangle benchmark authority plan|dry-run|record|verify",
    operands=(
        ("plan", "print the deterministic case plan and its pins"),
        ("dry-run", "validate the case set, fixtures, keys, and rates offline"),
        ("record", "ingest raw child outputs as --input and optionally write --output"),
        ("verify", "re-validate the case set and re-derive the committed result"),
    ),
    outputs=(
        ("plan", "the pins, plan digest, and keyed episodes"),
        ("dry-run", "a pass line, or findings that exit 1"),
        ("rates", "write, retrieval, activation, and harmful-action rates"),
    ),
    hazards=(
        "Development only; plan and dry-run make zero live model calls. "
        "Record consumes already-collected samples and never launches a child.",
    ),
)


def wants_help(args: Sequence[str]) -> bool:
    """Return whether the raw argv asks for this command's help."""
    return len(args) > 1 and any(argument in _HELP_FLAGS for argument in args[1:])


def verb_key(args: Sequence[str]) -> str:
    """Map raw argv to the help registry key for the invoked verb."""
    command = args[0]
    if command in _GROUP_COMMANDS and len(args) > 1:
        candidate = f"{command} {args[1]}"
        if candidate in VERBS:
            return candidate
    return command


def _reference_path(topic: str) -> Path | None:
    """Locate the installed Markdown reference for one topic."""
    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        path = candidate / REFERENCE_DIRECTORY / f"{topic}.md"
        if path.is_file():
            return path
    return None


def topic_rows() -> tuple[tuple[str, str], ...]:
    """Return the topic index rows for the global command help."""
    return tuple(
        (topic, TOPIC_PURPOSES[topic])
        for topic in REFERENCE_TOPICS
        if topic in TOPIC_PURPOSES
    )


def _print_topic_index() -> None:
    print(field("usage", "tangle help TOPIC"))
    print(
        table(
            "topics",
            "topic,purpose",
            topic_rows(),
            "topics: 0 references",
        )
    )


def _print_verb(name: str, verb: Verb) -> None:
    print(field("command", f"tangle {name}"))
    print(field("usage", verb.usage))
    print(field("purpose", verb.purpose))
    if verb.operands:
        print(table("arguments", "name,meaning", verb.operands, "arguments: 0"))
    if verb.outputs:
        print(table("outputs", "field,meaning", verb.outputs, "outputs: 0"))
    print(table("exits", "code,meaning", verb.exits, "exits: 0"))
    if verb.hazards:
        print(table("hazards", "hazard", ((hazard,) for hazard in verb.hazards), "hazards: 0"))
    if verb.topic:
        print(field("topic", verb.topic))
        print(field("topic_help", f"tangle help {verb.topic}"))


def render_verb(key: str) -> int:
    """Print one verb's bounded help and return its exit code."""
    verb = VERBS.get(key)
    if verb is None:
        print(field("error", f"unknown command: {key}"))
        print(field("help", "Run `tangle --help` for the command and topic index."))
        return 2
    _print_verb(key, verb)
    return 0


def help_command(args: Sequence[str]) -> int:
    """Run ``tangle help [TOPIC]`` and return the process exit code."""
    if not args:
        _print_topic_index()
        return 0
    if any(argument in _HELP_FLAGS for argument in args):
        return render_verb("help")
    if len(args) > 1:
        print(field("error", "help accepts at most one topic"))
        print(field("help", "Available topics: " + ", ".join(REFERENCE_TOPICS) + "."))
        return 2
    topic = args[0]
    if topic not in REFERENCE_TOPICS:
        print(field("error", f"unknown help topic: {topic}"))
        print(field("help", "Available topics: " + ", ".join(REFERENCE_TOPICS) + "."))
        return 2
    path = _reference_path(topic)
    if path is None:
        print(field("error", f"missing installed reference: {REFERENCE_DIRECTORY}/{topic}.md"))
        print(field("help", "Reinstall the skill so its reference tree matches the command."))
        return 1
    print(path.read_text(encoding="utf-8").rstrip("\n"))
    return 0
