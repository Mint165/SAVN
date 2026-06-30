"""
Training pipeline for HeartBits stroke diagnosis.
Uses a balanced RandomForest model and stores feature importances for XAI.
"""
import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split


DATASET_PATH = "healthcare-dataset-stroke-data.csv"
MODEL_PATH = "stroke_final_model.pkl"
META_PATH = "preprocessor_meta.pkl"
NUMERICAL_COLS = ["age", "avg_glucose_level", "bmi"]
CATEGORICAL_COLS = ["gender", "work_type", "smoking_status"]


def load_data():
    if os.path.exists(DATASET_PATH):
        print(f"Loading original dataset from {DATASET_PATH}")
        df = pd.read_csv(DATASET_PATH)
        return df.drop(columns=["id", "ever_married", "Residence_type"], errors="ignore")

    print("Original CSV not found. Falling back to synthetic dataset...")
    from tests.synthetic_data import SYNTHETIC_PATIENTS

    df = pd.DataFrame(SYNTHETIC_PATIENTS)
    fast_score = df["fast_f"] + df["fast_a"] + df["fast_s"] + df["fast_t"]
    df["stroke"] = (
        (df["age"] > 65)
        | ((df["hypertension"] == 1) & (df["heart_disease"] == 1))
        | (fast_score > 4)
    ).astype(int)
    return df


def build_feature_stats(df: pd.DataFrame):
    stats = {}
    for col in NUMERICAL_COLS:
        series = pd.to_numeric(df[col], errors="coerce")
        stats[col] = {
            "min": float(series.min()),
            "max": float(series.max()),
            "median": float(series.median()),
            "p75": float(series.quantile(0.75)),
        }
    return stats


def train():
    print("=" * 50)
    print("  HEARTBITS - TRAINING PIPELINE (RANDOM FOREST)")
    print("=" * 50)

    df = load_data()

    median_bmi = float(df["bmi"].median())
    median_glucose = float(df["avg_glucose_level"].median())
    df["bmi"] = df["bmi"].fillna(median_bmi)
    df["avg_glucose_level"] = df["avg_glucose_level"].fillna(median_glucose)

    df_encoded = pd.get_dummies(df, columns=CATEGORICAL_COLS)
    X = df_encoded.drop(columns=["stroke"])
    y = df_encoded["stroke"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=500,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )

    print("Training RandomForestClassifier model...")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)

    print("\n" + "=" * 50)
    print("  EVALUATION RESULTS")
    print("=" * 50)
    print(f"  Accuracy : {acc:.4f}")
    print(f"  Recall   : {rec:.4f}")
    print(f"  ROC AUC  : {auc:.4f}")
    print("-" * 50)
    print(classification_report(y_test, y_pred))

    model.n_jobs = 1
    importances = dict(zip(X.columns, model.feature_importances_))
    meta = {
        "model_type": "RandomForestClassifier",
        "scaler": None,
        "median_bmi": median_bmi,
        "median_glucose": median_glucose,
        "feature_names": X.columns.tolist(),
        "feature_stats": build_feature_stats(X),
        "model_feature_importances": importances,
        "xai_source": "feature_importances",
    }

    joblib.dump(model, MODEL_PATH, compress=3)
    joblib.dump(meta, META_PATH, compress=3)
    print(f"\nSuccess! Artifacts saved: {MODEL_PATH}, {META_PATH}")


if __name__ == "__main__":
    train()
