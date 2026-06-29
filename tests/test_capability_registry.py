from aotp.capability_registry import REGISTRY


def test_every_adapter_declares_support_requirements_and_denials():
    assert REGISTRY
    for capability in REGISTRY.values():
        assert capability.supports
        assert capability.requires
        assert capability.denies
