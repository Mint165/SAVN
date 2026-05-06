import datetime
import json
from fastapi import FastAPI, Request, Depends, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import database, models, auth
import stroke_logic

# Create DB tables
try:
    models.Base.metadata.create_all(bind=database.engine)
except Exception as e:
    print(f"DB creation skipped or failed: {e}")

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure static and templates exist to prevent Starlette RuntimeError
static_path = os.path.join(BASE_DIR, "static")
templates_path = os.path.join(BASE_DIR, "templates")

if not os.path.exists(static_path):
    # If missing, use a temp dir to prevent crash
    static_path = "/tmp/static_placeholder"
    os.makedirs(static_path, exist_ok=True)
if not os.path.exists(templates_path):
    templates_path = "/tmp/templates_placeholder"
    os.makedirs(templates_path, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# --- Exercises Data ---
EXERCISES = [
    {
        "id": 1, "name": "Thở sâu thư giãn", "name_en": "Deep Breathing Relaxation",
        "duration": "10 phút", "duration_en": "10 minutes", "icon": "🫁",
        "image": "/static/img/exercise_breathing.png",
        "description": "Bài tập thở sâu giúp ổn định huyết áp và giảm căng thẳng.",
        "description_en": "Deep breathing exercises to stabilize blood pressure and reduce stress.",
        "steps": ["Ngồi thẳng lưng trên ghế thoải mái, hai tay đặt lên đùi.","Hít vào chậm và sâu qua mũi trong 4 giây, cảm nhận bụng phình ra.","Giữ hơi thở trong 2 giây.","Thở ra từ từ qua miệng trong 6 giây, bụng xẹp xuống.","Lặp lại 10 lần, mỗi ngày 2-3 lần."],
        "steps_en": ["Sit upright in a comfortable chair, hands on your thighs.","Breathe in slowly through your nose for 4 seconds, feel your belly expand.","Hold your breath for 2 seconds.","Exhale slowly through your mouth for 6 seconds, belly deflates.","Repeat 10 times, 2-3 times daily."]
    },
    {
        "id": 2, "name": "Đi bộ tại chỗ", "name_en": "Walking in Place",
        "duration": "15 phút", "duration_en": "15 minutes", "icon": "🚶",
        "image": "/static/img/exercise_walking.png",
        "description": "Bài tập tim mạch nhẹ nhàng, tăng tuần hoàn máu não.",
        "description_en": "Gentle cardio exercise to improve blood circulation to the brain.",
        "steps": ["Đứng thẳng, hai tay bám nhẹ vào thành ghế để giữ thăng bằng.","Nhấc chân trái lên từ từ, đầu gối vuông góc 90 độ, giữ 1 giây.","Hạ chân trái xuống, sau đó nhấc chân phải lên tương tự.","Tiếp tục luân phiên với nhịp độ chậm, đều đặn.","Thực hiện 20 bước mỗi chân, nghỉ 1 phút, lặp lại 3 lần."],
        "steps_en": ["Stand straight, hold the chair back lightly for balance.","Slowly lift your left leg, knee at 90 degrees, hold 1 second.","Lower your left leg, then lift your right leg similarly.","Continue alternating at a slow, steady pace.","Do 20 steps per leg, rest 1 minute, repeat 3 times."]
    },
    {
        "id": 3, "name": "Giãn cơ cổ", "name_en": "Neck Stretching",
        "duration": "5 phút", "duration_en": "5 minutes", "icon": "🧘",
        "image": "/static/img/exercise_neck.png",
        "description": "Giảm căng thẳng cơ cổ, cải thiện lưu thông máu lên não.",
        "description_en": "Relieve neck tension, improve blood flow to the brain.",
        "steps": ["Ngồi thẳng, hai vai thả lỏng.","Từ từ nghiêng đầu sang phải, tai chạm vai phải, giữ 5 giây.","Trở về vị trí trung tâm.","Nghiêng đầu sang trái, tai chạm vai trái, giữ 5 giây.","Quay đầu nhẹ nhàng sang phải-trái, mỗi bên 5 lần. Không ưỡn cổ ra sau."],
        "steps_en": ["Sit upright, relax your shoulders.","Slowly tilt your head to the right, ear towards right shoulder, hold 5 seconds.","Return to center position.","Tilt head to the left, ear towards left shoulder, hold 5 seconds.","Gently rotate head right-left, 5 times each side. Don't tilt backward."]
    },
    {
        "id": 4, "name": "Bài tập tay và vai", "name_en": "Arm & Shoulder Exercises",
        "duration": "10 phút", "duration_en": "10 minutes", "icon": "💪",
        "image": "/static/img/exercise_arms.png",
        "description": "Tăng sức mạnh tay, cải thiện phối hợp vận động.",
        "description_en": "Strengthen arms, improve motor coordination.",
        "steps": ["Ngồi thẳng trên ghế, hai tay buông dọc hai bên.","Từ từ nâng cả hai tay lên ngang vai, lòng bàn tay úp xuống.","Giữ 2 giây, sau đó hạ tay xuống từ từ.","Tiếp theo, nâng tay ra phía trước ngang vai, giữ 2 giây.","Thực hiện 10 lần mỗi động tác, nghỉ 30 giây giữa các set."],
        "steps_en": ["Sit upright, arms hanging at your sides.","Slowly raise both arms to shoulder height, palms facing down.","Hold 2 seconds, then lower slowly.","Next, raise arms forward to shoulder height, hold 2 seconds.","Do 10 reps per movement, rest 30 seconds between sets."]
    },
    {
        "id": 5, "name": "Bài tập thăng bằng", "name_en": "Balance Training",
        "duration": "10 phút", "duration_en": "10 minutes", "icon": "⚖️",
        "image": "/static/img/exercise_balance.png",
        "description": "Phòng ngã, tăng sự tự tin khi di chuyển hàng ngày.",
        "description_en": "Prevent falls, boost confidence in daily movement.",
        "steps": ["Đứng sau ghế, hai tay nhẹ nhàng bám vào lưng ghế.","Từ từ nâng gót chân phải lên khỏi sàn, đứng bằng mũi bàn chân trái.","Giữ thăng bằng 5-10 giây, nhìn thẳng về phía trước.","Hạ gót chân xuống từ từ, đổi sang chân trái.","Mỗi chân thực hiện 5 lần, ngày tập 2 lần."],
        "steps_en": ["Stand behind a chair, hands lightly on the backrest.","Slowly lift your right heel off the floor, stand on your left toes.","Balance for 5-10 seconds, look straight ahead.","Lower your heel slowly, switch to left leg.","5 reps per leg, twice daily."]
    },
    {
        "id": 6, "name": "Yoga nhẹ ngồi ghế", "name_en": "Chair Yoga",
        "duration": "15 phút", "duration_en": "15 minutes", "icon": "🧘‍♀️",
        "image": "/static/img/exercise_breathing.png",
        "description": "Yoga phù hợp người cao tuổi, tăng linh hoạt và thư giãn.",
        "description_en": "Senior-friendly yoga for flexibility and relaxation.",
        "steps": ["Ngồi thẳng, hai bàn chân đặt phẳng trên sàn.","Hít vào và giơ tay lên cao, kéo dài cột sống.","Thở ra và xoay người sang phải, tay trái đặt lên đầu gối phải, giữ 5 giây.","Hít vào trở về trung tâm, thở ra xoay sang trái tương tự.","Thực hiện 5 lần mỗi bên, chuyển động chậm và nhịp nhàng."],
        "steps_en": ["Sit upright, both feet flat on the floor.","Inhale and raise arms overhead, elongate your spine.","Exhale and twist to the right, left hand on right knee, hold 5 seconds.","Inhale back to center, exhale twist to the left similarly.","Do 5 reps each side, move slowly and rhythmically."]
    },
]

# --- DB Dependency ---
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Global variables for lazy loading ML model
_ml_model = None
_ml_meta = None

def get_ml_resources():
    global _ml_model, _ml_meta
    if _ml_model is None:
        _ml_model, _ml_meta = stroke_logic.load_artifacts()
    return _ml_model, _ml_meta

def get_current_user(request: Request, db: Session):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    try:
        return db.query(models.User).filter(models.User.id == int(user_id)).first()
    except Exception:
        return None

# ============================================================
# AUTH ROUTES
# ============================================================

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def login_post(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    action: str = Form(...),
    age: float = Form(None),
    gender: str = Form(None),
    work_type: str = Form(None),
    ever_married: str = Form(None),
    residence_type: str = Form(None),
    smoking_status: str = Form(None),
    heart_disease: int = Form(0),
    hypertension_history: int = Form(0),
    bmi: float = Form(None),
    db: Session = Depends(get_db)
):
    if action == "register":
        existing = db.query(models.User).filter(models.User.username == username).first()
        if existing:
            return templates.TemplateResponse(request=request, name="login.html",
                context={"error": "Tên đăng nhập đã tồn tại", "tab": "register"})
        hashed_pw = auth.get_password_hash(password)
        new_user = models.User(
            username=username, password_hash=hashed_pw,
            age=age, gender=gender, work_type=work_type,
            ever_married=ever_married, residence_type=residence_type,
            smoking_status=smoking_status, heart_disease=heart_disease,
            hypertension_history=hypertension_history, bmi=bmi
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        resp = RedirectResponse(url="/", status_code=302)
        resp.set_cookie(key="user_id", value=str(new_user.id), path="/", httponly=True, max_age=2592000)
        return resp
    else:
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user or not auth.verify_password(password, user.password_hash):
            return templates.TemplateResponse(request=request, name="login.html",
                context={"error": "Sai tên đăng nhập hoặc mật khẩu", "tab": "login"})
        resp = RedirectResponse(url="/", status_code=302)
        resp.set_cookie(key="user_id", value=str(user.id), path="/", httponly=True, max_age=2592000)
        return resp

@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/login")
    resp.delete_cookie("user_id", path="/")
    return resp

# ============================================================
# PROFILE ROUTES
# ============================================================

@app.get("/profile", response_class=HTMLResponse)
async def profile_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    records = db.query(models.HealthRecord).filter(
        models.HealthRecord.user_id == user.id
    ).order_by(models.HealthRecord.date.desc()).limit(10).all()
    return templates.TemplateResponse(request=request, name="profile.html",
        context={"user": user, "recent_records": records})

@app.post("/profile")
async def profile_post(
    request: Request,
    age: float = Form(...),
    gender: str = Form(...),
    work_type: str = Form(...),
    ever_married: str = Form(...),
    residence_type: str = Form(...),
    smoking_status: str = Form(...),
    heart_disease: int = Form(0),
    hypertension_history: int = Form(0),
    bmi: float = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    user.age = age
    user.gender = gender
    user.work_type = work_type
    user.ever_married = ever_married
    user.residence_type = residence_type
    user.smoking_status = smoking_status
    user.heart_disease = heart_disease
    user.hypertension_history = hypertension_history
    user.bmi = bmi
    db.commit()
    return RedirectResponse(url="/profile", status_code=302)

# ============================================================
# DASHBOARD
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    records = db.query(models.HealthRecord).filter(
        models.HealthRecord.user_id == user.id
    ).order_by(models.HealthRecord.date.asc()).all()
    
    dates = [r.date.strftime("%d/%m/%Y") for r in records]
    systolic_data = [r.systolic for r in records]
    diastolic_data = [r.diastolic for r in records]
    stroke_scores = [r.final_score for r in records]
    glucose_data = [r.avg_glucose_level for r in records]
    latest_record = records[-1] if records else None
    
    # Parse advice for latest record (bilingual)
    advice_list_vi = []
    advice_list_en = []
    if latest_record and latest_record.advice:
        try:
            advice_list_vi = json.loads(latest_record.advice)
        except Exception:
            advice_list_vi = [latest_record.advice]
        # Generate English advice fresh from the same data
        advice_list_en = stroke_logic.generate_advice_en(
            final_score=latest_record.final_score,
            systolic=latest_record.systolic, diastolic=latest_record.diastolic,
            avg_glucose=latest_record.avg_glucose_level or 0,
            age=latest_record.age or 50.0,
            fast_f=latest_record.fast_f or 0, fast_a=latest_record.fast_a or 0,
            fast_s=latest_record.fast_s or 0, fast_t=latest_record.fast_t or 0,
            heart_disease=latest_record.heart_disease or 0,
            smoking_status=latest_record.smoking_status or "never smoked",
        )

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": user,
        "dates": json.dumps(dates),
        "systolic": json.dumps(systolic_data),
        "diastolic": json.dumps(diastolic_data),
        "stroke_scores": json.dumps(stroke_scores),
        "glucose_data": json.dumps(glucose_data),
        "latest_record": latest_record,
        "advice_list_vi": advice_list_vi,
        "advice_list_en": advice_list_en,
    })

# ============================================================
# DAILY DATA ENTRY
# ============================================================

@app.get("/form", response_class=HTMLResponse)
async def form_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="form.html", context={"user": user})

@app.post("/form")
async def form_post(
    request: Request,
    systolic: int = Form(...),
    diastolic: int = Form(...),
    avg_glucose_level: str = Form(None),
    fast_f: int = Form(0),
    fast_a: int = Form(0),
    fast_s: int = Form(0),
    fast_t: int = Form(0),
    record_date: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Guard: user must have profile set up
    if user.age is None or user.bmi is None:
        return RedirectResponse(url="/profile?setup=1", status_code=302)
        
    hypertension = 1 if systolic >= 140 or diastolic >= 90 else 0
    
    try:
        parsed_glucose = float(avg_glucose_level) if avg_glucose_level and str(avg_glucose_level).strip() else None
    except ValueError:
        parsed_glucose = None
    
    # Lazy load ML resources
    ml_model, meta = get_ml_resources()
    
    df_row = stroke_logic.build_feature_row(
        age=user.age, gender=user.gender, work_type=user.work_type,
        smoking_status=user.smoking_status, hypertension=hypertension,
        heart_disease=user.heart_disease, avg_glucose_level=parsed_glucose,
        bmi=user.bmi, feature_names=meta["feature_names"] if meta else []
    )
    
    ml_prob = 0.0
    if ml_model and meta:
        ml_prob = stroke_logic.get_ml_probability(df_row, meta["scaler"], ml_model)
    
    risk_summary = stroke_logic.compute_risk_summary(
        ml_probability=ml_prob,
        fast_f=fast_f, fast_a=fast_a, fast_s=fast_s, fast_t=fast_t,
        systolic=systolic, diastolic=diastolic,
        avg_glucose=parsed_glucose,
        age=user.age or 50.0,
    )
    
    advice_items = stroke_logic.generate_advice(
        final_score=risk_summary["final_score"],
        systolic=systolic, diastolic=diastolic,
        avg_glucose=parsed_glucose, age=user.age or 50.0,
        fast_f=fast_f, fast_a=fast_a, fast_s=fast_s, fast_t=fast_t,
        heart_disease=user.heart_disease or 0,
        smoking_status=user.smoking_status or "never smoked",
    )
    
    record_date_obj = datetime.datetime.strptime(record_date, "%Y-%m-%d").date()
    advice_json = json.dumps(advice_items, ensure_ascii=False)
    
    existing = db.query(models.HealthRecord).filter(
        models.HealthRecord.user_id == user.id,
        models.HealthRecord.date == record_date_obj
    ).first()
    
    fields = dict(
        age=user.age, gender=user.gender, work_type=user.work_type,
        ever_married=user.ever_married, residence_type=user.residence_type,
        smoking_status=user.smoking_status, systolic=systolic, diastolic=diastolic,
        heart_disease=user.heart_disease, avg_glucose_level=parsed_glucose,
        bmi=user.bmi, fast_f=fast_f, fast_a=fast_a, fast_s=fast_s, fast_t=fast_t,
        ml_score=risk_summary["ml_score"], fast_sum=risk_summary["fast_sum"],
        combined_score=risk_summary["combined_score"], final_score=risk_summary["final_score"],
        override_msg=risk_summary["override_msg"], advice=advice_json,
    )
    
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(models.HealthRecord(user_id=user.id, date=record_date_obj, **fields))
    
    db.commit()
    return RedirectResponse(url="/", status_code=302)

# ============================================================
# EXERCISE
# ============================================================

@app.get("/exercise", response_class=HTMLResponse)
async def exercise_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    today = datetime.date.today()
    already_done = user.last_exercise_date == today
    
    return templates.TemplateResponse(request=request, name="exercise.html", context={
        "user": user,
        "exercises": EXERCISES,
        "already_done": already_done,
        "today": today.strftime("%d/%m/%Y"),
    })

@app.post("/exercise/complete")
async def exercise_complete(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    today = datetime.date.today()
    
    if user.last_exercise_date == today:
        return JSONResponse({"streak": user.exercise_streak, "already_done": True})
    
    yesterday = today - datetime.timedelta(days=1)
    if user.last_exercise_date == yesterday:
        user.exercise_streak = (user.exercise_streak or 0) + 1
    else:
        user.exercise_streak = 1  # Streak broken or first time
    
    user.last_exercise_date = today
    db.commit()
    
    return JSONResponse({"streak": user.exercise_streak, "already_done": False})

# ============================================================
# REPORT (Báo Cáo)
# ============================================================

@app.get("/report", response_class=HTMLResponse)
async def report_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    records = db.query(models.HealthRecord).filter(
        models.HealthRecord.user_id == user.id
    ).order_by(models.HealthRecord.date.asc()).all()
    
    if not records:
        return templates.TemplateResponse(request=request, name="report.html", context={
            "user": user, "records": []
        })
    
    dates = [r.date.strftime("%d/%m/%Y") for r in records]
    systolic_data = [r.systolic for r in records]
    diastolic_data = [r.diastolic for r in records]
    risk_scores = [r.final_score for r in records]
    
    avg_sys = round(sum(systolic_data) / len(systolic_data))
    avg_dia = round(sum(diastolic_data) / len(diastolic_data))
    gluc_values = [r.avg_glucose_level for r in records if r.avg_glucose_level is not None]
    avg_gluc = round(sum(gluc_values) / len(gluc_values), 1) if gluc_values else 0
    avg_risk = round(sum(risk_scores) / len(risk_scores))
    
    # Generate personalized advice (VI)
    diet_vi, rest_vi, ex_vi, warn_vi = [], [], [], []
    diet_en, rest_en, ex_en, warn_en = [], [], [], []
    
    if avg_sys >= 140 or avg_dia >= 90:
        diet_vi += ["Giảm muối trong bữa ăn (dưới 5g/ngày). Tránh thực phẩm chế biến sẵn.","Tăng cường rau xanh, trái cây giàu kali như chuối, cam, khoai lang."]
        diet_en += ["Reduce salt intake (under 5g/day). Avoid processed foods.","Increase green vegetables, potassium-rich fruits like bananas, oranges, sweet potatoes."]
    else:
        diet_vi.append("Huyết áp ổn định — tiếp tục duy trì chế độ ăn lành mạnh hiện tại.")
        diet_en.append("Blood pressure stable — continue your current healthy diet.")
    
    if avg_gluc > 140:
        diet_vi.append("Đường huyết cao — hạn chế tinh bột trắng, đồ ngọt. Ưu tiên ngũ cốc nguyên hạt.")
        diet_en.append("High blood glucose — limit refined carbs and sweets. Prefer whole grains.")
        warn_vi.append("Đường huyết trung bình vượt ngưỡng an toàn. Nên tham khảo ý kiến bác sĩ.")
        warn_en.append("Average blood glucose exceeds safe threshold. Consult your doctor.")
    elif avg_gluc > 100:
        diet_vi.append("Đường huyết hơi cao — giảm đồ ngọt, ăn nhiều chất xơ.")
        diet_en.append("Blood glucose slightly high — reduce sweets, eat more fiber.")
    
    rest_vi += ["Ngủ đủ 7-8 tiếng mỗi đêm, đi ngủ và thức dậy đúng giờ.","Tránh sử dụng thiết bị điện tử 30 phút trước khi ngủ."]
    rest_en += ["Sleep 7-8 hours per night, maintain a consistent sleep schedule.","Avoid electronic devices 30 minutes before bed."]
    if avg_risk >= 50:
        rest_vi.append("Nguy cơ đột quỵ cao — cần nghỉ ngơi đầy đủ, tránh căng thẳng kéo dài.")
        rest_en.append("High stroke risk — ensure adequate rest, avoid prolonged stress.")
    
    ex_vi += ["Đi bộ nhẹ 20-30 phút mỗi ngày giúp cải thiện tuần hoàn máu.","Tập thở sâu 10 phút/ngày giúp ổn định huyết áp và giảm stress."]
    ex_en += ["Light walking 20-30 minutes daily improves blood circulation.","Deep breathing 10 min/day helps stabilize blood pressure and reduce stress."]
    streak = user.exercise_streak or 0
    if streak >= 7:
        ex_vi.append(f"Tuyệt vời! Bạn đã duy trì chuỗi {streak} ngày tập liên tiếp 🔥")
        ex_en.append(f"Amazing! You've maintained a {streak}-day exercise streak 🔥")
    elif streak > 0:
        ex_vi.append(f"Bạn đang ở chuỗi {streak} ngày — hãy cố gắng duy trì nhé!")
        ex_en.append(f"You're on a {streak}-day streak — keep it up!")
    else:
        ex_vi.append("Hãy bắt đầu tập luyện hàng ngày để cải thiện sức khỏe tim mạch.")
        ex_en.append("Start exercising daily to improve cardiovascular health.")
    
    if avg_risk >= 75:
        warn_vi.append("Nguy cơ đột quỵ RẤT CAO — cần đến cơ sở y tế kiểm tra ngay.")
        warn_en.append("VERY HIGH stroke risk — visit a medical facility for examination immediately.")
    elif avg_risk >= 55:
        warn_vi.append("Nguy cơ đột quỵ CAO — nên đặt lịch khám bác sĩ trong tuần này.")
        warn_en.append("HIGH stroke risk — schedule a doctor's appointment this week.")
    
    return templates.TemplateResponse(request=request, name="report.html", context={
        "user": user, "records": records,
        "dates": json.dumps(dates),
        "systolic": json.dumps(systolic_data),
        "diastolic": json.dumps(diastolic_data),
        "risk_scores": json.dumps(risk_scores),
        "avg_systolic": avg_sys, "avg_diastolic": avg_dia,
        "avg_glucose": avg_gluc, "avg_risk": avg_risk,
        "total_records": len(records),
        "diet_vi": diet_vi, "rest_vi": rest_vi, "ex_vi": ex_vi, "warn_vi": warn_vi,
        "diet_en": diet_en, "rest_en": rest_en, "ex_en": ex_en, "warn_en": warn_en,
    })

# ============================================================
# SCHEDULE (Lịch)
# ============================================================

@app.get("/schedule", response_class=HTMLResponse)
async def schedule_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    today = datetime.date.today()
    schedules = db.query(models.Schedule).filter(
        models.Schedule.user_id == user.id,
        models.Schedule.date >= today
    ).order_by(models.Schedule.date.asc()).all()
    
    # Build date -> types map for calendar dots
    all_schedules = db.query(models.Schedule).filter(
        models.Schedule.user_id == user.id
    ).all()
    schedule_dates = {}
    for s in all_schedules:
        key = s.date.strftime("%Y-%m-%d")
        if key not in schedule_dates:
            schedule_dates[key] = []
        if s.schedule_type not in schedule_dates[key]:
            schedule_dates[key].append(s.schedule_type)
    
    # Build all schedules as JSON for day-detail click
    all_schedules_json = []
    for s in all_schedules:
        all_schedules_json.append({
            "date": s.date.strftime("%Y-%m-%d"),
            "title": s.title,
            "desc": s.description or "",
            "time": s.time or "",
            "type": s.schedule_type,
        })
    
    return templates.TemplateResponse(request=request, name="schedule.html", context={
        "user": user,
        "schedules": schedules,
        "schedule_dates": json.dumps(schedule_dates),
        "all_schedules_json": json.dumps(all_schedules_json, ensure_ascii=False),
        "current_month": today.month,
        "current_year": today.year,
    })

@app.post("/schedule")
async def schedule_post(
    request: Request,
    title: str = Form(...),
    schedule_type: str = Form(...),
    date: str = Form(...),
    time: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    new_schedule = models.Schedule(
        user_id=user.id,
        title=title,
        schedule_type=schedule_type,
        date=date_obj,
        time=time or None,
        description=description or None,
    )
    db.add(new_schedule)
    db.commit()
    return RedirectResponse(url="/schedule", status_code=302)

@app.delete("/schedule/{schedule_id}")
async def schedule_delete(schedule_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    schedule = db.query(models.Schedule).filter(
        models.Schedule.id == schedule_id,
        models.Schedule.user_id == user.id
    ).first()
    if schedule:
        db.delete(schedule)
        db.commit()
    return JSONResponse({"ok": True})

# ============================================================
# HOSPITALS API (for Google Maps)
# ============================================================

@app.get("/api/hospitals")
async def hospitals_api():
    """Return Google Maps search URL for nearby hospitals."""
    return JSONResponse({
        "maps_url": "https://www.google.com/maps/search/bệnh+viện+gần+đây/",
        "maps_embed_search": "hospital+near+me",
    })

