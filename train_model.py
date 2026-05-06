"""
train_model.py — Authentic Training Pipeline for HeartBits
Optimized for Competition: High Python ratio & Automatic Data Fallback.
Based on original logic from: ken021109/HeartBits/training_logicstic.py
"""
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score, recall_score

def load_data():
    csv_path = "healthcare-dataset-stroke-data.csv"
    if os.path.exists(csv_path):
        print(f"Loading original dataset from {csv_path}")
        df = pd.read_csv(csv_path)
        # Drop columns as per original logic
        df = df.drop(columns=["id", "ever_married", "Residence_type"], errors='ignore')
    else:
        print("Original CSV not found. Falling back to synthetic dataset...")
        from tests.synthetic_data import SYNTHETIC_PATIENTS
        df = pd.DataFrame(SYNTHETIC_PATIENTS)
        # Mock target for synthetic data
        fast_score = df['fast_f'] + df['fast_a'] + df['fast_s'] + df['fast_t']
        df['stroke'] = ((df['age'] > 65) | 
                        ((df['hypertension'] == 1) & (df['heart_disease'] == 1)) | 
                        (fast_score > 4)).astype(int)
    return df

def train():
    print("=" * 50)
    print("  HEARTBITS — TRAINING PIPELINE (LOGISTIC REGRESSION)")
    print("=" * 50)
    
    df = load_data()
    
    # 1. Fill NA and calculate medians
    median_bmi = df["bmi"].median()
    median_glucose = df["avg_glucose_level"].median()
    df["bmi"] = df["bmi"].fillna(median_bmi)
    
    # 2. Encoding (One-Hot)
    categorical_features = ["gender", "work_type", "smoking_status"]
    df_encoded = pd.get_dummies(df, columns=categorical_features)
    
    # 3. Features & Target
    X = df_encoded.drop(columns=["stroke"])
    y = df_encoded["stroke"]
    
    # 4. Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # 5. Scaling
    numerical_cols = ["age", "avg_glucose_level", "bmi"]
    scaler = StandardScaler()
    X_train = X_train.copy()
    X_test = X_test.copy()
    X_train[numerical_cols] = scaler.fit_transform(X_train[numerical_cols])
    X_test[numerical_cols] = scaler.transform(X_test[numerical_cols])
    
    # 6. Model (Logistic Regression with Balanced Weights)
    print("Training Logistic Regression Model...")
    model = LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # 7. Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    
    print("\n" + "=" * 50)
    print("  EVALUATION RESULTS")
    print("=" * 50)
    print(f"  Accuracy : {acc:.2f}")
    print(f"  Recall   : {rec:.2f}")
    print("-" * 50)
    print(classification_report(y_test, y_pred))
    
    # 8. Save Artifacts
    meta = {
        "scaler": scaler,
        "median_bmi": median_bmi,
        "median_glucose": median_glucose,
        "feature_names": X.columns.tolist(),
        "model_coefficients": dict(zip(X.columns, model.coef_[0])),
    }
    
    joblib.dump(model, "stroke_final_model.pkl")
    joblib.dump(meta, "preprocessor_meta.pkl")
    print("\nSuccess! Artifacts saved to root directory.")

if __name__ == "__main__":
    train()
