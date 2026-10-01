"""The runner lets a port's deliberate extra usage lines pass, and nothing else."""

from golden_master.runner import without_known_extensions

SCENARIO = {"known_extensions": [{"target": "usage: new [--opt]", "legacy": "usage: new"},
                                 {"target": "an extra hint", "legacy": None}]}


def test_a_listed_line_is_put_back_or_dropped():
    assert without_known_extensions("usage: new [--opt]\nan extra hint\nExample\n", SCENARIO) == "usage: new\nExample\n"


def test_any_other_line_is_kept_so_that_it_still_differs():
    assert without_known_extensions("usage: new\nsomething else\n", SCENARIO) == "usage: new\nsomething else\n"


def test_a_scenario_without_extensions_is_unchanged():
    assert without_known_extensions("a\nb\n", {}) == "a\nb\n"
