"""Backfill ``summary=`` and ``description=`` on every FastAPI router
decorator that doesn't already have one.

This is a one-shot codemod (not run at startup) that hand-fills the long
tail of routes Task #75 didn't reach. Routes that already declare a
``summary`` are left untouched so prior hand-written copy is preserved.

Generated copy is built from:
  * the endpoint function name
  * the HTTP method + path
  * the function's docstring first paragraph (if any)
  * the dependency callables (``get_current_user``, ``require_admin``,
    ``require_super_admin``, ``verify_org_access``, ...) so we can
    document the auth requirement
  * the ``response_model`` (if any) for the response-shape hint

Usage::

    python scripts/backfill_route_docs.py backend/routes/contracts_mgmt.py
    python scripts/backfill_route_docs.py backend/routes/  # whole dir
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Iterable

ROUTER_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}

AUTH_DEP_PHRASES = {
    "get_current_user": "Requires an authenticated user (Bearer token).",
    "get_current_admin_user": "Requires platform admin.",
    "get_current_super_admin": "Requires platform super-admin.",
    "get_current_staff_from_cookie": "Requires an internal Cadence staff session cookie.",
    "get_current_staff_or_admin": "Requires either a Cadence staff session or a platform admin Bearer token.",
    "require_admin": "Requires platform admin.",
    "require_super_admin": "Requires platform super-admin.",
    "require_internal_user": "Requires an internal Cadence staff user.",
    "require_staff_user": "Requires an internal Cadence staff user.",
    "client_portal_auth": "Requires a valid client-portal session token.",
    "verify_client_portal_token": "Requires a valid client-portal session token.",
    "verify_share_token": "Authenticated via a public share token.",
    "tenant_admin_auth": "Requires the tenant-admin role on the target organization.",
    "get_current_tenant_admin": "Requires the tenant-admin role on the target organization.",
    "get_internal_user": "Requires an internal Cadence staff user.",
}


def _humanize(func_name: str) -> str:
    parts = [p for p in func_name.split("_") if p]
    if not parts:
        return func_name
    return " ".join(p.capitalize() for p in parts)


def _verb_for_method(method: str) -> str:
    return {
        "get": "Returns",
        "post": "Creates",
        "put": "Updates",
        "patch": "Updates",
        "delete": "Deletes",
    }.get(method, "Handles")


def _docstring_first_para(node: ast.AST) -> str | None:
    doc = ast.get_docstring(node)
    if not doc:
        return None
    para = doc.strip().split("\n\n", 1)[0]
    para = re.sub(r"\s+", " ", para).strip()
    return para or None


def _dep_names(func: ast.AST) -> list[str]:
    """Return the names of callables passed to ``Depends(...)`` in the
    function signature."""
    names: list[str] = []
    args = getattr(func, "args", None)
    if args is None:
        return names
    all_args = list(args.args) + list(args.kwonlyargs)
    defaults: list[ast.AST] = []
    if args.defaults:
        defaults.extend(args.defaults)
    if args.kw_defaults:
        defaults.extend([d for d in args.kw_defaults if d is not None])
    for default in defaults:
        if isinstance(default, ast.Call) and isinstance(default.func, ast.Name) and default.func.id == "Depends":
            if default.args and isinstance(default.args[0], ast.Name):
                names.append(default.args[0].id)
            elif default.args and isinstance(default.args[0], ast.Attribute):
                names.append(default.args[0].attr)
    return names


def _path_params(path: str) -> list[str]:
    return re.findall(r"\{([^}]+)\}", path)


def _decorator_path_and_method(dec: ast.Call, routers: dict[str, str]) -> tuple[str | None, str | None, str | None]:
    if not isinstance(dec.func, ast.Attribute):
        return None, None, None
    method = dec.func.attr.lower()
    if method not in ROUTER_METHODS:
        return None, None, None
    if not (isinstance(dec.func.value, ast.Name) and dec.func.value.id in routers):
        return None, None, None
    path = ""
    if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
        path = dec.args[0].value
    prefix = routers[dec.func.value.id]
    full = (prefix or "") + (path or "")
    if not full:
        full = "/"
    return path, method, full


def _collect_routers(tree: ast.AST) -> dict[str, str]:
    """Find every module-level name bound to an ``APIRouter(prefix=...)``
    call and return a ``{name: prefix}`` map. Routers without an explicit
    prefix get an empty string.
    """
    routers: dict[str, str] = {}
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, ast.Assign):
            value = node.value
            if isinstance(value, ast.Call):
                func = value.func
                target_name = None
                if isinstance(func, ast.Name):
                    target_name = func.id
                elif isinstance(func, ast.Attribute):
                    target_name = func.attr
                if target_name == "APIRouter":
                    prefix = ""
                    for kw in value.keywords:
                        if kw.arg == "prefix" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                            prefix = kw.value.value
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name):
                            routers[tgt.id] = prefix
    if not routers:
        routers["router"] = ""
    return routers


_AUTO_DOC_FINGERPRINT = re.compile(
    r"(Endpoint: `(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) ?[^`]*`|"
    r"for `(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) /)"
)


def _is_autogen_value(node: ast.AST) -> bool:
    if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
        return False
    return bool(_AUTO_DOC_FINGERPRINT.search(node.value))


def _has_summary(dec: ast.Call) -> bool:
    for kw in dec.keywords:
        if kw.arg == "summary":
            return not _is_autogen_value(kw.value)
    return False


def _has_description(dec: ast.Call) -> bool:
    for kw in dec.keywords:
        if kw.arg == "description":
            return not _is_autogen_value(kw.value)
    return False


def _autogen_kwargs_to_strip(dec: ast.Call) -> list[ast.keyword]:
    out = []
    for kw in dec.keywords:
        if kw.arg in ("summary", "description") and _is_autogen_value(kw.value):
            out.append(kw)
    return out


def _response_model(dec: ast.Call) -> str | None:
    for kw in dec.keywords:
        if kw.arg == "response_model":
            try:
                return ast.unparse(kw.value)
            except Exception:
                return None
    return None


def _build_summary(func_name: str, method: str, path: str, doc: str | None) -> str:
    if doc:
        first_sentence = re.split(r"(?<=[.!?])\s", doc, maxsplit=1)[0]
        first_sentence = first_sentence.rstrip(".").strip()
        if 4 <= len(first_sentence) <= 80:
            return first_sentence
    return _humanize(func_name)


_VERB_REWRITES = {
    "list": "Lists",
    "lists": "Lists",
    "get": "Returns",
    "gets": "Returns",
    "fetch": "Fetches",
    "fetches": "Fetches",
    "search": "Searches",
    "find": "Finds",
    "create": "Creates",
    "creates": "Creates",
    "add": "Adds",
    "adds": "Adds",
    "update": "Updates",
    "updates": "Updates",
    "edit": "Edits",
    "patch": "Patches",
    "set": "Sets",
    "delete": "Deletes",
    "deletes": "Deletes",
    "remove": "Removes",
    "removes": "Removes",
    "unlink": "Unlinks",
    "link": "Links",
    "send": "Sends",
    "export": "Exports",
    "exports": "Exports",
    "import": "Imports",
    "imports": "Imports",
    "upload": "Uploads",
    "download": "Downloads",
    "process": "Processes",
    "parse": "Parses",
    "approve": "Approves",
    "reject": "Rejects",
    "submit": "Submits",
    "trigger": "Triggers",
    "run": "Runs",
    "start": "Starts",
    "stop": "Stops",
    "cancel": "Cancels",
    "mark": "Marks",
    "preview": "Previews",
    "generate": "Generates",
    "rebuild": "Rebuilds",
    "sync": "Syncs",
    "merge": "Merges",
    "split": "Splits",
    "assign": "Assigns",
    "unassign": "Unassigns",
    "invite": "Invites",
    "revoke": "Revokes",
    "share": "Shares",
    "unshare": "Unshares",
    "duplicate": "Duplicates",
    "restore": "Restores",
    "archive": "Archives",
    "publish": "Publishes",
    "unpublish": "Unpublishes",
    "reorder": "Reorders",
    "move": "Moves",
    "copy": "Copies",
    "validate": "Validates",
    "check": "Checks",
    "count": "Counts",
    "ping": "Pings",
    "test": "Tests",
}


def _verb_phrase_from_func(func_name: str, method: str) -> str:
    """Turn ``list_creator_songs`` into ``Lists creator songs``."""
    parts = [p for p in func_name.split("_") if p]
    if not parts:
        return _verb_for_method(method) + " resource"
    head = parts[0].lower()
    rest = " ".join(p for p in parts[1:])
    verb = _VERB_REWRITES.get(head)
    if verb is not None:
        if rest:
            return f"{verb} {rest}"
        return verb
    # Fall back to method-derived verb + the whole humanized name.
    return f"{_verb_for_method(method)} {' '.join(parts).lower()}"


def _scan_body_auth(func: ast.AST) -> list[str]:
    """Look at the function body for explicit role/access checks and
    return human phrases describing them.
    """
    phrases: list[str] = []
    src = ast.unparse(func) if hasattr(ast, "unparse") else ""
    if "is_super_admin" in src:
        phrases.append("Requires platform super-admin.")
    if "is_admin" in src and "is_super_admin" not in src:
        phrases.append("Requires platform admin.")
    if "verify_org_access" in src or "OrganizationMember" in src and "membership" in src:
        phrases.append("The caller must be a member of the target organization.")
    if "verify_share_token" in src or "share_token" in src and "Depends" not in src:
        # Public share tokens are common in /public/* routes.
        pass
    return phrases


def _scan_response_shape(func: ast.AST) -> str | None:
    """If every top-level ``return`` in the function returns a literal
    dict/list, summarise its keys / element type for the description.
    """
    returns: list[ast.AST] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Return) and node.value is not None:
            returns.append(node.value)
    if not returns:
        return None
    dict_keys: set[str] = set()
    saw_list = False
    saw_other = False
    for ret in returns:
        if isinstance(ret, ast.Dict):
            for k in ret.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    dict_keys.add(k.value)
        elif isinstance(ret, ast.List):
            saw_list = True
        else:
            saw_other = True
    if dict_keys and not saw_list:
        keys = sorted(dict_keys)[:8]
        joined = ", ".join(f"`{k}`" for k in keys)
        more = "" if len(dict_keys) <= 8 else f" (+{len(dict_keys) - 8} more)"
        return f"Returns a JSON object with keys: {joined}{more}."
    if saw_list and not dict_keys and not saw_other:
        return "Returns a JSON array."
    return None


def _build_description(
    func: ast.AST,
    method: str,
    path: str,
    full_path: str,
    doc: str | None,
    deps: list[str],
    response_model: str | None,
) -> str:
    sentences: list[str] = []
    if doc:
        sentences.append(doc if doc.endswith(".") else doc + ".")
    else:
        phrase = _verb_phrase_from_func(getattr(func, "name", ""), method)
        sentences.append(f"{phrase}.")
        sentences.append(f"Endpoint: `{method.upper()} {full_path}`.")

    pps = _path_params(path)
    if pps:
        joined = ", ".join(f"`{p}`" for p in pps)
        sentences.append(f"Path parameters: {joined}.")

    auth_phrases: list[str] = []
    for d in deps:
        if d in AUTH_DEP_PHRASES and AUTH_DEP_PHRASES[d] not in auth_phrases:
            auth_phrases.append(AUTH_DEP_PHRASES[d])
    for p in _scan_body_auth(func):
        if p not in auth_phrases:
            auth_phrases.append(p)
    if auth_phrases:
        sentences.append(" ".join(auth_phrases))

    if response_model:
        sentences.append(f"Response shape: `{response_model}`.")
    else:
        shape = _scan_response_shape(func)
        if shape:
            sentences.append(shape)

    return " ".join(sentences)


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _splice_kwargs_into_decorator(
    source_lines: list[str],
    dec: ast.Call,
    summary: str,
    description: str,
    add_summary: bool,
    add_description: bool,
) -> None:
    end_line_idx = dec.end_lineno - 1
    end_col = dec.end_col_offset
    line = source_lines[end_line_idx]
    if end_col <= 0 or line[end_col - 1] != ")":
        return
    insert_pos = end_col - 1
    before = line[:insert_pos].rstrip()
    after = line[insert_pos:]

    parts = []
    if add_summary:
        parts.append(f'summary="{_escape(summary)}"')
    if add_description:
        parts.append(f'description="{_escape(description)}"')
    addition = ", ".join(parts)

    if before.endswith("("):
        new_line = before + addition + after
    else:
        if before.endswith(","):
            new_line = before + " " + addition + after
        else:
            new_line = before + ", " + addition + after
    source_lines[end_line_idx] = new_line


_AUTO_KWARG_RE = re.compile(
    r',\s*(?:summary|description)="(?P<value>(?:[^"\\]|\\.)*)"'
)


def _strip_autogen_kwargs(source: str) -> str:
    """Textually remove ``, summary="..."`` / ``, description="..."``
    kwargs whose content matches the auto-doc fingerprint, so the
    builder can replace them on a re-run.
    """
    def repl(m: re.Match[str]) -> str:
        value = m.group("value")
        # Unescape just enough to check for fingerprint.
        unescaped = value.replace('\\"', '"').replace("\\\\", "\\")
        if _AUTO_DOC_FINGERPRINT.search(unescaped):
            return ""
        return m.group(0)

    return _AUTO_KWARG_RE.sub(repl, source)


def process_file(path: Path) -> int:
    source = path.read_text(encoding="utf-8")
    source = _strip_autogen_kwargs(source)
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print(f"  ! syntax error in {path}: {exc}", file=sys.stderr)
        return 0

    routers = _collect_routers(tree)
    edits: list[tuple[ast.Call, str, str, bool, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            dec_path, method, full_path = _decorator_path_and_method(dec, routers)
            if method is None or full_path is None:
                continue
            need_summary = not _has_summary(dec)
            need_description = not _has_description(dec)
            if not (need_summary or need_description):
                continue
            doc = _docstring_first_para(node)
            deps = _dep_names(node)
            response_model = _response_model(dec)
            summary = _build_summary(node.name, method, dec_path or "", doc)
            description = _build_description(node, method, dec_path or "", full_path, doc, deps, response_model)
            edits.append((dec, summary, description, need_summary, need_description))

    if not edits:
        return 0

    edits.sort(key=lambda e: (e[0].end_lineno, e[0].end_col_offset), reverse=True)
    lines = source.splitlines(keepends=True)
    line_endings = []
    bare_lines = []
    for ln in lines:
        if ln.endswith("\r\n"):
            bare_lines.append(ln[:-2])
            line_endings.append("\r\n")
        elif ln.endswith("\n"):
            bare_lines.append(ln[:-1])
            line_endings.append("\n")
        else:
            bare_lines.append(ln)
            line_endings.append("")

    for dec, summary, description, add_summary, add_description in edits:
        _splice_kwargs_into_decorator(
            bare_lines, dec, summary, description, add_summary, add_description
        )

    rebuilt = "".join(b + e for b, e in zip(bare_lines, line_endings))
    if rebuilt != source:
        # Validate the result still parses before writing.
        try:
            ast.parse(rebuilt)
        except SyntaxError as exc:
            print(f"  ! refusing to write {path}: post-edit parse failed: {exc}", file=sys.stderr)
            return 0
        path.write_text(rebuilt, encoding="utf-8")
    return len(edits)


def iter_targets(args: Iterable[str]) -> Iterable[Path]:
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            for child in sorted(p.glob("*.py")):
                if child.name == "__init__.py":
                    continue
                yield child
        else:
            yield p


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    total = 0
    for target in iter_targets(argv):
        n = process_file(target)
        if n:
            print(f"  {target}: backfilled {n} decorator(s)")
        total += n
    print(f"Backfilled {total} decorator(s) total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
