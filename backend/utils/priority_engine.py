from datetime import datetime
from typing import List, Dict
from collections import defaultdict


PRIORITY_WEIGHTS = {
    1: 40,
    2: 30,
    3: 20,
    4: 10,
}

PRIORITY_LABELS = {
    1: "Critical",
    2: "High",
    3: "Medium",
    4: "Low",
}


def calculate_priority_score(action_item) -> int:
    score = PRIORITY_WEIGHTS.get(action_item.priority, 10)

    if action_item.deadline:
        now = datetime.utcnow()
        delta = (action_item.deadline - now).total_seconds()
        days_until = delta / 86400

        if days_until < 0:
            days_overdue = abs(int(days_until))
            overdue_bonus = 50 + (days_overdue * 5)
            score += min(overdue_bonus, 100)
        elif days_until <= 3:
            score += 25
        elif days_until <= 7:
            score += 15

    if action_item.status == "PENDING":
        score += 5

    return score


def get_priority_label(priority_int: int) -> str:
    return PRIORITY_LABELS.get(priority_int, "Low")


def filter_by_minimum_priority(action_items: list, min_priority: int) -> list:
    return [item for item in action_items if item.priority <= min_priority]


def sort_by_urgency(action_items: list) -> list:
    return sorted(action_items, key=lambda item: calculate_priority_score(item), reverse=True)


def group_by_priority(action_items: list) -> Dict[str, list]:
    groups: Dict[str, list] = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": [],
    }
    label_map = {1: "critical", 2: "high", 3: "medium", 4: "low"}

    for item in action_items:
        key = label_map.get(item.priority, "low")
        groups[key].append(item)

    return groups
