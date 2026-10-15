import pytest

from visual.analyzer import analyze_source

VALID = '''
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

ll = LinkedList()
ll.append(1)
'''


def test_detects_conventional_linked_list():
    result = analyze_source(VALID)
    assert result.supported
    assert result.node_class == "Node"
    assert result.list_class == "LinkedList"


@pytest.mark.parametrize("source", ["", "print('hello')", "x = 2\n"])
def test_does_not_detect_unrelated_programs(source):
    assert not analyze_source(source).supported


def test_import_is_rejected():
    result = analyze_source("import os\n" + VALID)
    assert not result.supported
    assert any("import" in d.message.lower() for d in result.diagnostics)


def test_syntax_error_has_location():
    result = analyze_source("class Node(:\n pass")
    assert not result.supported
    assert result.diagnostics[0].line == 1


def test_requires_node_and_linkedlist():
    result = analyze_source("class Node:\n    pass\n")
    assert not result.supported


def test_recursion_is_rejected():
    source = '''
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
    def walk(self):
        self.walk()
class LinkedList:
    def __init__(self):
        self.head = None
ll = LinkedList()
'''
    result = analyze_source(source)
    assert not result.supported
    assert any("recurs" in item.message.lower() for item in result.diagnostics)


def test_float_literal_is_rejected():
    result = analyze_source(VALID.replace("ll.append(1)", "ll.append(1.5)"))
    assert not result.supported
    assert any("integer" in item.message.lower() for item in result.diagnostics)


def test_dsa_import_and_hello_world_has_no_intent():
    result = analyze_source("from dsa import LinkedList\nprint('Hello World')")
    assert result.intent_level == "none"
    assert not result.supported


def test_node_alone_is_only_possible_intent():
    result = analyze_source("class Node:\n    def __init__(self, data):\n        self.data = data\n        self.next = None\n")
    assert result.intent_level == "possible"


def test_structural_usage_without_import_is_strong():
    result = analyze_source(VALID)
    assert result.intent_level == "strong"
    assert result.signals
    assert result.evidence


def test_dsa_import_is_hint_not_trigger():
    result = analyze_source("from dsa import LinkedList\nprint('hello')")
    assert result.intent_level != "strong"


def test_dsa_import_with_shadowing_is_not_used_as_definition():
    result = analyze_source("from dsa import LinkedList\nclass LinkedList:\n    pass\n")
    assert result.intent_level == "possible"
    assert any("shadow" in item.lower() for item in result.signals)


def test_unsupported_strong_candidate_keeps_intent_but_is_not_supported():
    source = VALID.replace("ll.append(1)", "for value in [1]:\n    ll.append(value)")
    result = analyze_source(source)
    assert result.intent_level == "strong"
    assert not result.supported
    assert result.diagnostics
