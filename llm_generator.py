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
    Generates Python code using Gemini API if key is provided, or a intelligent AST compiler fallback.
    """
    if api_key:
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
        except Exception as e:
            pass  # Fallback to AST compiler below if API fails

    # Rule-based fallback AST code compiler
    return fallback_ast_compiler(ast_json)

def fallback_ast_compiler(ast_json):
    """
    Deterministic rule-based compiler for basic flowchart AST structures.
    """
    lines = ["# Auto-generated Python code from Flowchart", ""]
    nodes = {n["id"]: n for n in ast_json.get("nodes", [])}
    edges = ast_json.get("edges", [])

    # Map graph edges
    next_map = {}
    for e in edges:
        next_map[e["from"]] = e["to"]

    # Start traversal from start node or node 1
    start_node = next((n for n in nodes.values() if n["type"] == "start"), None)
    curr_id = start_node["id"] if start_node else (nodes[1]["id"] if 1 in nodes else None)

    visited = set()
    indent = ""
    while curr_id and curr_id in nodes and curr_id not in visited:
        visited.add(curr_id)
        node = nodes[curr_id]
        ntype = node["type"]
        text = node["raw_text"]

        if ntype == "start":
            lines.append(f"{indent}# Program Start")
        elif ntype == "input":
            var_match = re.search(r'input\s*([a-zA-Z_]\w*)', text, re.IGNORECASE)
            var_name = var_match.group(1) if var_match else "n"
            lines.append(f'{indent}{var_name} = int(input("Enter {var_name}: "))')
        elif ntype == "output":
            clean_print = re.sub(r'^(print|output|display)\s*', '', text, flags=re.IGNORECASE).strip()
            # Wrap string literal if not already quoted or numeric
            if clean_print and not (clean_print.startswith('"') or clean_print.startswith("'") or clean_print.isnumeric()):
                clean_print = f'"{clean_print}"'
            default_val = '"Done"'
            lines.append(f'{indent}print({clean_print if clean_print else default_val})')
        elif ntype == "decision":
            clean_cond = text.replace("?", "").strip()
            lines.append(f'{indent}if {clean_cond}:')
            indent += "    "
        elif ntype == "end":
            indent = ""
            lines.append(f"{indent}# Program End")

        curr_id = next_map.get(curr_id)

    return "\n".join(lines)
