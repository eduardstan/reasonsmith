from reasonsmith.examples import sklearn_model
from reasonsmith.report import evaluate_requirement
from reasonsmith.spec import load_pack
from reasonsmith.verdict import Strength, Verdict


def test_sklearn_example_reaches_probed_on_ecoa_pack() -> None:
    pack = load_pack("ecoa")
    requirement = pack.get_requirement(sklearn_model.REQUIREMENT_ID)

    result = evaluate_requirement(
        requirement,
        sklearn_model.system_under_test(),
    )

    assert result.verdict == Verdict.SATISFIED
    assert result.strength == Strength.PROBED
