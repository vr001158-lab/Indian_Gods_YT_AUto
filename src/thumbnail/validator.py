# src/thumbnail/validator.py
# Phase 2H — Thumbnail Safety Validator

from src.thumbnail.schemas import validate_decision_input


def validate_decision_safety(decision: dict) -> tuple:
    """
    Enforces safety checks. Fails closed by returning (False, error) if the decision
    fails any safety parameters.

    Raises ValueError on validation failure if called in strict mode.
    """
    ok, error_msg = validate_decision_input(decision)
    if not ok:
        return False, f"❌ Safety Gate Rejection: {error_msg}"
    return True, ""


def verify_or_raise_safety(decision: dict):
    """
    Stricter wrapper that raises ValueError if safety checks fail.
    """
    ok, error_msg = validate_decision_safety(decision)
    if not ok:
        raise ValueError(error_msg)
