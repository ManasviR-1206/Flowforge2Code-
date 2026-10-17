import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logic_engine
import executor

# 7-node factorial graph representing the exact flowchart from the user:
# 1: Start
# 2: Input n
# 3: fact = 1\ni = 1 (in the same process rectangle)
# 4: i <= n?
# 5: fact = fact * i\ni = i + 1 (in the same process rectangle)
# 6: Print fact
# 7: End

nodes = [
    {"id": "1", "type": "start_end", "data": {"label": "Start"}},
    {"id": "2", "type": "input_output", "data": {"label": "Input n"}},
    {"id": "3", "type": "process", "data": {"label": "fact = 1\ni = 1"}},
    {"id": "4", "type": "decision", "data": {"label": "i <= n?"}},
    {"id": "5", "type": "process", "data": {"label": "fact = fact * i\ni = i + 1"}},
    {"id": "6", "type": "input_output", "data": {"label": "Print fact"}},
    {"id": "7", "type": "start_end", "data": {"label": "End"}},
]

edges = [
    {"source": "1", "target": "2"},
    {"source": "2", "target": "3"},
    {"source": "3", "target": "4"},
    {"source": "4", "target": "5", "label": "Yes"},
    {"source": "4", "target": "6", "label": "No"},
    {"source": "5", "target": "4"}, # loop back!
    {"source": "6", "target": "7"},
]

ast_data = logic_engine.build_flowchart_ast(nodes, edges)
print("AST built.")
try:
    code = logic_engine.compile_to_python(ast_data)
    print("Compiled Code:\n" + code)
    out5 = executor.run_code_safely(code, "5\n")
    print("Output for 5:", repr(out5))
    out0 = executor.run_code_safely(code, "0\n")
    print("Output for 0:", repr(out0))
except Exception as e:
    print("Compilation/execution failed:", type(e), e)
