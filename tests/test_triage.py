import numpy as np
import pandas as pd
from run import classify, texts, threshold_for_precision


class FakeModel:
    classes_ = np.array(["Bug", "Cancellation"])

    def predict_proba(self, text):
        return np.array([[0.95, 0.05], [0.03, 0.97], [0.51, 0.49]])


def test_review_guards_and_only_text_used():
    f = pd.DataFrame(
        {
            "case_id": ["a", "b", "c"],
            "subject": ["error", "cancel", "unsure"],
            "description": ["", "", ""],
            "agent_category": ["Billing"] * 3,
        }
    )
    p = classify(FakeModel(), f, 0.8)
    assert list(p.action) == ["suggest_route", "human_review", "human_review"]
    assert (p.priority == "human_review").all() and texts(f) == [
        "error ",
        "cancel ",
        "unsure ",
    ]
    assert threshold_for_precision(np.array([0.99] * 30), np.zeros(30, dtype=bool)) > 1


def test_threshold_uses_minimum_sample_and_rejects_low_quality():
    assert threshold_for_precision(np.array([0.99] * 10), np.ones(10, dtype=bool)) > 1
    assert threshold_for_precision(np.array([0.9] * 30), np.ones(30, dtype=bool)) <= 0.9


def test_evaluation_excludes_reviewed_tickets_from_accepted_accuracy():
    from run import evaluate

    p = pd.DataFrame(
        {
            "case_id": ["a", "b"],
            "predicted_category": ["Bug", "Billing"],
            "action": ["suggest_route", "human_review"],
        }
    )
    truth = pd.DataFrame(
        {"case_id": ["a", "b"], "true_category": ["Bug", "Integration"]}
    )
    metrics = evaluate(p, truth)
    assert (
        metrics["accuracy"] == 0.5
        and metrics["accepted_accuracy"] == 1
        and metrics["routing_coverage"] == 0.5
    )
