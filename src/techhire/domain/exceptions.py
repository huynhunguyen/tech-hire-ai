"""Domain-specific error hierarchy."""


class TechHireError(Exception):
    """Base class for all errors raised by the system."""


class SchemaValidationError(TechHireError):
    """The input dataset does not satisfy the canonical schema."""


class InvalidCandidateProfileError(TechHireError):
    def __init__(self, violations: list[str]):
        super().__init__("; ".join(violations))
        self.violations = violations


class SensitiveAttributeLeakError(TechHireError):
    """A sensitive attribute reached a model that must be blind to it."""


class DecisionValidationError(TechHireError):
    def __init__(self, violations: list[str]):
        super().__init__("; ".join(violations))
        self.violations = violations


class AuditLogCorruptedError(TechHireError):
    """The audit log file cannot be parsed."""
