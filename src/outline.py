import json
from typing import List, Optional

class OutlineNode:
    def __init__(self, title: str, content: str = "", children: Optional[List['OutlineNode']] = None):
        self.title = title
        self.content = content
        self.children = children or []

    def add_child(self, node: 'OutlineNode'):
        self.children.append(node)

    def to_dict(self):
        return {
            "title": self.title,
            "content": self.content,
            "children": [child.to_dict() for child in self.children]
        }

    @staticmethod
    def from_dict(data):
        children = [OutlineNode.from_dict(child) for child in data.get("children", [])]
        return OutlineNode(data["title"], data.get("content", ""), children)

def save_outline_to_file(root: OutlineNode, filepath: str):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(root.to_dict(), f, indent=2)

def load_outline_from_file(filepath: str) -> OutlineNode:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return OutlineNode.from_dict(data)
    except FileNotFoundError:
        # Return default root if no file
        return OutlineNode("Root Task: Start coding session")
    except Exception as e:
        print(f"[ERROR] Failed to load outline from {filepath}: {e}")
        return OutlineNode("Root Task: Start coding session")
