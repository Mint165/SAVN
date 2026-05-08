"""
stroke_logic.py - Enhanced risk and XAI logic for HeartBits.
# Build Heartbeat: 2026-05-08
FAST scale: 0=None, 1=Mild, 2=Clear, 3=Severe
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

XAI_GROUP_AGE = "Tuổi tác"
XAI_GROUP_HEART = "Huyết áp / Tim"
XAI_GROUP_GLUCOSE = "Đường huyết"
XAI_GROUP_BMI = "Chỉ số BMI"
XAI_GROUP_SMOKING = "Hút thuốc"
XAI_GROUP_WORK = "Nghề nghiệp"
XAI_GROUP_GENDER = "Giới tính"

XAI_GROUP_TRANSLATIONS = {
    XAI_GROUP_AGE: {"vi": "Tuổi tác", "en": "Age"},
    XAI_GROUP_HEART: {"vi": "Huyết áp & Tim mạch", "en": "Blood Pressure & Heart"},
    XAI_GROUP_GLUCOSE: {"vi": "Đường huyết", "en": "Blood Glucose"},
    XAI_GROUP_BMI: {"vi": "Chỉ số BMI", "en": "BMI Index"},
    XAI_GROUP_SMOKING: {"vi": "Hút thuốc", "en": "Smoking status"},
    XAI_GROUP_WORK: {"vi": "Nghề nghiệp", "en": "Occupation"},
    XAI_GROUP_GENDER: {"vi": "Giới tính", "en": "Gender"},
}

LEGACY_XAI_LABELS = {
    "TuÃ¡Â»â€¢i tÃƒÂ¡c": XAI_GROUP_AGE,
    "HuyÃ¡ÂºÂ¿t ÃƒÂ¡p / Tim": XAI_GROUP_HEART,
    "Ã„ÂÃ†Â°Ã¡Â»Âng huyÃ¡ÂºÂ¿t": XAI_GROUP_GLUCOSE,
    "ChÃ¡Â»â€° sÃ¡Â»â€˜ BMI": XAI_GROUP_BMI,
    "HÃƒÂºt thuÃ¡Â»â€˜c": XAI_GROUP_SMOKING,
    "NghÃ¡Â»Â nghiÃ¡Â»â€¡p": XAI_GROUP_WORK,
    "GiÃ¡Â»â€ºi tÃƒÂ­nh": XAI_GROUP_GENDER,
}

BASE_XAI_GROUPS = {
    XAI_GROUP_AGE: ["age"],
    XAI_GROUP_HEART: ["hypertension", "heart_disease"],
    XAI_GROUP_GLUCOSE: ["avg_glucose_level"],
    XAI_GROUP_BMI: ["bmi"],
}

PROTECTIVE_XAI_FEATURES = {
    "smoking_status_never smoked",
    "work_type_Never_worked",
    "work_type_children",
    "ever_married_No",
}

XAI_GROUP_WEIGHTS = {
    XAI_GROUP_WORK: 0.35,
    XAI_GROUP_GENDER: 0.2,
}


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
    if scaler is not None:
        scaled_cols = ["age", "avg_glucose_level", "bmi"]
        df_scaled[scaled_cols] = scaler.transform(df_row[scaled_cols])
    return float(model.predict_proba(df_scaled)[0][1])


def calc_fast_points_v2(fast_f: int, fast_a: int, fast_s: int, fast_t: int) -> int:
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
    ml_score = int(ml_probability * 100)
    fast_sum = calc_fast_points_v2(fast_f, fast_a, fast_s, fast_t)

    weighted_ml = ml_score * 0.4
    weighted_fast = (fast_sum / 100) * 60
    base_score = int(weighted_ml + weighted_fast)

    bp_bonus = 0
    if systolic >= 180 or diastolic >= 120:
        bp_bonus = 15
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

    if max(fast_f, fast_a, fast_s, fast_t) == FAST_LEVEL_SEVERE:
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
    advice = []
    max_fast = max(fast_f, fast_a, fast_s, fast_t)

    if max_fast == FAST_LEVEL_SEVERE or final_score >= RISK_CRITICAL:
        advice.append("🚨 Gọi cấp cứu 115 ngay lập tức! Đây là tình huống khẩn cấp y tế.")
        return advice

    if max_fast == FAST_LEVEL_CLEAR:
        advice.append("⚠️ Xuất hiện triệu chứng thần kinh đáng chú ý — hãy đến cơ sở y tế kiểm tra ngay hôm nay.")
    elif max_fast == FAST_LEVEL_MILD:
        advice.append("🔔 Có triệu chứng nhẹ. Theo dõi sát và ghi chép. Nếu nặng hơn, hãy đến khám bác sĩ.")

    if systolic >= 180 or diastolic >= 120:
        advice.append("🩺 Huyết áp ở mức nguy hiểm. Cần khám bác sĩ ngay trong ngày hôm nay.")
    elif systolic >= 140 or diastolic >= 90:
        advice.append("💊 Huyết áp cao. Hạn chế muối, giảm stress, tái khám đúng lịch hẹn.")
    elif systolic >= 120:
        advice.append("📊 Huyết áp tiền cao huyết áp. Duy trì lối sống lành mạnh và theo dõi đều đặn.")

    if avg_glucose is not None:
        if avg_glucose > 200:
            advice.append("🍬 Đường huyết rất cao. Cần điều chỉnh chế độ ăn và liên hệ bác sĩ về thuốc.")
        elif avg_glucose > 140:
            advice.append("🥗 Đường huyết cao. Hạn chế thực phẩm nhiều đường, tăng cường vận động nhẹ.")
        elif avg_glucose < 70:
            advice.append("⚡ Đường huyết thấp. Ăn nhẹ ngay và tránh hoạt động gắng sức.")

    if age >= 65:
        advice.append("🧓 Ở độ tuổi của bạn, khám sức khỏe định kỳ 3 tháng/lần là rất quan trọng.")

    if smoking_status == "smokes":
        advice.append("🚭 Hút thuốc lá làm tăng đáng kể nguy cơ đột quỵ. Hãy tìm sự hỗ trợ để bỏ thuốc.")

    if heart_disease:
        advice.append("❤️ Với tiền sử bệnh tim, hãy uống thuốc đúng giờ và không bỏ tái khám.")

    if final_score < RISK_MODERATE and not advice:
        advice.append("✅ Các chỉ số của bạn đang tốt! Duy trì lối sống lành mạnh và tiếp tục theo dõi.")

    if final_score < RISK_HIGH:
        advice.append("🏃 Tập thể dục nhẹ 30 phút mỗi ngày giúp giảm nguy cơ đột quỵ đến 27%.")

    return advice[:4]


def get_score_meta(score: int) -> Tuple[str, str, str]:
    if score >= RISK_CRITICAL:
        return "#DC2626", "NGUY CƠ RẤT CAO", "critical"
    if score >= RISK_HIGH:
        return "#EA580C", "NGUY CƠ CAO", "high"
    if score >= RISK_MODERATE:
        return "#D97706", "NGUY CƠ TRUNG BÌNH", "medium"
    return "#16A34A", "NGUY CƠ THẤP", "low"


def normalize_xai_groups(xai_groups: Optional[Dict[str, float]]) -> Dict[str, float]:
    normalized: Dict[str, float] = {}
    for raw_name, raw_value in (xai_groups or {}).items():
        name = LEGACY_XAI_LABELS.get(raw_name, raw_name)
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            value = 0.0
        normalized[name] = round(normalized.get(name, 0.0) + value, 2)
    return normalized


def calc_xai_groups(df_row: pd.DataFrame, meta) -> Dict[str, float]:
    importances = meta.get("model_feature_importances") or {}
    coeffs = meta.get("model_coefficients") or {}
    scaler = meta.get("scaler")
    feature_names = meta["feature_names"]

    groups = dict(BASE_XAI_GROUPS)
    groups[XAI_GROUP_SMOKING] = [n for n in feature_names if n.startswith("smoking_status_")]
    groups[XAI_GROUP_WORK] = [n for n in feature_names if n.startswith("work_type_")]
    groups[XAI_GROUP_GENDER] = [n for n in feature_names if n.startswith("gender_")]

    def local_intensity(col: str) -> float:
        if col not in df_row.columns:
            return 0.0
        value = float(df_row[col].values[0])
        if col in {"hypertension", "heart_disease"}:
            return 1.0 if value > 0 else 0.0
        if col.startswith(("gender_", "work_type_", "smoking_status_")):
            return 1.0 if value > 0 and col not in PROTECTIVE_XAI_FEATURES else 0.0

        stats = (meta.get("feature_stats") or {}).get(col, {})
        if col == "age":
            floor = float(stats.get("median", 50.0))
            ceiling = float(stats.get("max", 90.0))
        elif col == "avg_glucose_level":
            floor = 110.0
            ceiling = float(stats.get("max", 260.0))
        elif col == "bmi":
            floor = 24.0
            ceiling = float(stats.get("max", 45.0))
        else:
            floor = float(stats.get("min", 0.0))
            ceiling = float(stats.get("max", max(value, 1.0)))
        if ceiling <= floor:
            return 0.0
        return max(0.0, min(1.0, (value - floor) / (ceiling - floor)))

    if importances:
        return {
            group_name: float(
                round(
                    sum(importances.get(col, 0.0) * local_intensity(col) * 100 for col in cols)
                    * XAI_GROUP_WEIGHTS.get(group_name, 1.0),
                    2,
                )
            )
            for group_name, cols in groups.items()
        }

    df_scaled = df_row.copy()
    if scaler is not None:
        scaled_cols = ["age", "avg_glucose_level", "bmi"]
        df_scaled[scaled_cols] = scaler.transform(df_row[scaled_cols])

    return {
        group_name: float(
            round(
                sum(
                    max(0.0, coeffs.get(col, 0.0) * df_scaled[col].values[0])
                    for col in cols
                    if col in df_scaled.columns and col not in PROTECTIVE_XAI_FEATURES
                )
                * XAI_GROUP_WEIGHTS.get(group_name, 1.0),
                2,
            )
        )
        for group_name, cols in groups.items()
    }


def get_key_factors_msg(xai_groups, lang='vi'):
    sorted_factors = sorted(normalize_xai_groups(xai_groups).items(), key=lambda x: x[1], reverse=True)
    top_factors = [f[0] for f in sorted_factors[:2] if f[1] > 0]

    if not top_factors:
        return "Các chỉ số của bạn khá cân bằng." if lang == "vi" else "Your metrics are fairly balanced."

    f1 = XAI_GROUP_TRANSLATIONS.get(top_factors[0], {}).get(lang, top_factors[0])
    if len(top_factors) > 1:
        f2 = XAI_GROUP_TRANSLATIONS.get(top_factors[1], {}).get(lang, top_factors[1])
        if lang == "vi":
            return f"Phân tích cho thấy <strong>{f1}</strong> và <strong>{f2}</strong> là những yếu tố chính ảnh hưởng đến rủi ro của bạn."
        return f"Analysis shows that <strong>{f1}</strong> and <strong>{f2}</strong> are the primary factors affecting your risk."

    if lang == "vi":
        return f"Yếu tố quan trọng nhất cần lưu ý là <strong>{f1}</strong>."
    return f"The most significant factor to note is <strong>{f1}</strong>."


def build_xai_insights(
    xai_groups,
    systolic,
    diastolic,
    avg_glucose,
    bmi,
    age,
    smoking_status,
    heart_disease,
    lang="vi",
):
    insights = []
    sorted_factors = sorted(normalize_xai_groups(xai_groups).items(), key=lambda x: x[1], reverse=True)
    top_factors = [f[0] for f in sorted_factors[:3] if f[1] > 0]

    for factor in top_factors:
        if factor == XAI_GROUP_HEART:
            if systolic >= 140 or diastolic >= 90:
                insights.append(
                    "Huyết áp của bạn đang ở mức cao, đây là một trong những nguyên nhân trực tiếp làm tăng gánh nặng lên mạch máu và nguy cơ đột quỵ."
                    if lang == "vi"
                    else "Your blood pressure is high, which directly increases the strain on your blood vessels and your stroke risk."
                )
            elif heart_disease:
                insights.append(
                    "Tiền sử bệnh tim mạch của bạn làm tăng nguy cơ cục máu đông, cần tuân thủ nghiêm ngặt phác đồ điều trị."
                    if lang == "vi"
                    else "Your history of heart disease increases the risk of blood clots; strict adherence to treatment is crucial."
                )
        elif factor == XAI_GROUP_GLUCOSE and avg_glucose is not None and avg_glucose > 140:
            insights.append(
                "Mức đường huyết cao đang gây xơ vữa động mạch, một yếu tố rủi ro thầm lặng rất đáng kể."
                if lang == "vi"
                else "High blood glucose contributes to atherosclerosis, a significant silent risk factor."
            )
        elif factor == XAI_GROUP_SMOKING and smoking_status == "smokes":
            insights.append(
                "Việc hút thuốc lá đang làm suy yếu thành mạch máu của bạn một cách rõ rệt. Bỏ thuốc là cách tốt nhất để giảm ngay rủi ro này."
                if lang == "vi"
                else "Smoking is visibly weakening your blood vessel walls. Quitting is the best way to immediately reduce this risk."
            )
        elif factor == XAI_GROUP_BMI and bmi is not None and bmi >= 25:
            insights.append(
                "Chỉ số BMI cho thấy bạn đang thừa cân, điều này ảnh hưởng gián tiếp qua việc tăng nguy cơ tiểu đường và huyết áp cao."
                if lang == "vi"
                else "Your BMI indicates you are overweight, which indirectly increases risk by promoting diabetes and high blood pressure."
            )
        elif factor == XAI_GROUP_AGE and age >= 60:
            insights.append(
                "Tuổi tác là yếu tố rủi ro tự nhiên không thể thay đổi, nhưng nó nhắc nhở bạn cần chú trọng hơn vào việc tầm soát sức khỏe định kỳ."
                if lang == "vi"
                else "Age is an unchangeable natural risk factor, but it reminds you to prioritize regular health screenings."
            )
        elif factor == XAI_GROUP_WORK:
            insights.append(
                "Nghề nghiệp hoặc môi trường làm việc có thể mang lại căng thẳng hoặc tính chất ít vận động, góp phần làm tăng nhẹ rủi ro."
                if lang == "vi"
                else "Your occupation or work environment may involve stress or a sedentary lifestyle, slightly increasing your risk."
            )

    if not insights:
        insights.append(
            "Các chỉ số của bạn khá ổn định và không có yếu tố nào gây nguy hiểm vượt mức."
            if lang == "vi"
            else "Your indicators are quite stable and there are no overwhelmingly dangerous factors."
        )

    return insights[:3]


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
