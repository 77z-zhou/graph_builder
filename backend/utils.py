import os
import re
from pathlib import Path


def formatted_time(current_time):
    formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S %Z')
    return str(formatted_time)


def validate_file_path(directory: str, filename: str) -> str:
    """验证文件路径"""
    file_path = os.path.join(directory, filename)
    abs_directory = os.path.abspath(directory)
    abs_file_path = os.path.abspath(file_path)
    if not abs_file_path.startswith(abs_directory):
        raise ValueError("Invalid file path")
    return abs_file_path


def sanitize_additional_instruction(instruction: str) -> str:
    """ 提示词消毒 """
    if not instruction or instruction.strip() == "": 
        return ""
    instruction = instruction.replace("{", "[").replace("}", "]")  # Convert `{}` to `[]` for safety
    # Step 2: Block dangerous function calls
    injection_patterns = [r"os\.getenv\(", r"eval\(", r"exec\(", r"subprocess\.", r"import os", r"import subprocess"]
    for pattern in injection_patterns:
        instruction = re.sub(pattern, "[BLOCKED]", instruction, flags=re.IGNORECASE)
    # Step 4: Normalize spaces
    instruction = re.sub(r'\s+', ' ', instruction).strip()
    return instruction


def clean_nodes_and_relationships(graph_document_list):
    """ 去除node 和 relatioinship id 和 type 中的不良字符 """
    for graph_document in graph_document_list:
        # Clean node id and types
        cleaned_nodes = []
        for node in graph_document.nodes:
            if node.type.strip() and node.id.strip():
                node.type = node.type.replace('`', '')
                cleaned_nodes.append(node)
        # Clean relationship id types and source/target node id and types
        cleaned_relationships = []
        for rel in graph_document.relationships:
            if rel.type.strip() and rel.source.id.strip() and rel.source.type.strip() and rel.target.id.strip() and rel.target.type.strip():
                rel.type = rel.type.replace('`', '')
                rel.source.type = rel.source.type.replace('`', '')
                rel.target.type = rel.target.type.replace('`', '')
                cleaned_relationships.append(rel)
        graph_document.relationships = cleaned_relationships
        graph_document.nodes = cleaned_nodes
    return graph_document_list


def delete_uploaded_local_file(merged_file_path):
    file_path = Path(merged_file_path)
    if file_path.exists():
        file_path.unlink()