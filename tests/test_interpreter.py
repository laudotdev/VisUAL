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


def test_traversal_snapshot_marks_the_node_printed():
    result = ControlledInterpreter().run(PROGRAM)
    output_steps = [step for step in result.snapshots if step["event_type"] == "output"]
    assert [step["traversed_node_ref"] for step in output_steps] == [2, 3]
    assert all(step["traversed_node_ref"] in {node["id"] for node in step["nodes"]} for step in output_steps)


def test_explanations_include_factual_values_and_output():
    result = ControlledInterpreter().run(PROGRAM)
    value_update = next(step for step in result.snapshots if step["event_type"] == "value_update")
    assert "changed from" in value_update["explanation"]
    assert "to" in value_update["explanation"]
    output = next(step for step in result.snapshots if step["event_type"] == "output")
    assert "Printed" in output["explanation"]
    assert "11" in output["explanation"]


def test_condition_explanation_identifies_expression_and_result():
    result = ControlledInterpreter().run(PROGRAM)
    condition = next(step for step in result.snapshots if step["event_type"] == "condition")
    assert "evaluated to" in condition["explanation"]


def test_dsa_import_alias_preserves_local_linked_list_and_trace_data():
    source = '''
from dsa import LinkedList as DsaLinkedList
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
    def insert_beginning(self, data):
        new_node = Node(data)
        new_node.next = self.head
        self.head = new_node
    def traverse(self):
        current = self.head
        while current is not None:
            print(current.data)
            current = current.next
ll = LinkedList()
ll.head = Node(12)
ll.head.next = Node(14)
ll.insert_beginning(13)
ll.traverse()
'''
    result = ControlledInterpreter().run(source)
    assert result.status == "completed", result.error
    final = result.snapshots[-1]
    assert result.output == ["13", "12", "14"]
    assert [(node["id"], node["data"], node["next"]) for node in final["nodes"]] == [
        (4, 13, 2), (2, 12, 3), (3, 14, None)
    ]


def test_class_definition_is_a_blueprint_and_node_creation_is_recorded_separately():
    source = '''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
ll = LinkedList()
node = Node(12)
'''
    result = ControlledInterpreter().run(source)
    assert result.status == "completed", result.error
    class_step = next(step for step in result.snapshots if step["event_type"] == "class_definition" and "Node" in step["explanation"])
    assert "blueprint" in class_step["explanation"].lower()
    assert class_step["nodes"] == []
    assert class_step["visualization"]["kind"] == "class_blueprint"
    assert class_step["visualization"]["class_name"] == "Node"
    assert class_step["visualization"]["attributes"] == ["data", "next"]
    creation = next(step for step in result.snapshots if step["event_type"] == "object_creation" and step["nodes"])
    assert creation["nodes"][0]["data"] == 12


def test_method_call_and_variable_explanation_describe_actual_references():
    result = ControlledInterpreter().run('''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
    def insert(self, data):
        new_node = Node(data)
        self.head = new_node
ll = LinkedList()
ll.insert(13)
''')
    assert result.status == "completed", result.error
    method_step = next(step for step in result.snapshots if step["event_type"] == "method_call")
    assert "self" in method_step["explanation"]
    assert "13" in method_step["explanation"]
    variables = method_step["variable_explanations"]
    assert variables["self"]["value"]["class"] == "LinkedList"
    assert "object" in variables["self"]["explanation"].lower()


def test_self_explanation_identifies_alias_to_calling_variable():
    result = ControlledInterpreter().run('''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
    def insert(self, data):
        self.head = Node(data)
ll = LinkedList()
ll.insert(13)
''')
    method_step = next(step for step in result.snapshots if step["event_type"] == "method_call" and "insert" in step["explanation"])
    assert "same object as ll" in method_step["variable_explanations"]["self"]["explanation"]
    assert "same object as self" not in method_step["variable_explanations"]["ll"]["explanation"]


def test_head_update_explanation_describes_its_learning_significance():
    result = ControlledInterpreter().run('''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
    def insert(self, data):
        new_node = Node(data)
        self.head = new_node
ll = LinkedList()
ll.insert(13)
''')
    head_step = next(step for step in result.snapshots if step["event_type"] == "link_change" and "first node" in step["explanation"])
    assert "head reference" in head_step["explanation"]
    assert "first node" in head_step["explanation"]
    assert "13" in head_step["explanation"]


def test_prepend_records_creation_next_head_and_output_in_order():
    result = ControlledInterpreter().run('''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
    def prepend(self, data):
        new_value = Node(data)
        new_value.next = self.head
        self.head = new_value
        print(new_value.data)
ll = LinkedList()
ll.head = Node(12)
ll.prepend(13)
''')
    events = result.snapshots
    creation_index = max(i for i, step in enumerate(events) if step["event_type"] == "object_creation" and any(node["data"] == 13 for node in step["nodes"]))
    next_index = next(i for i, step in enumerate(events[creation_index:], creation_index) if step["event_type"] == "link_change" and "next reference" in step["explanation"] and "13" in step["explanation"])
    head_index = next(i for i, step in enumerate(events[next_index:], next_index) if step["event_type"] == "link_change" and "first node" in step["explanation"])
    output_index = next(i for i, step in enumerate(events[head_index:], head_index) if step["event_type"] == "output")
    assert creation_index < next_index < head_index < output_index


def test_variable_explanation_tracks_node_attributes_without_confusing_output():
    result = ControlledInterpreter().run('''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
ll = LinkedList()
ll.head = Node(12)
current = ll.head
''')
    assert result.status == "completed", result.error
    state = next(step for step in result.snapshots if step["variables"].get("current"))
    assert state["program_output"] == []
    assert state["variable_explanations"]["current.data"]["value"] == 12
    assert "stored" in state["variable_explanations"]["current.data"]["explanation"].lower()


def test_variable_explanation_follows_highlighted_attribute_assignment():
    result = ControlledInterpreter().run('''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
ll = LinkedList()
ll.head = Node(12)
''')
    step = next(step for step in result.snapshots if step["source"]["line"] == 4)
    entries = step["variable_explanations"]
    assert set(entries) == {"self", "self.data", "data"}
    assert "ll" not in entries
    assert "self.next" not in entries


def test_variable_explanation_includes_identity_access_paths_and_attribute_owner():
    result = ControlledInterpreter().run('''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
ll = LinkedList()
ll.head = Node(12)
''')
    step = next(step for step in result.snapshots if "self.data" in step["variable_explanations"])
    node_id = step["variable_explanations"]["self"]["reference_id"]
    self_entry = step["variable_explanations"]["self"]
    data_entry = step["variable_explanations"]["self.data"]
    assert self_entry["object_type"] == "Node"
    assert self_entry["access_paths"] == ["self"]
    assert self_entry["reference_id"] == node_id
    assert data_entry["belongs_to"] == {"object_type": "Node", "reference_id": node_id}


def test_object_access_paths_include_aliases_from_the_current_state():
    result = ControlledInterpreter().run('''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
class LinkedList:
    def __init__(self):
        self.head = None
    def inspect(self):
        alias = self
        return alias
ll = LinkedList()
ll.inspect()
''')
    step = next(step for step in result.snapshots if step["event_type"] == "method_call" and "inspect" in step["explanation"])
    assert step["variable_explanations"]["self"]["access_paths"] == ["ll", "self"]
