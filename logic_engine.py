import json

def build_flowchart_ast(blocks, connections):
    """
    Builds a structured AST JSON representation from detected flowchart blocks and connections.
    """
    ast_nodes = []
    
    for b in blocks:
        text = b.get("text", "").strip()
        shape_type = b.get("type", "process")
        
        # Override shape type based on text content heuristics
        text_lower = text.lower()
        if "start" in text_lower:
            node_type = "start"
        elif "end" in text_lower:
            node_type = "end"
        elif "input" in text_lower or "read" in text_lower:
            node_type = "input"
        elif "print" in text_lower or "output" in text_lower or "display" in text_lower:
            node_type = "output"
        elif "?" in text or ">" in text or "<" in text or "==" in text or shape_type == "decision":
            node_type = "decision"
        else:
            node_type = shape_type

        ast_nodes.append({
            "id": b["id"],
            "type": node_type,
            "raw_text": text if text else f"Step {b['id']}",
            "bbox": b.get("bbox", (0, 0, 0, 0))
        })

    ast_edges = []
    for conn in connections:
        ast_edges.append({
            "from": conn["from"],
            "to": conn["to"],
            "branch": conn.get("branch", None)
        })

    ast = {
        "program_name": "FlowchartProgram",
        "nodes": ast_nodes,
        "edges": ast_edges
    }
    
    return ast
