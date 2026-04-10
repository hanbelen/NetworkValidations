"""
Base check result dataclass.
All checks return a CheckResult — consistent structure for reporting.
"""


from dataclasses import dataclass, field


@dataclass
class CheckResult:
    device:  str
    check:   str
    passed:  bool
    reason:  str = ""
    detail:  dict = field(default_factory=dict)

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def to_dict(self) -> dict:
        return {
            "device":  self.device,
            "check":   self.check,
            "status":  self.status,
            "reason":  self.reason,
            "detail":  self.detail,
        }
