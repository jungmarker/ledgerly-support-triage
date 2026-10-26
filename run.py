"""Local text-classification baseline with separate validation and test accounts."""

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from reporting import render
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline

ROUTES = {
    "How-To": "Customer Success",
    "Bug": "Engineering",
    "Billing": "Finance",
    "Account Access": "Support",
    "Integration": "Integrations",
    "Feature Request": "Product",
    "Cancellation": "Retention",
}


def bucket(account):
    return int(hashlib.sha256(account.encode()).hexdigest()[:8], 16) % 5


def texts(frame):
    return (frame.subject.fillna("") + " " + frame.description.fillna("")).tolist()


def classify(model, frame, threshold):
    prob = model.predict_proba(texts(frame))
    best = prob.argmax(axis=1)
    pred = model.classes_[best]
    confidence = prob.max(axis=1)
    review = (confidence < threshold) | (pred == "Cancellation")
    # Priority is not recoverable from the synthetic text: do not automate it.
    return pd.DataFrame(
        {
            "case_id": frame.case_id.to_numpy(),
            "predicted_category": pred,
            "confidence": confidence,
            "action": np.where(review, "human_review", "suggest_route"),
            "suggested_team": [ROUTES[c] for c in pred],
            "priority": "human_review",
        }
    )


def threshold_for_precision(confidence, correct, target=0.95):
    choices = []
    for t in np.arange(0.5, 1.0, 0.01):
        keep = confidence >= t
        if keep.sum() >= 20 and correct[keep].mean() >= target:
            choices.append((keep.mean(), float(t)))
    return max(choices)[1] if choices else 1.01


def evaluate(pred, truth):
    z = pred.merge(truth, on="case_id", validate="one_to_one")
    accepted = z.action == "suggest_route"
    return {
        "tickets": len(z),
        "accuracy": accuracy_score(z.true_category, z.predicted_category),
        "macro_f1": f1_score(z.true_category, z.predicted_category, average="macro"),
        "routing_coverage": float(accepted.mean()),
        "accepted_accuracy": float(
            (
                z.loc[accepted, "true_category"]
                == z.loc[accepted, "predicted_category"]
            ).mean()
        )
        if accepted.any()
        else None,
    }


def main(data, out):
    t = pd.read_csv(data / "raw/support_tickets.csv")
    t["created_at"] = pd.to_datetime(t.created_at)
    train = t[
        (t.created_at < "2026-01-01")
        & t.account_id.map(bucket).isin([0, 1, 2])
        & t.agent_category.notna()
    ]
    validation = t[
        (t.created_at >= "2026-01-01")
        & (t.created_at < "2026-04-01")
        & (t.account_id.map(bucket) == 3)
    ]
    test = t[(t.created_at >= "2026-04-01") & (t.account_id.map(bucket) == 4)]
    assert not set(train.account_id) & set(test.account_id) and not set(
        validation.account_id
    ) & set(test.account_id)
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
        LogisticRegression(max_iter=1500, C=4),
    ).fit(texts(train), train.agent_category)
    # Predictions made before evaluation labels are read. Training uses noisy agent labels.
    valpred = classify(model, validation, 0)
    testpred = classify(model, test, 0)
    truth = pd.read_csv(data / "truth/ticket_labels.csv")
    v = valpred.merge(truth, on="case_id", validate="one_to_one")
    threshold = threshold_for_precision(
        v.confidence.to_numpy(), (v.predicted_category == v.true_category).to_numpy()
    )
    testpred = classify(model, test, threshold)
    metrics = evaluate(testpred, truth)
    labels = sorted(ROUTES)
    scored = testpred.merge(truth, on="case_id")
    cm = pd.DataFrame(
        confusion_matrix(
            scored.true_category, scored.predicted_category, labels=labels
        ),
        columns=labels,
    )
    cm.insert(0, "actual", labels)
    baseline = test.merge(truth, on="case_id")
    metrics.update(
        noisy_agent_accuracy=accuracy_score(
            baseline.true_category, baseline.agent_category.fillna("Unknown")
        ),
        training_tickets=len(train),
        validation_tickets=len(validation),
        confidence_threshold=round(threshold, 2),
    )
    stress = pd.read_csv(Path(__file__).parent / "evaluation/novel_tickets.csv")
    stresspred = classify(model, stress, threshold)
    stressmetrics = evaluate(stresspred, stress[["case_id", "true_category"]])
    metrics["novel_text_accuracy"] = stressmetrics["accuracy"]
    metrics["novel_text_routing_coverage"] = stressmetrics["routing_coverage"]
    current = classify(model, t.sort_values("created_at").tail(50), threshold)
    render(
        out,
        "Support triage evaluation lab",
        metrics,
        {
            "heldout_predictions": testpred,
            "confusion_matrix": cm,
            "novel_text_predictions": stresspred.merge(
                stress[["case_id", "true_category"]], on="case_id"
            ),
            "recent_ticket_queue": current,
        },
        "TF-IDF plus logistic regression is a local AI baseline, not an LLM agent. Training uses noisy agent categories; truth scores validation/test only. Later tickets from unseen accounts test generalization. Repeated generator templates make synthetic accuracy optimistic: the separate novel-text set exposes this gap. All routing is advisory; cancellation and priority require human review.",
        (
            ["Noisy agent", "Heldout classifier", "Novel wording"],
            [
                metrics["noisy_agent_accuracy"],
                metrics["accuracy"],
                metrics["novel_text_accuracy"],
            ],
            "Category accuracy",
        ),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("data"))
    p.add_argument("--out", type=Path, default=Path("reports"))
    a = p.parse_args()
    main(a.data, a.out)
