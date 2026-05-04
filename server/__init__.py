"""assemble server — single-import facade.

Re-export the main public API here so LLMs don't have to guess where each
symbol lives. When adding a new public function, always add it to __all__.
"""

from server.inventory import (
    scan,
    apply_classification,
    unclassified_names,
    unclassified_entries,
    parse_skill_frontmatter,
    load_stages,
    load_stage_roles,
    enumerate_skill_paths,
    enumerate_agent_paths,
)
from server.progress import (
    create_run,
    load_progress,
    mark_stage,
    list_runs,
    find_resumable,
)
from server.menu import (
    build_stage_options,
    tools_for_stage,
    contextual_helpers,
)
from server.classify import (
    build_prompt as build_classify_prompt,
    parse_response as parse_classify_response,
)
from server.sequence import (
    build_prompt as build_sequence_prompt,
    parse_response as parse_sequence_response,
)
from server.run_dir import (
    write_run_artifact,
    read_run_artifact,
    run_artifact_path,
    run_dir_path,
    strip_bash_fence,
    update_iteration_state,
)
from server.harness import (
    wrap_with_preamble,
    record_dispatch,
    verify_dispatches,
    canonical_preamble_sha256,
    dispatch_prompt,
    dispatch_and_record,
    update_dispatch_status,
    substitute_inputs,
    extract_wrote_paths,
    bundle_for_stage,
    ALLOWED_PROMPT_FILES,
)
from server.scope_parser import parse_scope_md

__all__ = [
    # inventory
    "scan", "apply_classification",
    "unclassified_names", "unclassified_entries",
    "parse_skill_frontmatter", "load_stages",
    "load_stage_roles", "enumerate_skill_paths", "enumerate_agent_paths",
    # progress
    "create_run", "load_progress", "mark_stage",
    "list_runs", "find_resumable",
    # menu
    "build_stage_options", "tools_for_stage", "contextual_helpers",
    # classify
    "build_classify_prompt", "parse_classify_response",
    # sequence
    "build_sequence_prompt", "parse_sequence_response",
    # run_dir
    "write_run_artifact", "read_run_artifact", "run_artifact_path",
    "run_dir_path", "strip_bash_fence", "update_iteration_state",
    # harness
    "wrap_with_preamble", "record_dispatch", "verify_dispatches",
    "canonical_preamble_sha256",
    "dispatch_prompt", "dispatch_and_record", "update_dispatch_status",
    "substitute_inputs", "extract_wrote_paths",
    "bundle_for_stage",
    "ALLOWED_PROMPT_FILES",
    # scope_parser
    "parse_scope_md",
]
