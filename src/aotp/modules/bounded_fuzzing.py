"""Canonical bounded fuzzing module contract."""

from ..bounded_fuzzing import FUZZING_SAFE_PAYLOAD_CLASSES, FUZZING_UNSAFE_ACTIONS


MODULE = {
    "name": "bounded_fuzzing",
    "supports": tuple(sorted(FUZZING_SAFE_PAYLOAD_CLASSES)),
    "requires": ("explicit_fuzzing_authorization", "payload_budget", "request_budget", "rate_limits"),
    "denies": tuple(sorted(FUZZING_UNSAFE_ACTIONS)),
}
