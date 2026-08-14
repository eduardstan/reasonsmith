"""Shipped gold-triple system: symbolic rules with a reproducible timing violation."""

from . import symbolic_rules


def system_under_test():
    sut = symbolic_rules.system_under_test()
    sut._rules = [
        rule.replace("notification_queue_days + 1", "notification_queue_days + 40")
        for rule in sut._rules
    ]
    return sut
