"""Compare predictive models using synthetic medicine inventory data."""

import math
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_NAMES = [
    "stock",
    "daily_usage",
    "safety_stock",
    "incoming_stock",
    "delivery_delay_days",
    "days_until_stockout",
    "stock_vs_safety_stock",
]


def _features(stock, daily_usage, safety_stock,
              incoming_stock, delivery_delay_days):
    days_cover = stock / daily_usage if daily_usage > 0 else 365.0
    return [
        stock,
        daily_usage,
        safety_stock,
        incoming_stock,
        delivery_delay_days,
        min(days_cover, 365.0),
        stock - safety_stock,
    ]


def _simulate_stockout(rng, stock, daily_usage,
                       incoming_stock, delivery_delay_days):
    """Simulate whether demand causes a stockout within seven days."""
    remaining = float(stock)
    arrival_day = max(1, math.ceil(delivery_delay_days))
    shipment_received = False

    for day in range(1, 8):
        if not shipment_received and day >= arrival_day:
            remaining += incoming_stock
            shipment_received = True

        demand = max(
            0.1,
            rng.normal(daily_usage, max(daily_usage * 0.20, 0.1)),
        )
        remaining -= demand

        if remaining <= 0:
            return 1

    return 0


def build_dataset(n_samples=5000, random_state=42):
    """Create a reproducible Pandas dataset with simulated labels."""
    rng = np.random.default_rng(random_state)
    rows = []
    labels = []

    for _ in range(n_samples):
        stock = int(rng.integers(0, 301))
        daily_usage = float(rng.uniform(0.5, 50))
        safety_stock = int(rng.integers(0, 101))
        incoming_stock = int(rng.integers(0, 301))
        delay = float(rng.uniform(0, 14))

        rows.append(
            _features(
                stock, daily_usage, safety_stock,
                incoming_stock, delay,
            )
        )
        labels.append(
            _simulate_stockout(
                rng, stock, daily_usage, incoming_stock, delay,
            )
        )

    X = pd.DataFrame(rows, columns=FEATURE_NAMES)
    y = pd.Series(labels, name="stockout_within_7_days")
    return X, y


def compare_models(n_samples=5000, random_state=42):
    """Evaluate two models on exactly the same held-out scenarios."""
    X, y = build_dataset(n_samples, random_state)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=random_state,
        stratify=y,
    )

    models = {
        "Random Forest": RandomForestClassifier(
            n_estimators=120,
            max_depth=10,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=1,
        ),
        "Logistic Regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=random_state,
            ),
        ),
    }

    results = {}

    for name, model in models.items():
        model.fit(X_train, y_train)

        predictions = model.predict(X_test)
        probabilities = model.predict_proba(X_test)[:, 1]

        # Warm up before measuring batch inference time.
        model.predict_proba(X_test.iloc[:10])
        start = time.perf_counter()
        for _ in range(5):
            model.predict_proba(X_test)
        elapsed = (time.perf_counter() - start) / 5

        metrics = {
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "stockout_examples_in_test": int(y_test.sum()),
            "accuracy": round(accuracy_score(y_test, predictions), 3),
            "precision": round(
                precision_score(y_test, predictions, zero_division=0), 3
            ),
            "recall": round(
                recall_score(y_test, predictions, zero_division=0), 3
            ),
            "roc_auc": round(roc_auc_score(y_test, probabilities), 3),
            "batch_inference_ms": round(elapsed * 1000, 3),
            "inference_us_per_scenario": round(
                elapsed * 1_000_000 / len(X_test), 2
            ),
            "data_note": "Synthetic simulated data; not real clinical data.",
        }

        results[name] = {"model": model, "metrics": metrics}

    return results


def train_model(n_samples=5000, random_state=42):
    """Compatibility helper returning the Random Forest model and metrics."""
    result = compare_models(n_samples, random_state)["Random Forest"]
    return result["model"], result["metrics"]


def predict_stockout_probability(
    model,
    stock,
    daily_usage,
    safety_stock,
    incoming_stock=0,
    delivery_delay_days=0.0,
):
    """Estimate simulated stockout probability within seven days."""
    values = _features(
        stock, daily_usage, safety_stock,
        incoming_stock, delivery_delay_days,
    )
    sample = pd.DataFrame([values], columns=FEATURE_NAMES)
    return float(model.predict_proba(sample)[0, 1])


if __name__ == "__main__":
    results = compare_models()

    print("MEDIFLOW SENTINEL — MODEL COMPARISON")
    print("Data: synthetic inventory scenarios")
    print("Prediction target: stockout within seven days")
    print()

    for name, result in results.items():
        print(f"--- {name} ---")
        for metric, value in result["metrics"].items():
            print(f"{metric}: {value}")
        print()

    # Example prediction using Random Forest.
    rf_model = results["Random Forest"]["model"]
    probability = predict_stockout_probability(
        rf_model,
        stock=20,
        daily_usage=15,
        safety_stock=30,
        incoming_stock=0,
        delivery_delay_days=2,
    )
    print(f"Example simulated 7-day stockout probability: {probability:.1%}")
