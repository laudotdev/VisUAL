from visual.analyzer import analyze_source
from visual.interpreter import ControlledInterpreter

PROGRAM = '''
from dsa import LinkedList

class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

class LinkedList:
    def __init__(self):
        self.head = None
    def append(self, data):
        node = Node(data)
        if self.head is None:
            self.head = node
        else:
            current = self.head
            while current.next is not None:
                current = current.next
            current.next = node
    def update_first(self, value):
        if self.head is not None:
            self.head.data = value

ll = LinkedList()
ll.append(10)
ll.append(20)
ll.update_first(11)
current = ll.head
while current is not None:
    print(current.data)
    current = current.next
'''


def test_interpreter_records_snapshots_and_output():
    analysis = analyze_source(PROGRAM)
    assert analysis.supported, analysis.diagnostics
    result = ControlledInterpreter(max_steps=500).run(PROGRAM)
    assert result.status == "completed", result.error
    assert result.output == ["11", "20"]
    assert len(result.snapshots) > 5
    assert result.snapshots[-1]["status"] == "completed"


def test_duplicate_values_have_distinct_node_ids():
    source = PROGRAM.replace("ll.append(20)", "ll.append(10)").replace("ll.update_first(11)", "ll.update_first(10)")
    result = ControlledInterpreter().run(source)
    final = result.snapshots[-1]
    nodes = final["nodes"]
    assert len(nodes) == 2
    assert nodes[0]["data"] == nodes[1]["data"] == 10
    assert nodes[0]["id"] != nodes[1]["id"]


def test_step_limit_stops_infinite_loop():
    source = PROGRAM + "\nwhile True:\n    pass\n"
    result = ControlledInterpreter(max_steps=30).run(source)
    assert result.status == "failed"
    assert "limit" in result.error.lower()


def test_unsupported_expression_is_rejected_before_interpretation():
    source = PROGRAM + "\nimport os\n"
    result = ControlledInterpreter().run(source)
    assert result.status == "failed"
    assert "import" in result.error.lower()


def test_insert_at_head_and_delete_head_preserve_node_identity():
    source = '''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
    def prepend(self, data):
        node = Node(data)
        node.next = self.head
        self.head = node
    def delete_head(self):
        if self.head is not None:
            self.head = self.head.next
ll = LinkedList()
ll.prepend(20)
ll.prepend(10)
ll.delete_head()
'''
    result = ControlledInterpreter().run(source)
    assert result.status == "completed", result.error
    final = result.snapshots[-1]
    assert [node["data"] for node in final["nodes"]] == [20]
    assert final["head_ref"] == final["nodes"][0]["id"]
    assert any(step["event_type"] == "link_change" for step in result.snapshots)


def test_delete_non_head_node_updates_predecessor_link():
    source = '''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
    def append(self, data):
        node = Node(data)
        if self.head is None:
            self.head = node
        else:
            current = self.head
            while current.next is not None:
                current = current.next
            current.next = node
    def delete(self, key):
        current = self.head
        previous = None
        while current is not None:
            if current.data == key:
                if previous is None:
                    self.head = current.next
                else:
                    previous.next = current.next
                return
            previous = current
            current = current.next
ll = LinkedList()
ll.append(1)
ll.append(2)
ll.append(3)
ll.delete(2)
'''
    result = ControlledInterpreter().run(source)
    assert result.status == "completed", result.error
    final = result.snapshots[-1]
    assert [node["data"] for node in final["nodes"]] == [1, 3]
    assert final["nodes"][0]["next"] == final["nodes"][1]["id"]


def test_empty_list_snapshot_is_explicitly_empty():
    source = '''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
ll = LinkedList()
'''
    result = ControlledInterpreter().run(source)
    assert result.status == "completed", result.error
    final = result.snapshots[-1]
    assert final["nodes"] == []
    assert final["head_ref"] is None


def test_update_keeps_node_identity_and_links():
    result = ControlledInterpreter().run(PROGRAM)
    before = next(s for s in result.snapshots if s["event_type"] == "link_change" and len(s["nodes"]) == 2)
    after = next(s for s in result.snapshots if s["event_type"] == "value_update" and len(s["nodes"]) == 2)
    before_by_id = {node["id"]: node for node in before["nodes"]}
    after_by_id = {node["id"]: node for node in after["nodes"]}
    assert before_by_id.keys() == after_by_id.keys()
    assert {key: node["next"] for key, node in before_by_id.items()} == {key: node["next"] for key, node in after_by_id.items()}
    assert any(before_by_id[key]["data"] != after_by_id[key]["data"] for key in before_by_id)
