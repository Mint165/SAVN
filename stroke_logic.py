"""
stroke_logic.py — Enhanced risk algorithm for HeartBits
FAST scale: 0=Không, 1=Nhẹ, 2=Rõ, 3=Nặng
"""
import os
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

# FAST 4-level thresholds
FAST_LEVEL_NONE = 0
FAST_LEVEL_MILD = 1
FAST_LEVEL_CLEAR = 2
FAST_LEVEL_SEVERE = 3

# Points contributed by each FAST level per symptom
FAST_POINTS = {
    FAST_LEVEL_NONE: 0,
    FAST_LEVEL_MILD: 8,
    FAST_LEVEL_CLEAR: 18,
    FAST_LEVEL_SEVERE: 35,
}

# Risk thresholds
RISK_CRITICAL = 75
RISK_HIGH = 55
RISK_MODERATE = 35


def load_artifacts(
    model_name: str = "stroke_final_model.pkl",
    meta_name: str = "preprocessor_meta.pkl",
):
    import joblib
    base_path = os.path.dirname(__file__)
    model_path = os.path.join(base_path, model_name)
    meta_path = os.path.join(base_path, meta_name)

    if not os.path.exists(model_path) or not os.path.exists(meta_path):
        return None, None

    return joblib.load(model_path), joblib.load(meta_path)


def build_feature_row(
    age,
    gender,
    work_type,
    smoking_status,
    hypertension,
    heart_disease,
    avg_glucose_level,
    bmi,
    feature_names: Iterable[str],
) -> pd.DataFrame:
    row = {
        "age": float(age) if age is not None else 50.0,
        "hypertension": int(hypertension),
        "heart_disease": int(heart_disease),
        "avg_glucose_level": float(avg_glucose_level) if avg_glucose_level is not None else 100.0,
        "bmi": float(bmi) if bmi is not None else 22.0,
    }

    category_values = {
        "gender_": gender or "Male",
        "work_type_": work_type or "Private",
        "smoking_status_": smoking_status or "never smoked",
    }

    for feature_name in feature_names:
        for prefix, selected_value in category_values.items():
            if feature_name.startswith(prefix):
                row[feature_name] = int(feature_name[len(prefix):] == selected_value)
                break

    df = pd.DataFrame([row])
    for feature_name in feature_names:
        if feature_name not in df.columns:
            df[feature_name] = 0

    return df[list(feature_names)]


def get_ml_probability(df_row: pd.DataFrame, scaler, model) -> float:
    df_scaled = df_row.copy()
    scaled_cols = ["age", "avg_glucose_level", "bmi"]
    df_scaled[scaled_cols] = scaler.transform(df_row[scaled_cols])
    return float(model.predict_proba(df_scaled)[0][1])


def calc_fast_points_v2(fast_f: int, fast_a: int, fast_s: int, fast_t: int) -> int:
    """Calculate FAST score from 4-level inputs."""
    total = sum(FAST_POINTS.get(v, 0) for v in [fast_f, fast_a, fast_s, fast_t])
    return min(total, 100)


def compute_risk_summary(
    ml_probability: float,
    fast_f: int = 0,
    fast_a: int = 0,
    fast_s: int = 0,
    fast_t: int = 0,
    systolic: int = 120,
    diastolic: int = 80,
    avg_glucose: float = 100.0,
    age: float = 50.0,
) -> Dict[str, object]:
    """
    Enhanced risk algorithm:
    - ML model contributes 55% of score
    - FAST symptoms contribute up to 45%  
    - Blood pressure modifier: hypertensive crisis adds up to 10 pts
    - High glucose adds up to 5 pts
    - Age over 70 adds 5 pts
    """
    ml_score = int(ml_probability * 100)
    fast_sum = calc_fast_points_v2(fast_f, fast_a, fast_s, fast_t)

    # 60/40 Weighted combination as requested by user's reference
    # ML contributes 40%, FAST contributes 60%
    weighted_ml = ml_score * 0.4
    weighted_fast = (fast_sum / 100) * 60  # Scale fast_sum to be out of 60
    
    base_score = int(weighted_ml + weighted_fast)

    # Physical modifiers (Bonuses) - increased for better accuracy
    bp_bonus = 0
    if systolic >= 180 or diastolic >= 120:
        bp_bonus = 15  # Hypertensive crisis
    elif systolic >= 140 or diastolic >= 90:
        bp_bonus = 8
    elif systolic >= 130 or diastolic >= 80:
        bp_bonus = 4

    glucose_bonus = 0
    if avg_glucose is not None:
        if avg_glucose > 200:
            glucose_bonus = 10
        elif avg_glucose > 140:
            glucose_bonus = 5

    age_bonus = 5 if age >= 70 else (3 if age >= 60 else 0)

    combined_score = base_score + bp_bonus + glucose_bonus + age_bonus
    final_score = min(99, combined_score)
    override_msg = None

    # Hard overrides for severe FAST
    max_fast = max(fast_f, fast_a, fast_s, fast_t)
    if max_fast == FAST_LEVEL_SEVERE:
        final_score = 99
        override_msg = (
            "⚠️ CẢNH BÁO KHẨN CẤP: Triệu chứng NẶNG được phát hiện — "
            "GỌI CẤP CỨU 115 NGAY LẬP TỨC!"
        )

    return {
        "ml_score": ml_score,
        "fast_sum": fast_sum,
        "weighted_ml": round(weighted_ml, 1),
        "weighted_fast": round(weighted_fast, 1),
        "combined_score": combined_score,
        "final_score": final_score,
        "override_msg": override_msg,
    }


def generate_advice(
    final_score: int,
    systolic: int,
    diastolic: int,
    avg_glucose: float,
    age: float,
    fast_f: int,
    fast_a: int,
    fast_s: int,
    fast_t: int,
    heart_disease: int = 0,
    smoking_status: str = "never smoked",
) -> List[str]:
    """Generate personalised health advice based on the patient's data."""
    advice = []
    max_fast = max(fast_f, fast_a, fast_s, fast_t)

    # Emergency advice
    if max_fast == FAST_LEVEL_SEVERE or final_score >= RISK_CRITICAL:
        advice.append("🚨 Gọi cấp cứu 115 ngay lập tức! Đây là tình huống khẩn cấp y tế.")
        return advice  # No other advice needed

    # FAST advice
    if max_fast == FAST_LEVEL_CLEAR:
        advice.append("⚠️ Xuất hiện triệu chứng thần kinh đáng chú ý — hãy đến cơ sở y tế kiểm tra ngay hôm nay.")
    elif max_fast == FAST_LEVEL_MILD:
        advice.append("🔔 Có triệu chứng nhẹ. Theo dõi sát và ghi chép. Nếu nặng hơn, hãy đến khám bác sĩ.")

    # Blood pressure advice
    if systolic >= 180 or diastolic >= 120:
        advice.append("🩺 Huyết áp ở mức nguy hiểm. Cần khám bác sĩ ngay trong ngày hôm nay.")
    elif systolic >= 140 or diastolic >= 90:
        advice.append("💊 Huyết áp cao. Hạn chế muối, giảm stress, tái khám đúng lịch hẹn.")
    elif systolic >= 120:
        advice.append("📊 Huyết áp tiền cao huyết áp. Duy trì lối sống lành mạnh và theo dõi đều đặn.")

    # Glucose advice
    if avg_glucose is not None:
        if avg_glucose > 200:
            advice.append("🍬 Đường huyết rất cao. Cần điều chỉnh chế độ ăn và liên hệ bác sĩ về thuốc.")
        elif avg_glucose > 140:
            advice.append("🥗 Đường huyết cao. Hạn chế thực phẩm nhiều đường, tăng cường vận động nhẹ.")
        elif avg_glucose < 70:
            advice.append("⚡ Đường huyết thấp. Ăn nhẹ ngay và tránh hoạt động gắng sức.")

    # Age advice
    if age >= 65:
        advice.append("🧓 Ở độ tuổi của bạn, khám sức khỏe định kỳ 3 tháng/lần là rất quan trọng.")

    # Lifestyle advice
    if smoking_status == "smokes":
        advice.append("🚭 Hút thuốc lá làm tăng đáng kể nguy cơ đột quỵ. Hãy tìm sự hỗ trợ để bỏ thuốc.")
    
    if heart_disease:
        advice.append("❤️ Với tiền sử bệnh tim, hãy uống thuốc đúng giờ và không bỏ tái khám.")

    # Low risk encouragement
    if final_score < RISK_MODERATE and not advice:
        advice.append("✅ Các chỉ số của bạn đang tốt! Duy trì lối sống lành mạnh và tiếp tục theo dõi.")

    if final_score < RISK_HIGH:
        advice.append("🏃 Tập thể dục nhẹ 30 phút mỗi ngày giúp giảm nguy cơ đột quỵ đến 27%.")

    return advice[:4]  # Return max 4 pieces of advice


def get_score_meta(score: int) -> Tuple[str, str, str]:
    if score >= RISK_CRITICAL:
        return "#DC2626", "NGUY CƠ RẤT CAO", "critical"
    if score >= RISK_HIGH:
        return "#EA580C", "NGUY CƠ CAO", "high"
    if score >= RISK_MODERATE:
        return "#D97706", "NGUY CƠ TRUNG BÌNH", "medium"
    return "#16A34A", "NGUY CƠ THẤP", "low"


def calc_xai_groups(df_row: pd.DataFrame, meta) -> Dict[str, float]:
    coeffs = meta.get("model_coefficients", {})
    scaler = meta["scaler"]
    feature_names = meta["feature_names"]
    df_scaled = df_row.copy()
    scaled_cols = ["age", "avg_glucose_level", "bmi"]
    df_scaled[scaled_cols] = scaler.transform(df_row[scaled_cols])

    groups = {
        "Tuổi tác": ["age"],
        "Huyết áp / Tim": ["hypertension", "heart_disease"],
        "Đường huyết": ["avg_glucose_level"],
        "Chỉ số BMI": ["bmi"],
        "Hút thuốc": [n for n in feature_names if n.startswith("smoking_status_")],
        "Nghề nghiệp": [n for n in feature_names if n.startswith("work_type_")],
        "Giới tính": [n for n in feature_names if n.startswith("gender_")],
    }

    return {
        group_name: round(
            sum(abs(coeffs.get(col, 0) * df_scaled[col].values[0]) for col in cols if col in df_scaled.columns),
            3,
        )
        for group_name, cols in groups.items()
    }


def generate_advice_en(
    final_score: int,
    systolic: int,
    diastolic: int,
    avg_glucose: float,
    age: float,
    fast_f: int,
    fast_a: int,
    fast_s: int,
    fast_t: int,
    heart_disease: int = 0,
    smoking_status: str = "never smoked",
) -> List[str]:
    """Generate personalised health advice in English."""
    advice = []
    max_fast = max(fast_f, fast_a, fast_s, fast_t)

    if max_fast == FAST_LEVEL_SEVERE or final_score >= RISK_CRITICAL:
        advice.append("🚨 Call emergency services (115) immediately! This is a medical emergency.")
        return advice

    if max_fast == FAST_LEVEL_CLEAR:
        advice.append("⚠️ Notable neurological symptoms detected — visit a medical facility for examination today.")
    elif max_fast == FAST_LEVEL_MILD:
        advice.append("🔔 Mild symptoms present. Monitor closely and record. If worsening, see a doctor.")

    if systolic >= 180 or diastolic >= 120:
        advice.append("🩺 Blood pressure is at a dangerous level. See a doctor today.")
    elif systolic >= 140 or diastolic >= 90:
        advice.append("💊 High blood pressure. Reduce salt intake, manage stress, keep follow-up appointments.")
    elif systolic >= 120:
        advice.append("📊 Pre-hypertension detected. Maintain a healthy lifestyle and monitor regularly.")

    if avg_glucose is not None and avg_glucose > 0:
        if avg_glucose > 200:
            advice.append("🍬 Very high blood glucose. Adjust your diet and consult your doctor about medication.")
        elif avg_glucose > 140:
            advice.append("🥗 High blood glucose. Limit sugary foods and increase light exercise.")
        elif avg_glucose < 70:
            advice.append("⚡ Low blood glucose. Eat a light snack and avoid strenuous activity.")

    if age >= 65:
        advice.append("🧓 At your age, regular health check-ups every 3 months are very important.")

    if smoking_status == "smokes":
        advice.append("🚭 Smoking significantly increases stroke risk. Seek support to quit.")

    if heart_disease:
        advice.append("❤️ With heart disease history, take medications on time and don't skip follow-ups.")

    if final_score < RISK_MODERATE and not advice:
        advice.append("✅ Your indicators look good! Maintain a healthy lifestyle and keep monitoring.")

    if final_score < RISK_HIGH:
        advice.append("🏃 Light exercise for 30 minutes daily can reduce stroke risk by up to 27%.")

    return advice[:4]

