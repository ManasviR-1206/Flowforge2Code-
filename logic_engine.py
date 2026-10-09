"""
Flowchart logic engine.

The graph {nodes, edges} is the single source of truth. This module:
- normalizes React Flow / legacy graphs
- builds a structured AST
- compiles that AST into executable Python 3 (deterministic)
- analyzes structure for the debugger
- applies validated chatbot patches
"""

from __future__ import annotations

import ast
import copy
import re
from typing import Any, Optional

ALLOWED_NODE_TYPES = {
    "start_end",
    "start",
    "end",
    "process",
    "input_output",
    "input",
    "output",
    "decision",
    "document",
    "predefined_process",
    "database",
    "manual_input",
    "connector",
    "offpage",
    "delay",
    "arrow",
}

GENERIC_LABELS = {
    "",
    "start / end",
    "start/end",
    "process",
    "input / output",
    "input/output",
    "decision",
    "decision?",
    "document",
    "pre-defined process",
    "predefined process",
    "function",
    "database",
    "manual input",
    "connector",
    "off-page",
    "offpage",
    "delay",
    "arrow",
}


def node_text(node: dict) -> str:
    data = node.get("data")
    if isinstance(data, dict):
        return str(data.get("label") or data.get("text") or "").strip()
    if node.get("text"):
        return str(node["text"]).strip()
    return str(node.get("label") or "").strip()


def node_type_raw(node: dict) -> str:
    return str(node.get("type") or "process").strip()


def classify_semantic(shape: str, text: str) -> str:
    shape = (shape or "process").lower()
    text_lower = text.lower().strip()

    if shape in ("start", "end"):
        return shape
    if "start" in text_lower and "end" not in text_lower:
        return "start"
    if text_lower in ("end", "stop") or (text_lower.endswith("end") and shape in ("start_end", "start")):
        return "end"
    if shape == "start_end":
        if "end" in text_lower or "stop" in text_lower:
            return "end"
        return "start"

    is_out = any(k in text_lower for k in ("print", "output", "display", "show", "write"))
    is_in = any(k in text_lower for k in ("input", "read", "enter", "get", "scan"))

    if shape in ("input_output", "manual_input", "document"):
        if is_out and not is_in:
            return "output"
        if is_in and not is_out:
            return "input"
        if is_out:
            return "output"
        if is_in:
            return "input"
        if shape == "document":
            return "output"
        if shape == "manual_input":
            return "input"
        return "input"

    if is_out:
        return "output"
    if is_in:
        return "input"
    if shape == "decision" or "?" in text or _looks_like_condition(text):
        return "decision"
    if shape == "predefined_process":
        return "function"
    if shape in ("process", "database", "delay", "connector", "offpage", "arrow"):
        return "process" if shape not in ("connector", "offpage", "arrow") else shape
    return shape if shape in ALLOWED_NODE_TYPES else "process"


def _looks_like_condition(text: str) -> bool:
    return bool(re.search(r"(>=|<=|==|!=|>|<|%|\b(and|or|not)\b)", text, re.I))


def sanitize_graph(nodes: list, edges: list) -> tuple[list, list]:
    """Strip non-JSON fields and normalize ids/types for APIs."""
    clean_nodes = []
    for n in nodes or []:
        nid = str(n.get("id"))
        ntype = node_type_raw(n)
        if ntype not in ALLOWED_NODE_TYPES:
            ntype = "process"
        pos = n.get("position") or {"x": 300, "y": 80}
        data = n.get("data") if isinstance(n.get("data"), dict) else {}
        label = node_text(n)
        clean_nodes.append({
            "id": nid,
            "type": ntype,
            "position": {"x": float(pos.get("x", 0)), "y": float(pos.get("y", 0))},
            "data": {"label": label},
            "text": label,
        })

    clean_edges = []
    for i, e in enumerate(edges or []):
        src = str(e.get("source") or e.get("from") or "")
        tgt = str(e.get("target") or e.get("to") or "")
        if not src or not tgt:
            continue
        label = e.get("label") or e.get("branch") or ""
        if isinstance(label, dict):
            label = label.get("label") or ""
        label = str(label).strip()
        handle = str(e.get("sourceHandle") or "")
        if not label:
            hl = handle.lower()
            if hl in ("yes", "true", "left"):
                label = "Yes"
            elif hl in ("no", "false", "right"):
                label = "No"
        eid = str(e.get("id") or f"e_{src}_{tgt}_{i}")
        item = {
            "id": eid,
            "source": src,
            "target": tgt,
            "from": src,
            "to": tgt,
            "type": e.get("type") or "smoothstep",
            "animated": True,
            "label": label,
            "branch": label or None,
        }
        if handle:
            item["sourceHandle"] = handle
        clean_edges.append(item)
    return clean_nodes, clean_edges


def build_flowchart_ast(nodes_or_blocks, edges_or_connections):
    nodes, edges = sanitize_graph(nodes_or_blocks, edges_or_connections)
    ast_nodes = []
    for n in nodes:
        text = node_text(n)
        shape = node_type_raw(n)
        ast_nodes.append({
            "id": str(n["id"]),
            "type": classify_semantic(shape, text),
            "shape": shape,
            "raw_text": text if text else f"Step {n['id']}",
            "position": n.get("position") or {},
        })

    ast_edges = []
    for e in edges:
        ast_edges.append({
            "from": str(e["source"]),
            "to": str(e["target"]),
            "branch": (e.get("label") or None) or None,
            "sourceHandle": e.get("sourceHandle"),
        })

    return {
        "program_name": "FlowchartProgram",
        "nodes": ast_nodes,
        "edges": ast_edges,
    }


def _graph_maps(ast_data: dict):
    nodes = {str(n["id"]): n for n in ast_data.get("nodes", [])}
    next_map: dict[str, list[str]] = {}
    branch_map: dict[str, dict[str, str]] = {}
    incoming: dict[str, list[str]] = {}
    for e in ast_data.get("edges", []):
        frm, to = str(e["from"]), str(e["to"])
        next_map.setdefault(frm, []).append(to)
        incoming.setdefault(to, []).append(frm)
        br = e.get("branch")
        handle = str(e.get("sourceHandle") or "").lower()
        if not br and handle:
            if handle in ("yes", "true", "left"):
                br = "Yes"
            elif handle in ("no", "false", "right"):
                br = "No"
        if br:
            key = str(br).strip().capitalize()
            if key.lower() in ("true", "y"):
                key = "Yes"
            if key.lower() in ("false", "n"):
                key = "No"
            branch_map.setdefault(frm, {})[key] = to
    return nodes, next_map, branch_map, incoming


def find_start_id(nodes: dict) -> Optional[str]:
    for n in nodes.values():
        if n.get("type") == "start":
            return str(n["id"])
    for n in nodes.values():
        if "start" in str(n.get("raw_text", "")).lower():
            return str(n["id"])
    if nodes:
        return next(iter(nodes))
    return None


def reachable_from(start: str, next_map: dict, stop: Optional[str] = None) -> set[str]:
    seen = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        if cur in seen or cur == stop:
            continue
        seen.add(cur)
        for nxt in next_map.get(cur, []):
            if nxt not in seen:
                stack.append(nxt)
    return seen


def find_join(yes_id: Optional[str], no_id: Optional[str], next_map: dict) -> Optional[str]:
    if not yes_id or not no_id:
        return None
    yes_reach = reachable_from(yes_id, next_map)
    # Walk NO path in BFS; first node also reachable from YES is the merge
    q = [no_id]
    seen = set()
    while q:
        cur = q.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        if cur in yes_reach:
            return cur
        q.extend(next_map.get(cur, []))
    return None


def path_reaches(src: Optional[str], dest: str, next_map: dict, limit: int = 80) -> bool:
    if not src:
        return False
    q = [src]
    seen = set()
    steps = 0
    while q and steps < limit:
        cur = q.pop(0)
        steps += 1
        if cur == dest:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        q.extend(next_map.get(cur, []))
    return False


def extract_identifier(text: str, default: str = "n") -> str:
    clean = re.sub(r"^(input|read|get|enter|output|print|display|show|write)\s*", "", text, flags=re.I).strip()
    clean = clean.strip("\"'")
    match = re.search(r"[A-Za-z_][A-Za-z0-9_]*", clean)
    return match.group(0) if match else default


INPUT_TYPE_WORDS = {
    "number", "num", "integer", "int", "value", "val", "float", "double",
    "string", "str", "char", "character", "text", "line", "operation", "op",
    "name", "choice", "sign", "mode", "symbol", "digit", "operand",
}


def extract_input_var(text: str) -> str:
    """Variable name for an input node: 'Input number n' -> n, 'Input a' -> a."""
    clean = re.sub(r"^(input|read|get|enter)\s*", "", text, flags=re.I).strip()
    clean = clean.strip("\"'")
    ids = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", clean)
    if not ids:
        return "n"
    if len(ids) > 1 and ids[0].lower() in INPUT_TYPE_WORDS:
        return ids[-1]
    return ids[0]


def extract_print_value(text: str) -> str:
    clean = re.sub(r"^(print|output|display|show|write)\s*", "", text, flags=re.I).strip()
    if not clean:
        return '"Done"'
    if (clean.startswith('"') and clean.endswith('"')) or (clean.startswith("'") and clean.endswith("'")):
        return clean
    if re.fullmatch(r"-?\d+(\.\d+)?", clean):
        return clean
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", clean):
        # Capitalized words like Positive/Even are messages, not variables
        if clean[0].isupper() and clean not in ("True", "False", "None"):
            return json_quote(clean)
        return clean
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_ ]*", clean):
        return json_quote(clean)
    return json_quote(clean)


def json_quote(s: str) -> str:
    inner = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{inner}"'


def normalize_condition(text: str) -> str:
    cond = text.replace("?", "").strip()
    cond = re.sub(r"^(if|whether|check( if)?)\s+", "", cond, flags=re.I).strip()

    replacements = {
        "greater than or equal to": ">=",
        "less than or equal to": "<=",
        "greater than": ">",
        "less than": "<",
        "not equal to": "!=",
        "equal to": "==",
        "is equal to": "==",
        "equals": "==",
        "modulo": "%",
        "mod": "%",
        " is even": " % 2 == 0",
        " is odd": " % 2 != 0",
    }
    low = cond.lower()
    for k, v in replacements.items():
        if k in low:
            cond = re.sub(re.escape(k), v, cond, flags=re.I)

    # Convert single = to == if not already part of ==, !=, >=, <=
    cond = re.sub(r"(?<![<>=!])=(?!=)", "==", cond)

    # Wrap unquoted single-character operators or operator strings on RHS of comparison (e.g. op == + -> op == "+")
    cond = re.sub(r"(==|!=)\s*([+\-*/%^&|]+)\s*$", r'\1 "\2"', cond)

    # Wrap unquoted bare words on RHS if they look like string literals rather than numbers/booleans/variables
    # e.g., op == plus -> op == "plus"
    match_rhs = re.search(r"(==|!=)\s*([A-Za-z_][A-Za-z0-9_]*)\s*$", cond)
    if match_rhs:
        var_rhs = match_rhs.group(2)
        lhs = cond[:match_rhs.start(1)].strip()
        if var_rhs.lower() not in ("true", "false", "none") and not var_rhs.isdigit():
            if var_rhs != lhs and not re.search(rf"\b{re.escape(var_rhs)}\b", lhs):
                cond = cond[:match_rhs.start(1)] + f'{match_rhs.group(1)} "{var_rhs}"'

    # If condition is empty or missing comparison operator
    if not any(op in cond for op in (">", "<", "==", "!=", ">=", "<=", "%", " in ", " not ")):
        ident = extract_identifier(cond, cond or "n")
        if "even" in low:
            cond = f"{ident} % 2 == 0"
        elif "odd" in low:
            cond = f"{ident} % 2 != 0"
        elif "prime" in low:
            cond = "is_prime"
        else:
            cond = f"{ident} > 0" if ident else "True"

    # Fix incomplete trailing comparison operators: e.g. "x ==" or "x >"
    cond = re.sub(r"(==|!=)\s*$", '== ""', cond)
    cond = re.sub(r"(>=|<=|>|<)\s*$", r'\1 0', cond)

    # Test syntax with Python AST parser
    try:
        import ast as py_ast
        py_ast.parse(f"if {cond}:\n    pass")
    except SyntaxError:
        # Fallback repair attempts
        if "==" in cond:
            parts = cond.split("==", 1)
            lhs = parts[0].strip()
            rhs = parts[1].strip()
            rhs_quoted = f'"{rhs}"' if not (rhs.startswith('"') or rhs.startswith("'")) else rhs
            candidate = f"{lhs} == {rhs_quoted}"
            try:
                import ast as py_ast
                py_ast.parse(f"if {candidate}:\n    pass")
                return candidate
            except SyntaxError:
                pass
        ident = extract_identifier(cond, "n")
        cond = f"{ident} > 0" if ident else "True"

    return cond


def compile_to_python(ast_data: dict) -> str:
    """Deterministic Python compiler from flowchart AST. Never invents extra logic."""
    nodes, next_map, branch_map, _incoming = _graph_maps(ast_data)
    if not nodes:
        return "# Empty flowchart\n"

    start = find_start_id(nodes)
    lines: list[str] = []
    emitted_funcs: set[str] = set()

    def emit_node_body(nid: str, indent: str) -> None:
        node = nodes[nid]
        ntype = node.get("type")
        text = str(node.get("raw_text") or "").strip()
        if ntype in ("start", "end", "connector", "offpage", "arrow"):
            return
        if ntype == "input":
            var_name = extract_input_var(text)
            text_low = text.lower()
            if any(k in text_low for k in ("op", "operation", "str", "string", "name", "char", "choice", "text", "line", "symbol", "sign", "mode")):
                lines.append(f'{indent}{var_name} = input("Enter {var_name}: ")')
            elif any(k in text_low for k in ("float", "price", "rate", "avg", "average", "double")):
                lines.append(f'{indent}{var_name} = float(input("Enter {var_name}: "))')
            else:
                lines.append(f'{indent}{var_name} = int(input("Enter {var_name}: "))')
            return
        if ntype == "output":
            lines.append(f"{indent}print({extract_print_value(text)})")
            return
        if ntype == "function":
            name = re.sub(r"[^A-Za-z0-9_]", "_", extract_identifier(text, "fn"))
            lines.append(f"{indent}{name}()")
            return
        if ntype == "decision":
            return
        if "=" in text or "+=" in text or "-=" in text or "*=" in text or "/=" in text:
            lines.append(f"{indent}{text}")
        elif text and text.lower() not in GENERIC_LABELS:
            # Treat bare expressions as statements when they look like code
            if re.search(r"[+\-*/%]", text) and re.search(r"[A-Za-z_]", text):
                lines.append(f"{indent}{text}")
            else:
                lines.append(f"{indent}# {text}")

    def process_flow(nid: Optional[str], indent: str, stop_at: Optional[str], stack: tuple[str, ...]) -> None:
        while nid and nid in nodes and nid != stop_at:
            if nid in stack:
                return
            node = nodes[nid]
            ntype = node.get("type")
            text = str(node.get("raw_text") or "").strip()

            if ntype == "end":
                return

            if ntype == "decision":
                cond = normalize_condition(text)
                branches = branch_map.get(nid, {})
                targets = next_map.get(nid, [])
                yes_t = branches.get("Yes") or branches.get("True")
                no_t = branches.get("No") or branches.get("False")
                if not yes_t and targets:
                    yes_t = targets[0]
                if not no_t:
                    for t in targets:
                        if t != yes_t:
                            no_t = t
                            break

                yes_loops = path_reaches(yes_t, nid, next_map)
                no_loops = path_reaches(no_t, nid, next_map)

                if yes_loops and not no_loops:
                    lines.append(f"{indent}while {cond}:")
                    if yes_t:
                        process_flow(yes_t, indent + "    ", nid, stack + (nid,))
                    else:
                        lines.append(f"{indent}    pass")
                    nid = no_t
                    continue
                if no_loops and not yes_loops:
                    lines.append(f"{indent}while not ({cond}):")
                    if no_t:
                        process_flow(no_t, indent + "    ", nid, stack + (nid,))
                    else:
                        lines.append(f"{indent}    pass")
                    nid = yes_t
                    continue
                if yes_loops and no_loops:
                    lines.append(f"{indent}while True:")
                    lines.append(f"{indent}    if {cond}:")
                    if yes_t:
                        process_flow(yes_t, indent + "        ", nid, stack + (nid,))
                    lines.append(f"{indent}    else:")
                    if no_t:
                        process_flow(no_t, indent + "        ", nid, stack + (nid,))
                    return

                join = find_join(yes_t, no_t, next_map) if yes_t and no_t else None
                lines.append(f"{indent}if {cond}:")
                if yes_t and yes_t != join:
                    process_flow(yes_t, indent + "    ", join, stack + (nid,))
                else:
                    lines.append(f"{indent}    pass")
                lines.append(f"{indent}else:")
                if no_t and no_t != join:
                    process_flow(no_t, indent + "    ", join, stack + (nid,))
                else:
                    lines.append(f"{indent}    pass")
                nid = join
                continue

            emit_node_body(nid, indent)
            targets = next_map.get(nid, [])
            nid = targets[0] if targets else None

    process_flow(start, "", None, tuple())
    if not lines:
        lines = ["# Flowchart produced no executable steps"]

    code = "\n".join(lines) + "\n"
    try:
        import ast as py_ast
        py_ast.parse(code)
    except SyntaxError:
        repaired_lines = []
        for line in lines:
            if line.strip().startswith("if ") or line.strip().startswith("while "):
                indent_str = line[:len(line) - len(line.lstrip())]
                parts = line.strip().split(" ", 1)
                kw = parts[0]
                rest = parts[1].rstrip(":").strip() if len(parts) > 1 else "True"
                safe_cond = normalize_condition(rest)
                repaired_lines.append(f"{indent_str}{kw} {safe_cond}:")
            else:
                repaired_lines.append(line)
        code = "\n".join(repaired_lines) + "\n"

    return code


def _collect_assigned_names(tree) -> set:
    """All names bound by assignment, import, def, for, with, except in a parsed module."""
    assigned = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        assigned.add(sub.id)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    assigned.add(sub.id)
        elif isinstance(node, ast.For):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    assigned.add(sub.id)
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars:
                    for sub in ast.walk(item.optional_vars):
                        if isinstance(sub, ast.Name):
                            assigned.add(sub.id)
        elif isinstance(node, ast.FunctionDef):
            assigned.add(node.name)
            for a in node.args.args:
                assigned.add(a.arg)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assigned.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                assigned.add(alias.asname or alias.name)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                assigned.add(node.name)
        elif isinstance(node, ast.Global):
            assigned.update(node.names)
    return assigned


def _undefined_identifiers(code_str: str) -> set:
    """Names read in code_str that are never assigned there and not builtins."""
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        return set()
    assigned = _collect_assigned_names(tree)
    used = {
        n.id for n in ast.walk(tree)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
    }
    builtins_ns = dir(__builtins__) if not isinstance(__builtins__, dict) else list(__builtins__)
    known = set(builtins_ns) | {
        "input", "print", "int", "float", "str", "bool", "len", "range",
        "list", "dict", "set", "tuple", "sum", "abs", "max", "min", "type",
        "enumerate", "zip", "round", "sorted", "reversed", "map", "filter",
    }
    return used - assigned - known


def consistency_warnings(ast_data: dict, code: str) -> list[str]:
    warnings = []
    input_vars = set()
    for node in ast_data.get("nodes", []):
        if node.get("type") == "input":
            var_name = extract_input_var(str(node.get("raw_text") or ""))
            input_vars.add(var_name)
    undefined = _undefined_identifiers(code)
    if undefined:
        warnings.append(
            "Warning: The generated code reads variable(s) not defined by the flowchart: "
            + ", ".join(sorted(undefined))
            + ". The deterministic compiler output is recommended instead."
        )
    for node in ast_data.get("nodes", []):
        ntype = node.get("type")
        text = str(node.get("raw_text") or "").strip()
        if not text or text.lower() in GENERIC_LABELS:
            continue
        if ntype == "input":
            var_name = extract_input_var(text)
            if var_name and not re.search(rf"\b{re.escape(var_name)}\b", code):
                warnings.append(f"Warning: The input node '{text}' is not represented correctly in the generated code.")
            elif "input(" not in code:
                warnings.append("Warning: Flowchart input operations are missing from the generated code.")
        elif ntype == "output":
            if "print(" not in code:
                warnings.append(f"Warning: The output node '{text}' is not represented correctly in the generated code.")
            else:
                token = extract_identifier(text, "")
                printable = re.sub(r"^(print|output|display|show)\s*", "", text, flags=re.I).strip().strip("\"'")
                if printable and not re.search(rf"\b{re.escape(printable)}\b", code) and token and not re.search(rf"\b{re.escape(token)}\b", code):
                    warnings.append(f"Warning: The output node '{text}' is not represented correctly in the generated code.")
        elif ntype == "decision":
            cond = normalize_condition(text)
            tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[><=!%]+", cond)
            significant = [t for t in tokens if t.lower() not in ("if", "and", "or", "not")]
            sig_ids = [t for t in significant if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t)]
            if sig_ids and not any(re.search(rf"\b{re.escape(t)}\b", code) for t in sig_ids):
                warnings.append(f"Warning: The decision node '{text}' is not represented correctly in the generated code.")
        elif ntype == "process" and ("=" in text or any(op in text for op in ("+", "*", "-", "/"))):
            snippet = text.replace(" ", "")
            compact = code.replace(" ", "")
            if snippet and snippet not in compact:
                # allow whitespace differences already handled; check operators
                if any(op in text for op in ("+", "*", "-", "/")) and not any(op in code for op in re.findall(r"[+\-*/]", text)):
                    warnings.append(f"Warning: The process node '{text}' is not represented correctly in the generated code.")
    return warnings


def analyze_graph_structure(nodes: list, edges: list) -> list[dict]:
    nodes, edges = sanitize_graph(nodes, edges)
    issues: list[dict] = []
    if not nodes:
        issues.append({"type": "error", "message": "Canvas is empty. Add some nodes first.", "node_id": None})
        return issues

    ast_data = build_flowchart_ast(nodes, edges)
    nmap, next_map, branch_map, incoming = _graph_maps(ast_data)
    start_id = find_start_id(nmap)
    starts = [n for n in ast_data["nodes"] if n["type"] == "start"]
    ends = [n for n in ast_data["nodes"] if n["type"] == "end"]

    if not starts:
        issues.append({"type": "error", "message": "Missing Start node. Every flowchart must begin with a Start terminator.", "node_id": None})
    if not ends:
        issues.append({"type": "error", "message": "Missing End node. Flowcharts should terminate with an End terminator.", "node_id": None})

    reach = reachable_from(start_id, next_map) if start_id else set()

    for n in ast_data["nodes"]:
        nid = n["id"]
        label = n["raw_text"]
        ins = incoming.get(nid, [])
        outs = next_map.get(nid, [])

        if n["type"] not in ("start",) and not ins and not outs:
            issues.append({"type": "warning", "message": f"Node '{label or nid}' is disconnected — it has no connections.", "node_id": nid})
        elif start_id and nid not in reach:
            issues.append({"type": "warning", "message": f"Node '{label or nid}' is unreachable from Start.", "node_id": nid})

        if n["type"] != "end" and not outs and n["type"] != "arrow":
            issues.append({"type": "warning", "message": f"Node '{label or nid}' has no outgoing connection. Connect it to the next step.", "node_id": nid})

        if not label or label.lower() in GENERIC_LABELS:
            if n["type"] not in ("connector", "arrow", "start", "end"):
                issues.append({"type": "error", "message": f"Node '{nid}' has empty or placeholder text. Double-click it to add a real instruction.", "node_id": nid})

        if n["type"] == "decision":
            outs = next_map.get(nid, [])
            branches = branch_map.get(nid, {})
            labels = [str(e.get("branch") or "").lower() for e in ast_data["edges"] if e["from"] == nid]
            has_yes = any(k in ("yes", "true", "y") for k in list(branches.keys()) + labels) or any(
                (e.get("sourceHandle") or "").lower() in ("yes", "left") for e in ast_data["edges"] if e["from"] == nid
            )
            has_no = any(k in ("no", "false", "n") for k in list(branches.keys()) + labels) or any(
                (e.get("sourceHandle") or "").lower() in ("no", "right") for e in ast_data["edges"] if e["from"] == nid
            )
            if len(outs) == 0:
                issues.append({"type": "error", "message": f"Your decision node '{label}' has no outgoing branches. Add Yes and No branches.", "node_id": nid})
            elif len(outs) == 1:
                missing = "NO" if has_yes or (labels and labels[0] in ("yes", "true", "y")) else "YES"
                issues.append({
                    "type": "error",
                    "message": f"Missing {missing} branch. Your decision node '{label}' must have both YES and NO paths.",
                    "node_id": nid,
                })
            else:
                if not has_yes:
                    issues.append({"type": "error", "message": f"Missing YES branch. Label an outgoing edge from '{label}' as YES.", "node_id": nid})
                if not has_no:
                    issues.append({"type": "error", "message": f"Missing NO branch. Your decision node '{label}' is missing a NO branch.", "node_id": nid})
            if not label or label.lower() in ("decision", "decision?", ""):
                issues.append({"type": "error", "message": "A decision node has an empty condition. Specify a condition (e.g., 'n > 0?').", "node_id": nid})

        if n["type"] == "start" and ins:
            issues.append({"type": "warning", "message": "Start should not have incoming connections (incorrect flow direction).", "node_id": nid})
        if n["type"] == "end" and outs:
            issues.append({"type": "warning", "message": "End should not have outgoing connections (incorrect flow direction).", "node_id": nid})

    # Duplicate placeholder nodes
    texts = {}
    for n in ast_data["nodes"]:
        key = (n["type"], n["raw_text"].strip().lower())
        texts.setdefault(key, []).append(n["id"])
    for (_t, txt), ids in texts.items():
        if txt and txt not in GENERIC_LABELS and len(ids) > 1:
            for nid in ids[1:]:
                issues.append({"type": "warning", "message": f"Duplicate node '{txt}' may be unnecessary.", "node_id": nid})

    # Possible infinite loops: cycle with a decision that has no exit off the cycle
    for nid, node in nmap.items():
        if node.get("type") != "decision":
            continue
        outs = next_map.get(nid, [])
        if len(outs) >= 2:
            continue
        if outs and path_reaches(outs[0], nid, next_map):
            issues.append({"type": "warning", "message": f"Possible infinite loop: decision '{node.get('raw_text')}' cycles without an exit (NO) branch.", "node_id": nid})

    return issues


def next_node_id(nodes: list, prefix: str = "node_") -> str:
    max_n = 0
    for n in nodes:
        m = re.search(r"(\d+)$", str(n.get("id", "")))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"{prefix}{max_n + 1}"


def apply_patch(nodes: list, edges: list, patch: dict) -> tuple[list, list]:
    if not patch:
        return nodes, edges
    nodes = copy.deepcopy(nodes)
    edges = copy.deepcopy(edges)
    action = (patch.get("action") or "replace").lower()

    if action == "replace":
        return patch.get("nodes") or nodes, patch.get("edges") or edges

    if action in ("add_nodes", "add"):
        new_nodes = patch.get("new_nodes") or patch.get("nodes") or []
        new_edges = patch.get("new_edges") or patch.get("edges") or []
        existing = {str(n.get("id")) for n in nodes}
        for n in new_nodes:
            if str(n.get("id")) not in existing:
                nodes.append(n)
        existing_e = {(str(e.get("source") or e.get("from")), str(e.get("target") or e.get("to")), str(e.get("label") or "")) for e in edges}
        for e in new_edges:
            key = (str(e.get("source") or e.get("from")), str(e.get("target") or e.get("to")), str(e.get("label") or ""))
            if key not in existing_e:
                edges.append(e)
        return nodes, edges

    if action == "update_node":
        nid = str(patch.get("node_id") or "")
        data = patch.get("data") or {}
        for n in nodes:
            if str(n.get("id")) == nid:
                n.setdefault("data", {})
                if isinstance(n["data"], dict):
                    n["data"].update(data)
                    if "label" in data:
                        n["text"] = data["label"]
                if "type" in patch:
                    n["type"] = patch["type"]
                if "label" in patch:
                    n.setdefault("data", {})
                    n["data"]["label"] = patch["label"]
        return nodes, edges

    if action == "delete_nodes":
        ids = {str(i) for i in (patch.get("node_ids") or ([patch["node_id"]] if patch.get("node_id") else []))}
        nodes = [n for n in nodes if str(n.get("id")) not in ids]
        edges = [e for e in edges if str(e.get("source") or e.get("from")) not in ids and str(e.get("target") or e.get("to")) not in ids]
        return nodes, edges

    if action == "add_edges":
        for e in patch.get("new_edges") or patch.get("edges") or []:
            edges.append(e)
        return nodes, edges

    return nodes, edges


def auto_fix_graph(nodes: list, edges: list, issues: Optional[list] = None) -> tuple[list, list]:
    """Deterministic structural repairs for common debugger issues."""
    nodes, edges = sanitize_graph(nodes, edges)
    ast = build_flowchart_ast(nodes, edges)
    max_y = max((float((n.get("position") or {}).get("y", 0)) for n in nodes), default=40)

    def has_start():
        return any(x["type"] == "start" for x in ast["nodes"])

    def has_end():
        return any(x["type"] == "end" for x in ast["nodes"])

    if not has_start():
        sid = next_node_id(nodes)
        start = {"id": sid, "type": "start_end", "position": {"x": 300, "y": 20}, "data": {"label": "Start"}}
        if nodes:
            first = str(nodes[0]["id"])
            nodes = [start] + nodes
            edges = [{"id": f"e_{sid}_{first}", "source": sid, "target": first, "type": "smoothstep", "animated": True, "label": ""}] + edges
        else:
            nodes = [start]
        ast = build_flowchart_ast(nodes, edges)

    if not has_end():
        eid = next_node_id(nodes)
        end = {"id": eid, "type": "start_end", "position": {"x": 300, "y": max_y + 140}, "data": {"label": "End"}}
        dangling = []
        sources = {str(e.get("source")) for e in edges}
        for n in nodes:
            nid = str(n["id"])
            if nid not in sources and "end" not in str((n.get("data") or {}).get("label", "")).lower():
                dangling.append(nid)
        nodes = nodes + [end]
        for d in dangling or ([str(nodes[-2]["id"])] if len(nodes) > 1 else []):
            edges.append({"id": f"e_{d}_{eid}", "source": d, "target": eid, "type": "smoothstep", "animated": True, "label": ""})
        ast = build_flowchart_ast(nodes, edges)

    nmap, next_map, branch_map, incoming = _graph_maps(ast)
    for n in ast["nodes"]:
        if n["type"] != "decision":
            continue
        outs = next_map.get(n["id"], [])
        branches = branch_map.get(n["id"], {})
        if len(outs) < 2 or "No" not in branches:
            nid = next_node_id(nodes)
            src_node = next((x for x in nodes if str(x["id"]) == n["id"]), {})
            extra = {
                "id": nid,
                "type": "input_output",
                "position": {
                    "x": 480,
                    "y": float((src_node.get("position") or {}).get("y", 300)) + 140,
                },
                "data": {"label": 'Print "else"'},
            }
            nodes.append(extra)
            edges.append({
                "id": f"e_{n['id']}_{nid}_no",
                "source": n["id"],
                "target": nid,
                "sourceHandle": "no",
                "label": "No",
                "type": "smoothstep",
                "animated": True,
            })
            ends = [x for x in ast["nodes"] if x["type"] == "end"]
            if ends:
                edges.append({
                    "id": f"e_{nid}_{ends[0]['id']}",
                    "source": nid,
                    "target": ends[0]["id"],
                    "type": "smoothstep",
                    "animated": True,
                    "label": "",
                })

    for n in nodes:
        label = node_text(n)
        if not label or label.lower() in GENERIC_LABELS:
            ntype = node_type_raw(n)
            if ntype == "decision":
                n.setdefault("data", {})["label"] = "n > 0?"
            elif ntype == "input_output":
                n.setdefault("data", {})["label"] = "Input n"
            elif ntype == "process":
                n.setdefault("data", {})["label"] = "result = n"

    return sanitize_graph(nodes, edges)


def insert_node_before_end(nodes: list, edges: list, new_node: dict) -> tuple[list, list]:
    ast = build_flowchart_ast(nodes, edges)
    nmap, next_map, _b, incoming = _graph_maps(ast)
    end_nodes = [n for n in ast["nodes"] if n["type"] == "end"]
    nodes = list(nodes) + [new_node]
    nid = str(new_node["id"])
    if end_nodes:
        end_id = end_nodes[0]["id"]
        preds = incoming.get(end_id, [])
        if preds:
            pred = preds[0]
            edges = [e for e in edges if not (
                str(e.get("source") or e.get("from")) == pred and str(e.get("target") or e.get("to")) == end_id
            )]
            edges.append({"id": f"e_{pred}_{nid}", "source": pred, "target": nid, "type": "smoothstep", "animated": True, "label": ""})
        else:
            start = find_start_id(nmap)
            if start:
                edges.append({"id": f"e_{start}_{nid}", "source": start, "target": nid, "type": "smoothstep", "animated": True, "label": ""})
        edges.append({"id": f"e_{nid}_{end_id}", "source": nid, "target": end_id, "type": "smoothstep", "animated": True, "label": ""})
    elif nodes:
        # connect from a node with no outgoing
        dangling = None
        ids = {str(n.get("id")) for n in nodes if str(n.get("id")) != nid}
        sources = {str(e.get("source") or e.get("from")) for e in edges}
        for i in ids:
            if i not in sources:
                dangling = i
                break
        if dangling:
            edges.append({"id": f"e_{dangling}_{nid}", "source": dangling, "target": nid, "type": "smoothstep", "animated": True, "label": ""})
    return nodes, edges


def local_chat_handler(message: str, nodes: list, edges: list) -> Optional[dict]:
    """
    Deterministic structured operations for common ARIA commands.
    Returns {reply, patch, trigger} or None if the message needs the LLM.
    """
    msg = (message or "").strip()
    low = msg.lower()

    if any(k in low for k in ("why is this flowchart incorrect", "fix flowchart", "fix this flowchart", "fix the flowchart")):
        issues = analyze_graph_structure(nodes, edges)
        if not issues:
            return {"reply": "I checked the flowchart. Structurally it looks valid.", "patch": None}
        nodes2, edges2 = auto_fix_graph(nodes, edges, issues)
        msgs = "\n".join(f"• {i.get('message')}" for i in issues[:8])
        return {
            "reply": f"I found these issues and applied automatic fixes on the canvas:\n{msgs}",
            "patch": {"action": "replace", "nodes": nodes2, "edges": edges2},
        }

    if "add a loop" in low or "repeat until" in low or ("until" in low and "enters 0" in low):
        built = prompt_to_flowchart("loop until 0")
        if built:
            return {
                "reply": "Added a loop that repeats until the user enters 0. You can edit labels on the canvas.",
                "patch": {"action": "replace", **built},
            }

    if "optimize" in low and "flowchart" in low:
        issues = analyze_graph_structure(nodes, edges)
        nodes2, edges2 = auto_fix_graph(nodes, edges, issues)
        return {
            "reply": "I tidied structural problems (Start/End, missing branches, empty labels) on the canvas.",
            "patch": {"action": "replace", "nodes": nodes2, "edges": edges2},
        }

    m = re.search(r"add (?:an |a )?(?:input )?node(?: for| named| called)?\s+(.+)$", low)
    if not m:
        m = re.search(r"add\b.+\binput\b.+\b(?:for|named|called)\s+([a-zA-Z0-9_]+)", low)
    if m and ("input" in low or "node" in low):
        raw = m.group(1).strip().strip("\"'. ")
        raw = re.sub(r"^(an |a )", "", raw)
        label = raw if raw.lower().startswith("input") else f"Input {raw}"
        nid = next_node_id(nodes)
        y = 120
        if nodes:
            ys = [float((n.get("position") or {}).get("y", 0)) for n in nodes]
            y = max(ys) - 40 if ys else 120
        new_node = {
            "id": nid,
            "type": "input_output",
            "position": {"x": 180, "y": max(80, y)},
            "data": {"label": label},
        }
        nodes2, edges2 = insert_node_before_end(nodes, edges, new_node)
        return {
            "reply": f"Added an input node for '{raw}' on the canvas. You can drag it or edit its text.",
            "patch": {"action": "replace", "nodes": nodes2, "edges": edges2},
        }

    m = re.search(r"change (?:the )?decision(?: node)? to\s+(.+)$", low)
    if m:
        cond = m.group(1).strip().strip("\"'")
        if not cond.endswith("?"):
            cond = cond + "?"
        for n in nodes:
            if str(n.get("type")) == "decision":
                patched = copy.deepcopy(nodes)
                for p in patched:
                    if str(p.get("id")) == str(n.get("id")):
                        p.setdefault("data", {})
                        p["data"]["label"] = cond
                return {
                    "reply": f"Updated the decision node to '{cond}'.",
                    "patch": {"action": "replace", "nodes": patched, "edges": edges},
                }
        nid = next_node_id(nodes)
        new_node = {"id": nid, "type": "decision", "position": {"x": 300, "y": 280}, "data": {"label": cond}}
        return {
            "reply": f"No decision existed, so I added one: '{cond}'.",
            "patch": {"action": "add_nodes", "new_nodes": [new_node], "new_edges": []},
        }

    if "else" in low or ("no branch" in low) or ("add an else" in low):
        ast = build_flowchart_ast(nodes, edges)
        nmap, next_map, branch_map, _inc = _graph_maps(ast)
        for n in ast["nodes"]:
            if n["type"] != "decision":
                continue
            outs = next_map.get(n["id"], [])
            branches = branch_map.get(n["id"], {})
            if len(outs) < 2 or "No" not in branches:
                nid = next_node_id(nodes)
                eid = next_node_id(nodes + [{"id": nid}], "end_")
                extra_nodes = [
                    {"id": nid, "type": "input_output", "position": {"x": 460, "y": 400}, "data": {"label": "Print else"}},
                ]
                extra_edges = [{
                    "id": f"e_{n['id']}_{nid}_no",
                    "source": n["id"],
                    "target": nid,
                    "sourceHandle": "no",
                    "label": "No",
                    "type": "smoothstep",
                    "animated": True,
                }]
                ends = [x for x in ast["nodes"] if x["type"] == "end"]
                if ends:
                    extra_edges.append({
                        "id": f"e_{nid}_{ends[0]['id']}",
                        "source": nid,
                        "target": ends[0]["id"],
                        "type": "smoothstep",
                        "animated": True,
                        "label": "",
                    })
                nodes2 = list(nodes) + extra_nodes
                edges2 = list(edges) + extra_edges
                return {
                    "reply": f"Added a NO / else branch on decision '{n['raw_text']}'.",
                    "patch": {"action": "replace", "nodes": nodes2, "edges": edges2},
                }

    if any(k in low for k in ("generate python", "generate code", "create code")):
        return {
            "reply": "I'll generate Python from the current flowchart graph now.",
            "patch": None,
            "trigger": "generate_code",
        }

    if low.startswith("explain") or "explain this flowchart" in low or "explain flowchart" in low:
        ast = build_flowchart_ast(nodes, edges)
        parts = []
        for n in ast["nodes"]:
            parts.append(f"- {n['type']}: {n['raw_text']}")
        body = "\n".join(parts) if parts else "The canvas is empty."
        return {
            "reply": "Here is the flowchart in simple terms:\n" + body + "\n\nCode will follow this exact sequence of steps.",
            "patch": None,
        }

    return None


def prompt_to_flowchart(prompt: str) -> Optional[dict]:
    """Rule-based flowchart builder for common teaching prompts (used if Gemini is down)."""
    p = (prompt or "").lower()

    def N(i, t, x, y, label):
        return {"id": str(i), "type": t, "position": {"x": x, "y": y}, "data": {"label": label}}

    def E(a, b, label="", handle=""):
        e = {"id": f"e{a}-{b}", "source": str(a), "target": str(b), "type": "smoothstep", "animated": True, "label": label}
        if handle:
            e["sourceHandle"] = handle
        return e

    if any(k in p for k in ("even", "odd")):
        return {"nodes": [
            N(1, "start_end", 300, 40, "Start"),
            N(2, "input_output", 300, 140, "Input n"),
            N(3, "decision", 300, 250, "n % 2 == 0?"),
            N(4, "input_output", 140, 390, 'Print "Even"'),
            N(5, "input_output", 460, 390, 'Print "Odd"'),
            N(6, "start_end", 300, 520, "End"),
        ], "edges": [
            E(1, 2), E(2, 3),
            E(3, 4, "Yes", "yes"), E(3, 5, "No", "no"),
            E(4, 6), E(5, 6),
        ]}

    if "positive" in p and "negative" not in p and "zero" not in p:
        return {"nodes": [
            N(1, "start_end", 300, 40, "Start"),
            N(2, "input_output", 300, 150, "Input n"),
            N(3, "decision", 300, 270, "n > 0?"),
            N(4, "input_output", 180, 410, 'Print "Positive"'),
            N(5, "input_output", 420, 410, 'Print "Not positive"'),
            N(6, "start_end", 300, 540, "End"),
        ], "edges": [
            E(1, 2), E(2, 3),
            E(3, 4, "Yes", "yes"), E(3, 5, "No", "no"),
            E(4, 6), E(5, 6),
        ]}

    if "positive" in p and "negative" in p and "zero" in p:
        return {"nodes": [
            N(1, "start_end", 300, 20, "Start"),
            N(2, "input_output", 300, 110, "Input number"),
            N(3, "decision", 300, 210, "number > 0?"),
            N(4, "input_output", 120, 340, 'Print "Positive"'),
            N(5, "decision", 460, 330, "number < 0?"),
            N(6, "input_output", 340, 460, 'Print "Negative"'),
            N(7, "input_output", 560, 460, 'Print "Zero"'),
            N(8, "start_end", 300, 580, "End"),
        ], "edges": [
            E(1, 2), E(2, 3),
            E(3, 4, "Yes", "yes"), E(3, 5, "No", "no"),
            E(5, 6, "Yes", "yes"), E(5, 7, "No", "no"),
            E(4, 8), E(6, 8), E(7, 8),
        ]}

    if "positive" in p and "negative" in p:
        return {"nodes": [
            N(1, "start_end", 300, 40, "Start"),
            N(2, "input_output", 300, 150, "Input n"),
            N(3, "decision", 300, 270, "n > 0?"),
            N(4, "input_output", 140, 410, 'Print "Positive"'),
            N(5, "input_output", 460, 410, 'Print "Negative"'),
            N(6, "start_end", 300, 540, "End"),
        ], "edges": [
            E(1, 2), E(2, 3),
            E(3, 4, "Yes", "yes"), E(3, 5, "No", "no"),
            E(4, 6), E(5, 6),
        ]}

    if "prime" in p:
        return {"nodes": [
            N(1, "start_end", 300, 20, "Start"),
            N(2, "input_output", 300, 110, "Input n"),
            N(3, "process", 300, 200, "is_prime = True"),
            N(4, "process", 300, 290, "i = 2"),
            N(5, "decision", 300, 380, "i * i <= n?"),
            N(6, "decision", 140, 500, "n % i == 0?"),
            N(7, "process", 140, 620, "is_prime = False"),
            N(8, "process", 460, 500, "i = i + 1"),
            N(9, "decision", 300, 740, "is_prime == True?"),
            N(10, "input_output", 140, 860, 'Print "Prime"'),
            N(11, "input_output", 460, 860, 'Print "Not prime"'),
            N(12, "start_end", 300, 980, "End"),
        ], "edges": [
            E(1, 2), E(2, 3), E(3, 4), E(4, 5),
            E(5, 6, "Yes", "yes"), E(5, 9, "No", "no"),
            E(6, 7, "Yes", "yes"), E(6, 8, "No", "no"),
            E(7, 9), E(8, 5),
            E(9, 10, "Yes", "yes"), E(9, 11, "No", "no"),
            E(10, 12), E(11, 12),
        ]}

    if "factorial" in p:
        return {"nodes": [
            N(1, "start_end", 300, 30, "Start"),
            N(2, "input_output", 300, 120, "Input n"),
            N(3, "process", 300, 210, "fact = 1"),
            N(4, "process", 300, 300, "i = 1"),
            N(5, "decision", 300, 400, "i <= n?"),
            N(6, "process", 140, 530, "fact = fact * i"),
            N(7, "process", 140, 620, "i = i + 1"),
            N(8, "input_output", 460, 530, "Print fact"),
            N(9, "start_end", 300, 720, "End"),
        ], "edges": [
            E(1, 2), E(2, 3), E(3, 4), E(4, 5),
            E(5, 6, "Yes", "yes"), E(5, 8, "No", "no"),
            E(6, 7), E(7, 5), E(8, 9),
        ]}

    if "largest" in p or "greatest" in p:
        return {"nodes": [
            N(1, "start_end", 300, 20, "Start"),
            N(2, "input_output", 300, 100, "Input a"),
            N(3, "input_output", 300, 180, "Input b"),
            N(4, "input_output", 300, 260, "Input c"),
            N(5, "decision", 300, 360, "a >= b and a >= c?"),
            N(6, "input_output", 120, 500, "Print a"),
            N(7, "decision", 460, 490, "b >= c?"),
            N(8, "input_output", 360, 620, "Print b"),
            N(9, "input_output", 560, 620, "Print c"),
            N(10, "start_end", 300, 740, "End"),
        ], "edges": [
            E(1, 2), E(2, 3), E(3, 4), E(4, 5),
            E(5, 6, "Yes", "yes"), E(5, 7, "No", "no"),
            E(7, 8, "Yes", "yes"), E(7, 9, "No", "no"),
            E(6, 10), E(8, 10), E(9, 10),
        ]}

    if "calculator" in p or ("sum" in p and "add" in p) or "a + b" in p:
        return {"nodes": [
            N(1, "start_end", 300, 30, "Start"),
            N(2, "input_output", 300, 120, "Input a"),
            N(3, "input_output", 300, 200, "Input b"),
            N(4, "input_output", 300, 280, "Input op"),
            N(5, "decision", 300, 380, "op == +?"),
            N(6, "process", 120, 500, "result = a + b"),
            N(7, "process", 460, 500, "result = a - b"),
            N(8, "input_output", 300, 620, "Print result"),
            N(9, "start_end", 300, 720, "End"),
        ], "edges": [
            E(1, 2), E(2, 3), E(3, 4), E(4, 5),
            E(5, 6, "Yes", "yes"), E(5, 7, "No", "no"),
            E(6, 8), E(7, 8), E(8, 9),
        ]}

    if "loop" in p and ("0" in p or "until" in p):
        return {"nodes": [
            N(1, "start_end", 300, 30, "Start"),
            N(2, "input_output", 300, 130, "Input n"),
            N(3, "decision", 300, 250, "n != 0?"),
            N(4, "input_output", 300, 380, "Print n"),
            N(5, "input_output", 300, 470, "Input n"),
            N(6, "start_end", 520, 250, "End"),
        ], "edges": [
            E(1, 2), E(2, 3),
            E(3, 4, "Yes", "yes"), E(3, 6, "No", "no"),
            E(4, 5), E(5, 3),
        ]}

    return None
