from visual.interpreter import ControlledInterpreter
from visual.visualizer_panel import VisualizerPanel


SOURCE = '''
from dsa import LinkedList
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
    def append(self, data):
        self.head = Node(data)
ll = LinkedList()
'''


def test_trace_contains_blueprint_metadata():
    result = ControlledInterpreter().run(SOURCE)
    blueprint = result.snapshots[-1]["blueprint"]
    assert blueprint["Node"]["attributes"] == ["data", "next"]
    assert blueprint["LinkedList"]["attributes"] == ["head"]
    assert "append" in blueprint["LinkedList"]["methods"]


def test_blueprint_formatter_is_trace_based():
    text = VisualizerPanel._format_blueprint({"Node": {"attributes": ["data"], "methods": ["__init__"]}})
    assert "Node" in text
    assert "data" in text
    assert "__init__" in text
