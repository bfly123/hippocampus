from __future__ import annotations

from dataclasses import dataclass, field


ROLE_SOURCE = "source"
ROLE_TEST = "test"
ROLE_CONFIG = "config"
ROLE_DOCS = "docs"

_BUDGET_RATIOS: dict[str, float] = {
    ROLE_SOURCE: 0.70,
    ROLE_TEST: 0.10,
    ROLE_CONFIG: 0.05,
    ROLE_DOCS: 0.05,
}
_ELASTIC_RATIO = 0.10


@dataclass
class PromptBudget:
    remaining: int
    parts: list[str] = field(default_factory=list)

    def append_if_fits(self, text: str, estimate_tokens) -> tuple[bool, int]:
        tokens = estimate_tokens(text)
        if text.strip() and tokens <= self.remaining:
            self.parts.append(text)
            self.remaining -= tokens
            return True, tokens
        return False, tokens


def compute_tree_budget_tokens(remaining: int, has_files: bool, profile: dict[str, object]) -> int:
    reserve_for_l2l3 = int(remaining * float(profile["tree_reserve_ratio"])) if has_files else 0
    return max(120, remaining - reserve_for_l2l3)


def compute_role_budgets(total_budget: int, file_roles: dict[str, str]) -> dict[str, int]:
    present_roles = set(file_roles.values())
    elastic = int(total_budget * _ELASTIC_RATIO)

    budgets: dict[str, int] = {}
    for role, ratio in _BUDGET_RATIOS.items():
        quota = int(total_budget * ratio)
        if role not in present_roles:
            elastic += quota
        else:
            budgets[role] = quota

    budgets[ROLE_SOURCE] = budgets.get(ROLE_SOURCE, 0) + elastic
    return budgets
