# src/assets/exceptions.py
# Exceptions for deity identity and asset consistency gates

class NoMatchingDeityAssetError(Exception):
    """Raised when no verified asset exists for the requested deity and avatar."""
    pass


class DeityIdentityMismatchError(Exception):
    """Raised when an asset depicts an unrelated or mismatched deity or avatar."""
    pass


class UnverifiedDeityAssetError(Exception):
    """Raised when an asset lacks explicit verified provenance for the requested deity/avatar."""
    pass
