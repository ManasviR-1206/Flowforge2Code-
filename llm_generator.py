import json
import re
import ast

import logic_engine

SYSTEM_PROMPT = """
You are a Python code generator that converts flowchart AST JSON into clean, executable Python 3.

Rules:
1. Output ONLY executable Python code. No markdown fences. No explanation.
2. Follow the AST exactly. Do not invent extra logic. Do not remove flowchart steps.
3. INPUT nodes → variable = int(input("Enter <var>: "))
4. OUTPUT nodes → print(...)
5. PROCESS nodes → the statement as written (assignments, calculations).
6. DECISION nodes → if/elif/else using the condition text. Preserve YES/NO branches.
7. Loops (back-edges) → while/for.
8. Preserve flowchart order.
"""


def generate_python_code(ast_json, api_key=None):
    """
    Deterministic compiler is always the source of truth.
    If Gemini is available, try it, then keep it only if it parses and matches the graph.
    """
    deterministic = logic_engine.compile_to_python(ast_json)
    llm_code = ""

    if api_key and str(api_key).strip():
        try:
            import google.generativeai as genai
            genai.configure(api_key=str(api_key).strip())
            model = None
            for name in ("gemini-3.8-flash",):
                try:
                    model = genai.GenerativeModel(name)
                    break
                except Exception:
                    continue
            if model is None:
                model = genai.GenerativeModel("gemini-3.8-flash")
            prompt = f"{SYSTEM_PROMPT}\n\nFlowchart AST JSON:\n{json.dumps(ast_json, indent=2)}"
            response = model.generate_content(prompt)
            llm_code = clean_code_formatting(response.text or "")
        except Exception:
            llm_code = ""

    chosen = deterministic
    if llm_code:
        try:
            ast.parse(llm_code)
            warns = logic_engine.consistency_warnings(ast_json, llm_code)
            if not warns:
                chosen = llm_code
        except SyntaxError:
            chosen = deterministic

    chosen = clean_code_formatting(chosen)
    try:
        ast.parse(chosen)
    except SyntaxError:
        chosen = deterministic
    return chosen


def clean_code_formatting(code_str: str) -> str:
    code_str = (code_str or "").strip()
    if code_str.startswith("```"):
        lines = code_str.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        code_str = "\n".join(lines).strip()
    return code_str


def fallback_ast_compiler(ast_json):
    return logic_engine.compile_to_python(ast_json)
