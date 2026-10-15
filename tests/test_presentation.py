from visual.presentation import format_variable_value


def test_formats_node_and_list_references_as_ids():
    assert format_variable_value({"ref": 4, "class": "Node"}) == "4"
    assert format_variable_value({"ref": 1, "class": "LinkedList"}) == "1"


def test_formats_self_and_duplicate_references_consistently():
    self_value = {"ref": 1, "class": "Node"}
    alias_value = {"ref": 1, "class": "Node"}
    assert format_variable_value(self_value) == format_variable_value(alias_value) == "1"


def test_formats_primitive_values_and_none():
    assert format_variable_value(133) == "133"
    assert format_variable_value("hello") == "hello"
    assert format_variable_value(True) == "True"
    assert format_variable_value(None) == "None"


def test_formats_nested_reference_values_without_changing_them():
    assert format_variable_value([{"ref": 4, "class": "Node"}, None, 2]) == "[4, None, 2]"


def test_keeps_unknown_or_invalid_references_visible():
    assert format_variable_value({"ref": "4", "class": "Node"}) == "{'ref': '4', 'class': 'Node'}"
    assert format_variable_value({"value": 4}) == "{'value': 4}"
