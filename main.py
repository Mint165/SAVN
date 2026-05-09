import datetime
import json
import os
import secrets
from typing import Type

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

import auth
import database
import models
import stroke_logic
from schemas import (
    DailyRecordPayload,
    ExerciseCompletePayload,
    LoginPayload,
    LogoutPayload,
    ProfilePayload,
    ScheduleDeletePayload,
    SchedulePayload,
    TriggerGoldenHourPayload,
)


try:
    models.Base.metadata.create_all(bind=database.engine)
except Exception as exc:
    print(f"DB creation skipped or failed: {exc}")


app = FastAPI()

CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_FORM_FIELD = "csrf_token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "session" not in request.scope:
            return await call_next(request)

        if "csrf_token" not in request.session:
            request.session["csrf_token"] = secrets.token_urlsafe(32)
        request.state.csrf_token = request.session["csrf_token"]

        if request.method not in SAFE_METHODS:
            provided_token = request.headers.get(CSRF_HEADER_NAME, "")
            if not provided_token:
                content_type = request.headers.get("content-type", "")
                if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                    form = await request.form()
                    request.state.cached_form_payload = {
                        key: value for key, value in form.items() if key != CSRF_FORM_FIELD
                    }
                    provided_token = str(form.get(CSRF_FORM_FIELD, ""))

            expected_token = str(request.session.get("csrf_token", ""))
            if not provided_token or not secrets.compare_digest(provided_token, expected_token):
                if is_json_request(request):
                    return JSONResponse({"error": "Invalid CSRF token."}, status_code=403)
                return html_error_response("Invalid CSRF token.", status_code=403)

        return await call_next(request)


app.add_middleware(CSRFMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-session-secret-change-me"),
    session_cookie="savn_session",
    same_site="lax",
    https_only=os.getenv("SESSION_COOKIE_SECURE") == "1" or bool(os.getenv("VERCEL")),
    max_age=60 * 60 * 24 * 30,
)


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        import traceback

        print(f"CRITICAL ERROR: {exc}")
        traceback.print_exc()
        
        # Check if client prefers JSON
        accept = request.headers.get("accept", "")
        content_type = request.headers.get("content-type", "")
        if "application/json" in accept or "application/json" in content_type:
            return JSONResponse(
                {"error": f"System Error: {str(exc)}"},
                status_code=500
            )

        return HTMLResponse(
            content=(
                "<html><body><h1>System Error (HeartBits)</h1>"
                "<p>Please report this issue to support:</p>"
                f"<pre>{exc}</pre></body></html>"
            ),
            status_code=500,
        )


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_path = os.path.join(BASE_DIR, "static")
templates_path = os.path.join(BASE_DIR, "templates")

if not os.path.exists(static_path):
    static_path = os.path.join(BASE_DIR, "static_placeholder")
    os.makedirs(static_path, exist_ok=True)
if not os.path.exists(templates_path):
    templates_path = os.path.join(BASE_DIR, "templates_placeholder")
    os.makedirs(templates_path, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)


def from_json_filter(value):
    try:
        return json.loads(value)
    except Exception:
        return {}


templates.env.filters["from_json"] = from_json_filter


def is_json_request(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    accept = request.headers.get("accept", "")
    return "application/json" in content_type or "application/json" in accept


def flatten_validation_error(exc: ValidationError) -> str:
    messages = []
    for err in exc.errors():
        location = ".".join(str(part) for part in err.get("loc", []) if part != "__root__")
        message = err.get("msg", "Invalid input.")
        messages.append(f"{location}: {message}" if location else message)
    return " ".join(messages) or "Invalid input."


async def parse_request_payload(request: Request) -> dict:
    cached_form_payload = getattr(request.state, "cached_form_payload", None)
    if isinstance(cached_form_payload, dict):
        return cached_form_payload

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        return payload if isinstance(payload, dict) else {}

    form = await request.form()
    return {key: value for key, value in form.items() if key != CSRF_FORM_FIELD}


async def validate_request_payload(request: Request, model: Type[BaseModel]):
    payload = await parse_request_payload(request)
    return model.model_validate(payload)


def html_error_response(message: str, status_code: int = 403) -> HTMLResponse:
    return HTMLResponse(
        content=(
            "<html><body><h1>Request blocked</h1>"
            f"<p>{message}</p>"
            "</body></html>"
        ),
        status_code=status_code,
    )


EXERCISES = [
    {
        "id": 1,
        "name": "Tho sau thu gian",
        "name_en": "Deep Breathing Relaxation",
        "duration": "10 phut",
        "duration_en": "10 minutes",
        "icon": "Breath",
        "image": "/static/img/exercise_breathing.png",
        "description": "Bai tap tho nhe giup giam cang thang va on dinh nhip sinh hoc.",
        "description_en": "Gentle breathing practice for relaxation and rhythm control.",
        "steps": [
            "Ngoi thang lung tren ghe thoai mai.",
            "Hit vao cham bang mui trong 4 giay.",
            "Giu hoi tho 2 giay.",
            "Tho ra tu tu qua mieng trong 6 giay.",
            "Lap lai 10 lan.",
        ],
        "steps_en": [
            "Sit upright in a comfortable chair.",
            "Inhale slowly through the nose for 4 seconds.",
            "Hold for 2 seconds.",
            "Exhale slowly through the mouth for 6 seconds.",
            "Repeat 10 times.",
        ],
    },
    {
        "id": 2,
        "name": "Di bo tai cho",
        "name_en": "Walking in Place",
        "duration": "15 phut",
        "duration_en": "15 minutes",
        "icon": "Walk",
        "image": "/static/img/exercise_walking.png",
        "description": "Van dong tim mach nhe de ho tro tuan hoan.",
        "description_en": "Light cardio movement to support circulation.",
        "steps": [
            "Dung thang va bam nhe vao thanh ghe.",
            "Nang goi trai len roi ha xuong.",
            "Doi ben voi chan phai.",
            "Tiep tuc luan phien voi nhip cham.",
            "Thuc hien 20 buoc moi chan.",
        ],
        "steps_en": [
            "Stand straight and lightly hold a chair.",
            "Lift the left knee and lower it.",
            "Repeat with the right leg.",
            "Continue at a slow and steady pace.",
            "Do 20 steps per leg.",
        ],
    },
    {
        "id": 3,
        "name": "Gian co co",
        "name_en": "Neck Stretching",
        "duration": "5 phut",
        "duration_en": "5 minutes",
        "icon": "Stretch",
        "image": "/static/img/exercise_neck.png",
        "description": "Giam cang co vai va giup co the thu gian.",
        "description_en": "Relieve neck and shoulder tension.",
        "steps": [
            "Ngoi thang va tha long vai.",
            "Nghieng dau sang phai, giu 5 giay.",
            "Tro ve giua, doi ben trai.",
            "Quay nhe sang hai ben.",
            "Khong uon co ra sau.",
        ],
        "steps_en": [
            "Sit upright and relax the shoulders.",
            "Tilt your head right and hold 5 seconds.",
            "Return to center, then repeat left.",
            "Rotate gently to both sides.",
            "Do not tilt backward.",
        ],
    },
    {
        "id": 4,
        "name": "Tap tay va vai",
        "name_en": "Arm and Shoulder Exercises",
        "duration": "10 phut",
        "duration_en": "10 minutes",
        "icon": "Arms",
        "image": "/static/img/exercise_arms.png",
        "description": "Tang suc manh tay va cai thien phoi hop van dong.",
        "description_en": "Improve upper-body strength and coordination.",
        "steps": [
            "Ngoi thang tren ghe.",
            "Nang hai tay ngang vai va giu 2 giay.",
            "Ha xuong cham.",
            "Nang tay ve phia truoc va giu 2 giay.",
            "Lap lai 10 lan moi dong tac.",
        ],
        "steps_en": [
            "Sit upright on a chair.",
            "Raise both arms to shoulder height and hold 2 seconds.",
            "Lower slowly.",
            "Raise arms forward and hold 2 seconds.",
            "Repeat 10 times per movement.",
        ],
    },
    {
        "id": 5,
        "name": "Tap thang bang",
        "name_en": "Balance Training",
        "duration": "10 phut",
        "duration_en": "10 minutes",
        "icon": "Balance",
        "image": "/static/img/exercise_balance.png",
        "description": "Ho tro giu thang bang va giam nguy co nga.",
        "description_en": "Support balance and reduce fall risk.",
        "steps": [
            "Dung sau ghe va dat tay len tua lung.",
            "Nang got chan phai va giu thang bang.",
            "Ha xuong tu tu va doi ben.",
            "Nhin thang ve phia truoc.",
            "Tap 5 lan moi ben.",
        ],
        "steps_en": [
            "Stand behind a chair with hands on the backrest.",
            "Lift the right heel and balance.",
            "Lower slowly and switch sides.",
            "Look straight ahead.",
            "Repeat 5 times per side.",
        ],
    },
    {
        "id": 6,
        "name": "Yoga ghe nhe",
        "name_en": "Chair Yoga",
        "duration": "15 phut",
        "duration_en": "15 minutes",
        "icon": "Yoga",
        "image": "/static/img/exercise_breathing.png",
        "description": "Chuyen dong nhe de tang linh hoat va thu gian.",
        "description_en": "Gentle seated yoga for flexibility and calm.",
        "steps": [
            "Ngoi vung va dat hai chan tren san.",
            "Hit vao va dua tay len cao.",
            "Tho ra va xoay nhe sang phai.",
            "Tro ve giua va doi ben trai.",
            "Lap lai 5 lan moi ben.",
        ],
        "steps_en": [
            "Sit steadily with both feet on the floor.",
            "Inhale and raise the arms overhead.",
            "Exhale and twist gently to the right.",
            "Return to center and repeat left.",
            "Repeat 5 times per side.",
        ],
    },
]


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


_ml_model = None
_ml_meta = None


def get_ml_resources():
    global _ml_model, _ml_meta
    if _ml_model is None:
        _ml_model, _ml_meta = stroke_logic.load_artifacts()
    return _ml_model, _ml_meta


def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        return db.query(models.User).filter(models.User.id == int(user_id)).first()
    except Exception:
        return None


def set_authenticated_session(request: Request, user: models.User) -> None:
    csrf_token = request.session.get("csrf_token")
    request.session.clear()
    request.session["user_id"] = int(user.id)
    request.session["csrf_token"] = csrf_token or secrets.token_urlsafe(32)


def clear_authenticated_session(request: Request) -> None:
    csrf_token = request.session.get("csrf_token")
    request.session.clear()
    request.session["csrf_token"] = csrf_token or secrets.token_urlsafe(32)


def render_login_template(request: Request, error: str | None = None, tab: str | None = None, status_code: int = 200):
    context = {}
    if error:
        context["error"] = error
    if tab:
        context["tab"] = tab
    return templates.TemplateResponse(request=request, name="login.html", context=context, status_code=status_code)


def build_profile_context(user: models.User, db: Session, error: str | None = None) -> dict:
    records = db.query(models.HealthRecord).filter(
        models.HealthRecord.user_id == user.id
    ).order_by(models.HealthRecord.date.desc()).limit(10).all()
    context = {"user": user, "recent_records": records}
    if error:
        context["error"] = error
    return context


def build_schedule_context(user: models.User, db: Session, error: str | None = None) -> dict:
    today = datetime.date.today()
    schedules = db.query(models.Schedule).filter(
        models.Schedule.user_id == user.id,
        models.Schedule.date >= today,
    ).order_by(models.Schedule.date.asc()).all()

    all_schedules = db.query(models.Schedule).filter(models.Schedule.user_id == user.id).all()
    schedule_dates = {}
    for schedule in all_schedules:
        key = schedule.date.strftime("%Y-%m-%d")
        schedule_dates.setdefault(key, [])
        if schedule.schedule_type not in schedule_dates[key]:
            schedule_dates[key].append(schedule.schedule_type)

    all_schedules_json = []
    for schedule in all_schedules:
        all_schedules_json.append(
            {
                "id": schedule.id,
                "date": schedule.date.strftime("%Y-%m-%d"),
                "title": schedule.title,
                "desc": schedule.description or "",
                "time": schedule.time or "",
                "type": schedule.schedule_type,
            }
        )

    context = {
        "user": user,
        "schedules": schedules,
        "schedule_dates": json.dumps(schedule_dates),
        "all_schedules_json": json.dumps(all_schedules_json, ensure_ascii=False),
        "current_month": today.month,
        "current_year": today.year,
    }
    if error:
        context["error"] = error
    return context


def build_xai_payload_from_record(record, user):
    if not record or not user:
        return None

    _, ml_meta = get_ml_resources()
    if not ml_meta:
        return None

    hypertension = record.hypertension
    if hypertension is None:
        hypertension = 1 if (record.systolic or 0) >= 140 or (record.diastolic or 0) >= 90 else 0

    feature_df = stroke_logic.build_feature_row(
        age=record.age if record.age is not None else user.age,
        gender=record.gender or user.gender,
        work_type=record.work_type or user.work_type,
        smoking_status=record.smoking_status or user.smoking_status,
        hypertension=hypertension,
        heart_disease=record.heart_disease or 0,
        avg_glucose_level=record.avg_glucose_level,
        bmi=record.bmi if record.bmi is not None else user.bmi,
        feature_names=ml_meta["feature_names"],
    )
    xai_factors = stroke_logic.calc_xai_groups(feature_df, ml_meta)

    return {
        "ml": xai_factors,
        "fast": {
            "fast_f_label": stroke_logic.FAST_POINTS.get(record.fast_f or 0, 0),
            "fast_a_label": stroke_logic.FAST_POINTS.get(record.fast_a or 0, 0),
            "fast_s_label": stroke_logic.FAST_POINTS.get(record.fast_s or 0, 0),
            "fast_t_label": stroke_logic.FAST_POINTS.get(record.fast_t or 0, 0),
        },
        "ml_total": record.ml_score or 0,
        "fast_total": record.fast_sum or 0,
        "weighted_ml": round((record.ml_score or 0) * 0.4, 1),
        "weighted_fast": round(((record.fast_sum or 0) / 100) * 60, 1),
        "final_score": record.final_score or 0,
        "insights_vi": stroke_logic.build_xai_insights(
            xai_factors,
            record.systolic,
            record.diastolic,
            record.avg_glucose_level,
            record.bmi if record.bmi is not None else user.bmi,
            record.age if record.age is not None else user.age,
            record.smoking_status or user.smoking_status,
            record.heart_disease or 0,
            lang="vi",
        ),
        "insights_en": stroke_logic.build_xai_insights(
            xai_factors,
            record.systolic,
            record.diastolic,
            record.avg_glucose_level,
            record.bmi if record.bmi is not None else user.bmi,
            record.age if record.age is not None else user.age,
            record.smoking_status or user.smoking_status,
            record.heart_disease or 0,
            lang="en",
        ),
    }


def enrich_xai_payload(record, user):
    if not record:
        return None

    xai = None
    try:
        if record.xai_data:
            xai = json.loads(record.xai_data)
    except Exception:
        xai = None

    rebuilt = build_xai_payload_from_record(record, user)
    if not xai:
        return rebuilt

    xai["ml"] = stroke_logic.normalize_xai_groups(xai.get("ml", {}))
    if rebuilt:
        for key, value in rebuilt.items():
            if key not in xai or xai.get(key) in (None, {}, []):
                xai[key] = value
        if not xai["ml"]:
            xai["ml"] = rebuilt.get("ml", {})

    if "insights_vi" not in xai:
        xai["insights_vi"] = stroke_logic.build_xai_insights(
            xai.get("ml", {}),
            record.systolic,
            record.diastolic,
            record.avg_glucose_level,
            user.bmi,
            user.age,
            user.smoking_status,
            user.heart_disease or 0,
            lang="vi",
        )
    if "insights_en" not in xai:
        xai["insights_en"] = stroke_logic.build_xai_insights(
            xai.get("ml", {}),
            record.systolic,
            record.diastolic,
            record.avg_glucose_level,
            user.bmi,
            user.age,
            user.smoking_status,
            user.heart_disease or 0,
            lang="en",
        )
    return xai


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return render_login_template(request)


@app.post("/login")
async def login_post(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await validate_request_payload(request, LoginPayload)
    except ValidationError as exc:
        raw_payload = await parse_request_payload(request)
        tab = "register" if raw_payload.get("action") == "register" else "login"
        return render_login_template(request, error=flatten_validation_error(exc), tab=tab, status_code=422)

    username = payload.username.strip()
    if payload.action == "register":
        existing = db.query(models.User).filter(models.User.username == username).first()
        if existing:
            return render_login_template(request, error="Username already exists.", tab="register", status_code=409)

        new_user = models.User(
            username=username,
            password_hash=auth.get_password_hash(payload.password),
            age=payload.age,
            gender=payload.gender,
            work_type=payload.work_type,
            ever_married=payload.ever_married,
            residence_type=payload.residence_type,
            smoking_status=payload.smoking_status,
            heart_disease=payload.heart_disease,
            hypertension_history=payload.hypertension_history,
            bmi=payload.bmi,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        set_authenticated_session(request, new_user)
        return RedirectResponse(url="/", status_code=302)

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not auth.verify_password(payload.password, user.password_hash):
        return render_login_template(request, error="Invalid username or password.", tab="login", status_code=401)

    set_authenticated_session(request, user)
    return RedirectResponse(url="/", status_code=302)


@app.get("/logout")
async def logout_get():
    return html_error_response("Use POST to logout.", status_code=405)


@app.post("/logout")
async def logout_post(request: Request):
    try:
        await validate_request_payload(request, LogoutPayload)
    except ValidationError as exc:
        return html_error_response(flatten_validation_error(exc), status_code=422)

    clear_authenticated_session(request)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/profile", response_class=HTMLResponse)
async def profile_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="profile.html", context=build_profile_context(user, db))


@app.post("/profile")
async def profile_post(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        payload = await validate_request_payload(request, ProfilePayload)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="profile.html",
            context=build_profile_context(user, db, error=flatten_validation_error(exc)),
            status_code=422,
        )

    user.age = payload.age
    user.gender = payload.gender
    user.work_type = payload.work_type
    user.ever_married = payload.ever_married
    user.residence_type = payload.residence_type
    user.smoking_status = payload.smoking_status
    user.heart_disease = payload.heart_disease
    user.hypertension_history = payload.hypertension_history
    user.bmi = payload.bmi
    user.emergency_phone = payload.emergency_phone
    db.commit()
    return RedirectResponse(url="/profile", status_code=302)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    records = db.query(models.HealthRecord).filter(
        models.HealthRecord.user_id == user.id
    ).order_by(models.HealthRecord.date.asc()).all()

    dates = [record.date.strftime("%d/%m/%Y") for record in records]
    systolic_data = [record.systolic for record in records]
    diastolic_data = [record.diastolic for record in records]
    stroke_scores = [record.final_score for record in records]
    glucose_data = [record.avg_glucose_level for record in records]
    latest_record = records[-1] if records else None

    xai_data = enrich_xai_payload(latest_record, user)
    xai_factors = xai_data.get("ml", {}) if xai_data else {}

    advice_list_vi = []
    advice_list_en = []
    if latest_record and latest_record.advice:
        try:
            advice_list_vi = json.loads(latest_record.advice)
        except Exception:
            advice_list_vi = [latest_record.advice]
        advice_list_en = stroke_logic.generate_advice_en(
            final_score=latest_record.final_score,
            systolic=latest_record.systolic,
            diastolic=latest_record.diastolic,
            avg_glucose=latest_record.avg_glucose_level or 0,
            age=latest_record.age or 50.0,
            fast_f=latest_record.fast_f or 0,
            fast_a=latest_record.fast_a or 0,
            fast_s=latest_record.fast_s or 0,
            fast_t=latest_record.fast_t or 0,
            heart_disease=latest_record.heart_disease or 0,
            smoking_status=latest_record.smoking_status or "never smoked",
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "dates": json.dumps(dates),
            "systolic": json.dumps(systolic_data),
            "diastolic": json.dumps(diastolic_data),
            "stroke_scores": json.dumps(stroke_scores),
            "glucose_data": json.dumps(glucose_data),
            "latest_record": latest_record,
            "advice_list_vi": advice_list_vi,
            "advice_list_en": advice_list_en,
            "xai": xai_data,
            "xai_msg": stroke_logic.get_key_factors_msg(xai_factors, "vi") if xai_factors else "",
            "xai_msg_en": stroke_logic.get_key_factors_msg(xai_factors, "en") if xai_factors else "",
        },
    )


@app.get("/form", response_class=HTMLResponse)
async def form_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="form.html", context={"user": user})


@app.post("/form")
async def form_post(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    if user.age is None or user.bmi is None:
        return RedirectResponse(url="/profile?setup=1", status_code=302)

    try:
        payload = await validate_request_payload(request, DailyRecordPayload)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="form.html",
            context={"user": user, "error": flatten_validation_error(exc)},
            status_code=422,
        )

    systolic = payload.systolic
    diastolic = payload.diastolic
    parsed_glucose = payload.avg_glucose_level
    hypertension = 1 if systolic >= 140 or diastolic >= 90 else 0

    ml_model, meta = get_ml_resources()
    df_row = stroke_logic.build_feature_row(
        age=user.age,
        gender=user.gender,
        work_type=user.work_type,
        smoking_status=user.smoking_status,
        hypertension=hypertension,
        heart_disease=user.heart_disease,
        avg_glucose_level=parsed_glucose,
        bmi=user.bmi,
        feature_names=meta["feature_names"] if meta else [],
    )

    ml_prob = 0.0
    if ml_model and meta:
        ml_prob = stroke_logic.get_ml_probability(df_row, meta["scaler"], ml_model)

    risk_summary = stroke_logic.compute_risk_summary(
        ml_probability=ml_prob,
        fast_f=payload.fast_f,
        fast_a=payload.fast_a,
        fast_s=payload.fast_s,
        fast_t=payload.fast_t,
        systolic=systolic,
        diastolic=diastolic,
        avg_glucose=parsed_glucose,
        age=user.age or 50.0,
    )

    advice_items = stroke_logic.generate_advice(
        final_score=risk_summary["final_score"],
        systolic=systolic,
        diastolic=diastolic,
        avg_glucose=parsed_glucose,
        age=user.age or 50.0,
        fast_f=payload.fast_f,
        fast_a=payload.fast_a,
        fast_s=payload.fast_s,
        fast_t=payload.fast_t,
        heart_disease=user.heart_disease or 0,
        smoking_status=user.smoking_status or "never smoked",
    )

    existing = db.query(models.HealthRecord).filter(
        models.HealthRecord.user_id == user.id,
        models.HealthRecord.date == payload.record_date,
    ).first()

    xai_factors = {}
    ml_model, ml_meta = get_ml_resources()
    if ml_model and ml_meta:
        feature_df = stroke_logic.build_feature_row(
            user.age,
            user.gender,
            user.work_type,
            user.smoking_status,
            hypertension,
            user.heart_disease or 0,
            parsed_glucose,
            user.bmi,
            ml_meta["feature_names"],
        )
        xai_factors = stroke_logic.calc_xai_groups(feature_df, ml_meta)

    fast_breakdown = {
        "fast_f_label": stroke_logic.FAST_POINTS.get(payload.fast_f, 0),
        "fast_a_label": stroke_logic.FAST_POINTS.get(payload.fast_a, 0),
        "fast_s_label": stroke_logic.FAST_POINTS.get(payload.fast_s, 0),
        "fast_t_label": stroke_logic.FAST_POINTS.get(payload.fast_t, 0),
    }

    insights_vi = stroke_logic.build_xai_insights(
        xai_factors,
        systolic,
        diastolic,
        parsed_glucose,
        user.bmi,
        user.age,
        user.smoking_status,
        user.heart_disease or 0,
        lang="vi",
    )
    insights_en = stroke_logic.build_xai_insights(
        xai_factors,
        systolic,
        diastolic,
        parsed_glucose,
        user.bmi,
        user.age,
        user.smoking_status,
        user.heart_disease or 0,
        lang="en",
    )

    xai_payload = json.dumps(
        {
            "ml": xai_factors,
            "fast": fast_breakdown,
            "ml_total": risk_summary["ml_score"],
            "fast_total": risk_summary["fast_sum"],
            "weighted_ml": risk_summary["weighted_ml"],
            "weighted_fast": risk_summary["weighted_fast"],
            "final_score": risk_summary["final_score"],
            "insights_vi": insights_vi,
            "insights_en": insights_en,
        },
        ensure_ascii=False,
    )

    fields = dict(
        age=user.age,
        gender=user.gender,
        work_type=user.work_type,
        ever_married=user.ever_married,
        residence_type=user.residence_type,
        smoking_status=user.smoking_status,
        systolic=systolic,
        diastolic=diastolic,
        heart_disease=user.heart_disease,
        hypertension=hypertension,
        avg_glucose_level=parsed_glucose,
        bmi=user.bmi,
        fast_f=payload.fast_f,
        fast_a=payload.fast_a,
        fast_s=payload.fast_s,
        fast_t=payload.fast_t,
        ml_score=risk_summary["ml_score"],
        fast_sum=risk_summary["fast_sum"],
        combined_score=risk_summary["combined_score"],
        final_score=risk_summary["final_score"],
        override_msg=risk_summary["override_msg"],
        advice=json.dumps(advice_items, ensure_ascii=False),
        xai_data=xai_payload,
    )

    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
    else:
        db.add(models.HealthRecord(user_id=user.id, date=payload.record_date, **fields))

    # Automatic Golden Hour trigger (threshold 70%)
    should_trigger = risk_summary["final_score"] >= 70
    if should_trigger:
        # Re-trigger if not started OR if the previous one is older than 4.5 hours
        is_expired = False
        if user.golden_hour_start:
            try:
                start_str = str(user.golden_hour_start)
                if start_str and start_str not in ("None", "null", ""):
                    start_dt = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=datetime.timezone.utc)
                    
                    now = datetime.datetime.now(datetime.timezone.utc)
                    if (now - start_dt).total_seconds() > 4.5 * 3600:
                        is_expired = True
                else:
                    is_expired = True
            except Exception:
                is_expired = True
        
        if not user.golden_hour_start or is_expired:
            user.golden_hour_start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    else:
        # If score is low, reset the Golden Hour timer
        user.golden_hour_start = None

    db.commit()
    return RedirectResponse(url="/", status_code=302)


@app.get("/exercise", response_class=HTMLResponse)
async def exercise_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    today = datetime.date.today()
    already_done = user.last_exercise_date == today
    return templates.TemplateResponse(
        request=request,
        name="exercise.html",
        context={
            "user": user,
            "exercises": EXERCISES,
            "already_done": already_done,
            "today": today.strftime("%d/%m/%Y"),
        },
    )


@app.post("/exercise/complete")
async def exercise_complete(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        await validate_request_payload(request, ExerciseCompletePayload)
    except ValidationError as exc:
        return JSONResponse({"error": flatten_validation_error(exc)}, status_code=422)

    today = datetime.date.today()
    if user.last_exercise_date == today:
        return JSONResponse({"streak": user.exercise_streak, "already_done": True})

    yesterday = today - datetime.timedelta(days=1)
    if user.last_exercise_date == yesterday:
        user.exercise_streak = (user.exercise_streak or 0) + 1
    else:
        user.exercise_streak = 1

    user.last_exercise_date = today
    db.commit()
    return JSONResponse({"streak": user.exercise_streak, "already_done": False})


@app.get("/report", response_class=HTMLResponse)
async def report_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    records = db.query(models.HealthRecord).filter(
        models.HealthRecord.user_id == user.id
    ).order_by(models.HealthRecord.date.asc()).all()

    if not records:
        return templates.TemplateResponse(request=request, name="report.html", context={"user": user, "records": []})

    dates = [record.date.strftime("%d/%m/%Y") for record in records]
    systolic_data = [record.systolic for record in records]
    diastolic_data = [record.diastolic for record in records]
    risk_scores = [record.final_score for record in records]

    avg_sys = round(sum(systolic_data) / len(systolic_data))
    avg_dia = round(sum(diastolic_data) / len(diastolic_data))
    gluc_values = [record.avg_glucose_level for record in records if record.avg_glucose_level is not None]
    avg_gluc = round(sum(gluc_values) / len(gluc_values), 1) if gluc_values else 0
    avg_risk = round(sum(risk_scores) / len(risk_scores))

    diet_vi, rest_vi, ex_vi, warn_vi = [], [], [], []
    diet_en, rest_en, ex_en, warn_en = [], [], [], []

    if avg_sys >= 140 or avg_dia >= 90:
        diet_vi += [
            "Giam muoi va tranh thuc pham che bien san.",
            "Tang rau xanh va trai cay giau kali.",
        ]
        diet_en += [
            "Reduce salt and avoid processed food.",
            "Increase vegetables and potassium-rich fruit.",
        ]
    else:
        diet_vi.append("Huyet ap on dinh. Tiep tuc duy tri che do an hien tai.")
        diet_en.append("Blood pressure is stable. Keep your current healthy diet.")

    if avg_gluc > 140:
        diet_vi.append("Duong huyet cao. Han che do ngot va tinh bot trang.")
        diet_en.append("High blood glucose. Limit sweets and refined carbs.")
        warn_vi.append("Duong huyet trung binh dang vuot nguong an toan.")
        warn_en.append("Average blood glucose is above the safer range.")
    elif avg_gluc > 100:
        diet_vi.append("Duong huyet hoi cao. Tang chat xo va giam duong.")
        diet_en.append("Blood glucose is slightly elevated. Increase fiber and reduce sugar.")

    rest_vi += [
        "Ngu 7-8 tieng moi dem va giu lich ngu deu.",
        "Tranh man hinh dien tu 30 phut truoc khi ngu.",
    ]
    rest_en += [
        "Sleep 7-8 hours nightly and keep a consistent schedule.",
        "Avoid screens 30 minutes before bed.",
    ]
    if avg_risk >= 50:
        rest_vi.append("Nguy co dang cao. Can nghi ngoi va giam stress.")
        rest_en.append("Risk is elevated. Prioritize rest and stress reduction.")

    ex_vi += [
        "Di bo nhe 20-30 phut moi ngay.",
        "Tap tho sau 10 phut moi ngay.",
    ]
    ex_en += [
        "Walk lightly for 20-30 minutes daily.",
        "Practice deep breathing for 10 minutes daily.",
    ]

    streak = user.exercise_streak or 0
    if streak >= 7:
        ex_vi.append(f"Ban dang co chuoi tap {streak} ngay lien tiep.")
        ex_en.append(f"You have maintained a {streak}-day exercise streak.")
    elif streak > 0:
        ex_vi.append(f"Ban dang o chuoi {streak} ngay. Tiep tuc duy tri.")
        ex_en.append(f"You are on a {streak}-day streak. Keep it going.")
    else:
        ex_vi.append("Hay bat dau tap luyen deu de ho tro tim mach.")
        ex_en.append("Start a daily routine to support cardiovascular health.")

    if avg_risk >= 75:
        warn_vi.append("Nguy co rat cao. Can den co so y te som nhat.")
        warn_en.append("Risk is very high. Seek medical care as soon as possible.")
    elif avg_risk >= 55:
        warn_vi.append("Nguy co cao. Nen dat lich kham trong tuan nay.")
        warn_en.append("Risk is high. Schedule a medical visit this week.")

    latest_record = records[-1]
    xai_data = enrich_xai_payload(latest_record, user)
    xai_msg = stroke_logic.get_key_factors_msg(xai_data["ml"], "vi") if xai_data and "ml" in xai_data else ""
    xai_msg_en = stroke_logic.get_key_factors_msg(xai_data["ml"], "en") if xai_data and "ml" in xai_data else ""

    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={
            "user": user,
            "records": records,
            "latest_record": latest_record,
            "xai": xai_data,
            "xai_msg": xai_msg,
            "xai_msg_en": xai_msg_en,
            "dates": json.dumps(dates),
            "systolic": json.dumps(systolic_data),
            "diastolic": json.dumps(diastolic_data),
            "risk_scores": json.dumps(risk_scores),
            "avg_systolic": avg_sys,
            "avg_diastolic": avg_dia,
            "avg_glucose": avg_gluc,
            "avg_risk": avg_risk,
            "total_records": len(records),
            "diet_vi": diet_vi,
            "rest_vi": rest_vi,
            "ex_vi": ex_vi,
            "warn_vi": warn_vi,
            "diet_en": diet_en,
            "rest_en": rest_en,
            "ex_en": ex_en,
            "warn_en": warn_en,
        },
    )


@app.get("/schedule", response_class=HTMLResponse)
async def schedule_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="schedule.html", context=build_schedule_context(user, db))


@app.post("/schedule")
async def schedule_post(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        payload = await validate_request_payload(request, SchedulePayload)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="schedule.html",
            context=build_schedule_context(user, db, error=flatten_validation_error(exc)),
            status_code=422,
        )

    new_schedule = models.Schedule(
        user_id=user.id,
        title=payload.title,
        schedule_type=payload.schedule_type,
        date=payload.date,
        time=payload.time,
        description=payload.description,
    )
    db.add(new_schedule)
    db.commit()
    return RedirectResponse(url="/schedule", status_code=302)


@app.delete("/schedule/{schedule_id}")
async def schedule_delete(schedule_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        payload = ScheduleDeletePayload.model_validate({"schedule_id": schedule_id})
    except ValidationError as exc:
        return JSONResponse({"error": flatten_validation_error(exc)}, status_code=422)

    schedule = db.query(models.Schedule).filter(
        models.Schedule.id == payload.schedule_id,
        models.Schedule.user_id == user.id,
    ).first()
    if schedule:
        db.delete(schedule)
        db.commit()
    return JSONResponse({"ok": True})


@app.get("/api/hospitals")
async def hospitals_api():
    return JSONResponse(
        {
            "maps_url": "https://www.google.com/maps/search/hospital+near+me/",
            "maps_embed_search": "hospital+near+me",
        }
    )


@app.post("/api/trigger-golden-hour")
async def trigger_golden_hour_api(request: Request, db: Session = Depends(get_db)):
    try:
        user = get_current_user(request, db)
        if not user:
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        payload = await validate_request_payload(request, TriggerGoldenHourPayload)
        
        # Re-trigger if not started OR if the previous one is older than 4.5 hours
        is_expired = False
        if user.golden_hour_start:
            try:
                # Use a more robust parsing method
                start_str = str(user.golden_hour_start)
                if start_str and start_str not in ("None", "null", ""):
                    start_dt = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    # Handle naive vs aware comparison
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=datetime.timezone.utc)
                    
                    now = datetime.datetime.now(datetime.timezone.utc)
                    if (now - start_dt).total_seconds() > 4.5 * 3600:
                        is_expired = True
                else:
                    is_expired = True
            except Exception:
                is_expired = True
        
        if not user.golden_hour_start or is_expired:
            user.golden_hour_start = datetime.datetime.now(datetime.timezone.utc).isoformat()
            db.commit()
        
        return JSONResponse({"ok": True, "start": str(user.golden_hour_start) if user.golden_hour_start else None, "source": payload.source})
    except Exception as exc:
        print(f"ERROR in trigger_golden_hour_api: {exc}")
        return JSONResponse({"error": str(exc)}, status_code=500)
