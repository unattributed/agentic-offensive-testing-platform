from aotp.human_approval import ApprovalRequest, requires_approval


def test_risky_actions_wait_for_human_approval():
    request = ApprovalRequest("id", "active_fuzzing", "state may change")
    assert requires_approval(request.action)
    assert request.status == "pending"
    request.approve()
    assert request.status == "approved"
