import json
import re

SYSTEM_PROMPT = """
You are a Python code generator that converts flowchart AST JSON representations into clean, readable, executable Python 3 code.

Rules:
1. Output ONLY executable Python code inside a ```python ... ``` code block.
2. Automatically parse variable types for input (e.g. `n = int(input("Enter n: "))` or `n = float(input("Enter n: "))`).
3. Fix OCR errors in conditions if any (e.g., `n ) 0` should become `n > 0`).
4. Properly structure conditionals (if/else) and loops (while/for).
5. Do NOT include Markdown conversational text outside the code block.
"""

def generate_python_code(ast_json, api_key=None):
    """
    Generates Python code using Gemini API if key is provided, or an intelligent AST compiler fallback.
    """
    if api_key and api_key.strip():
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"{SYSTEM_PROMPT}\n\nFlowchart AST JSON:\n{json.dumps(ast_json, indent=2)}"
            response = model.generate_content(prompt)
            
            raw_text = response.text
            match = re.search(r'```python\s*(.*?)\s*```', raw_text, re.DOTALL)
            if match:
                return match.group(1).strip()
            return raw_text.strip()
        except Exception:
            pass  # Fallback to AST compiler below

    return fallback_ast_compiler(ast_json)

def fallback_ast_compiler(ast_json):
    """
    Deterministic rule-based compiler for flowchart AST structures.
    Handles sequential flow, input/output, and decision branching (if/else).
    """
    lines = ["# Generated code from flowchart"]
    nodes = {str(n.get("id")): n for n in ast_json.get("nodes", [])}
    edges = ast_json.get("edges", [])

    # Map graph edges: next_map[from_id] = to_id (or dict of branch -> to_id for decision)
    next_map = {}
    branch_map = {} # node_id -> {"Yes": to_id, "No": to_id}

    for e in edges:
        from_id = str(e.get("from"))
        to_id = str(e.get("to"))
        branch = e.get("branch")
        
        if from_id not in branch_map:
            branch_map[from_id] = {}
        if branch:
            branch_map[from_id][branch.strip().capitalize()] = to_id
        
        next_map[from_id] = to_id

    # Find start node
    start_node = next((n for n in nodes.values() if n.get("type") == "start" or "start" in str(n.get("raw_text", "")).lower()), None)
    curr_id = str(start_node["id"]) if start_node else ("1" if "1" in nodes else list(nodes.keys())[0] if nodes else None)

    visited = set()
    
    def process_node_flow(nid, indent=""):
        nonlocal lines, visited
        while nid and nid in nodes and nid not in visited:
            visited.add(nid)
            node = nodes[nid]
            ntype = node.get("type", "process")
            text = str(node.get("raw_text", node.get("text", ""))).strip()
            text_lower = text.lower()

            if ntype == "start" or "start" in text_lower:
                pass
            elif ntype == "input" or "input" in text_lower or "read" in text_lower:
                var_match = re.search(r'input\s*([a-zA-Z_]\w*)', text, re.IGNORECASE)
                var_name = var_match.group(1) if var_match else "n"
                lines.append(f'{indent}{var_name} = int(input("Enter {var_name}: "))')
            elif ntype == "output" or "print" in text_lower or "output" in text_lower:
                clean_print = re.sub(r'^(print|output|display)\s*', '', text, flags=re.IGNORECASE).strip()
                if clean_print.startswith('"') or clean_print.startswith("'"):
                    val = clean_print
                elif clean_print.replace('.', '', 1).isdigit():
                    val = clean_print
                else:
                    val = f'"{clean_print}"' if clean_print else '"Done"'
                lines.append(f'{indent}print({val})')
            elif ntype == "decision" or "?" in text or ">" in text or "<" in text or "==" in text:
                clean_cond = text.replace("?", "").strip()
                lines.append(f'{indent}if {clean_cond}:')
                
                # Branching targets
                branches = branch_map.get(nid, {})
                yes_target = branches.get("Yes") or branches.get("True")
                no_target = branches.get("No") or branches.get("False")

                # Fallback if branch targets not explicitly labeled
                if not yes_target or not no_target:
                    targets = [str(e["to"]) for e in edges if str(e["from"]) == nid]
                    if len(targets) >= 2:
                        yes_target = str(targets[0])
                        no_target = str(targets[1])
                    elif len(targets) == 1:
                        yes_target = str(targets[0])

                if yes_target:
                    process_node_flow(yes_target, indent + "    ")
                
                lines.append(f'{indent}else:')
                if no_target:
                    process_node_flow(no_target, indent + "    ")
                else:
                    lines.append(f'{indent}    pass')
                
                break
            elif ntype == "process":
                if "=" in text:
                    lines.append(f'{indent}{text}')
                else:
                    lines.append(f'{indent}# {text}')
            elif ntype == "end" or "end" in text_lower:
                break

            nid = next_map.get(nid)

    if curr_id:
        process_node_flow(curr_id)

    return "\n".join(lines)
