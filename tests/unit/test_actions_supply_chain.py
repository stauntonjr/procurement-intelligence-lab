from tools.check_actions_supply_chain import validate, workflow_references


def test_all_workflow_actions_are_immutable_and_allowlisted() -> None:
    assert workflow_references()
    assert validate() == []
