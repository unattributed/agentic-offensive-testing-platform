from aotp.tool_inventory import generate_foss_tool_inventory


def test_foss_tool_inventory_does_not_grant_authority():
    inventory = generate_foss_tool_inventory(probe=False)
    assert inventory["schema_version"] == "1.0"
    assert "never bypasses ROE" in inventory["authority_note"]
    assert inventory["tools"]
    for item in inventory["tools"]:
        assert item["authority_note"] == "availability never grants execution authority"
        assert item["probe"] == {"available": None}
