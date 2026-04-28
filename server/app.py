# ====================================================
# server/app.py — سيرفر التطبيق الذكي
# يشتغل مع البوتات في نفس الـ process عبر main.py
# ====================================================
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os, json, requests as _requests, pytz
from datetime import datetime

app = Flask(__name__)

# ── متغيرات البيئة (نفس البوت) ────────────────────────
SHEET_KEY      = os.environ.get("SHEET_KEY", "")
GCREDS_JSON    = os.environ.get("GOOGLE_CREDENTIALS", "")
GEMINI_KEY     = os.environ.get("GEMINI_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
FIREBASE_CREDS = os.environ.get("FIREBASE_CREDENTIALS", "")
YEMEN_TZ       = pytz.timezone("Asia/Aden")

scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

# ── Firebase Admin ────────────────────────────────────
_firebase_ready = False
try:
    import firebase_admin
    from firebase_admin import credentials as fb_creds, auth, messaging
    if FIREBASE_CREDS:
        fb_cred = fb_creds.Certificate(json.loads(FIREBASE_CREDS))
        firebase_admin.initialize_app(fb_cred)
        _firebase_ready = True
except Exception as _e:
    print(f"⚠️ Firebase Admin: {_e}")

# ── Google Sheets ─────────────────────────────────────
def get_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(GCREDS_JSON), scope)
    return gspread.authorize(creds).open_by_key(SHEET_KEY)

def verify_token(id_token):
    """تحقق من Firebase Token وأرجع uid أو None"""
    if not _firebase_ready:
        return None
    try:
        decoded = auth.verify_id_token(id_token)
        return decoded
    except:
        return None

# ══════════════════════════════════════════════════════
# 1. تسجيل الدخول والتحقق من الصلاحية
# ══════════════════════════════════════════════════════
@app.route("/check_user", methods=["POST"])
def check_user():
    data      = request.json or {}
    id_token  = data.get("idToken", "")
    app_hash  = data.get("appHash", "")
    fcm_token = data.get("fcmToken", "")

    # تحقق من Firebase Token
    decoded = verify_token(id_token)
    if not decoded:
        return jsonify({"allowed": False, "reason": "token_invalid"})

    firebase_uid   = decoded.get("uid", "")
    firebase_email = decoded.get("email", "").lower().strip()
    firebase_phone = decoded.get("phone_number", "")
    if firebase_phone:
        firebase_phone = firebase_phone.replace(" ", "").replace("-", "")

    try:
        ss    = get_sheet()
        sheet = ss.worksheet("المستخدمين")
        rows  = sheet.get_all_values()

        for i, row in enumerate(rows[1:], start=2):
            # عمود M = البريد (index 12)، عمود B = الهاتف (index 1)
            row_email = row[12].strip().lower() if len(row) > 12 else ""
            row_phone = row[1].strip().replace(" ","").replace("-","") \
                        if len(row) > 1 else ""

            match_email = firebase_email and row_email == firebase_email
            match_phone = firebase_phone and (
                row_phone.endswith(firebase_phone) or
                firebase_phone.endswith(row_phone)
            )

            if not (match_email or match_phone):
                continue

            # وُجد المستخدم ✅
            allowed = str(row[3]).upper() == "TRUE"
            admin   = str(row[4]).upper() == "TRUE"
            owner   = str(row[5]).upper() == "TRUE"
            ai_ok   = str(row[8]).upper() == "TRUE" if len(row) > 8 else False
            name    = row[0].strip()

            if not allowed:
                return jsonify({
                    "allowed": False,
                    "reason":  "not_allowed",
                    "name":    name
                })

            role = "owner" if owner else ("admin" if admin else "user")

            # حفظ firebase_uid + fcm_token في الشيت
            updates = {}
            if not (row[13].strip() if len(row) > 13 else ""):
                updates["uid_col"]  = (i, 14, firebase_uid)
            if fcm_token and not (row[14].strip() if len(row) > 14 else ""):
                updates["fcm_col"]  = (i, 15, fcm_token)
            for _, (r, c, v) in updates.items():
                sheet.update_cell(r, c, v)

            return jsonify({
                "allowed":   True,
                "name":      name,
                "role":      role,
                "aiAllowed": ai_ok,
                "uid":       firebase_uid
            })

        # المستخدم غير موجود → سجّله تلقائياً
        display_name = data.get("name", "مجهول")
        sheet.append_row([
            f"🆕 {display_name}",
            firebase_phone or "",
            "",       # تلجرام ID
            False, False, False, False, False,
            False, False, False, False,
            firebase_email or "",  # M: البريد
            firebase_uid,          # N: Firebase UID
            fcm_token or ""        # O: FCM Token
        ], value_input_option="USER_ENTERED")

        # إشعار للمالكين
        _notify_owners(
            title="🔔 طلب انضمام جديد",
            body=f"{display_name} | {firebase_email or firebase_phone}",
            data={"type": "join_request", "uid": firebase_uid},
            sheet=sheet, rows=rows
        )

        return jsonify({
            "allowed": False,
            "reason":  "new_user",
            "message": "تم تسجيلك. انتظر موافقة المالك."
        })

    except Exception as e:
        return jsonify({"allowed": False, "reason": f"خطأ: {str(e)}"})

# ══════════════════════════════════════════════════════
# 2. جلب بيانات الشيت
# ══════════════════════════════════════════════════════
@app.route("/get_data", methods=["POST"])
def get_data():
    data     = request.json or {}
    id_token = data.get("idToken", "")

    if not verify_token(id_token):
        return jsonify({"error": "غير مصرح"})

    try:
        ss     = get_sheet()
        sheet  = ss.sheet1
        rows   = sheet.get_all_values()
        result = []

        for row in rows[1:]:
            if not any(r.strip() for r in row):
                continue
            result.append({
                "date":    row[0] if len(row) > 0 else "",
                "subject": row[1] if len(row) > 1 else "",
                "time":    row[2] if len(row) > 2 else "",
                "room":    row[3] if len(row) > 3 else "",
                "task":    row[4] if len(row) > 4 else "",
                "price":   row[5] if len(row) > 5 else "",
                "summary": row[6] if len(row) > 6 else "",
                "alert":   row[7] if len(row) > 7 else "",
            })

        return jsonify({"data": result})

    except Exception as e:
        return jsonify({"error": str(e)})

# ══════════════════════════════════════════════════════
# 3. الذكاء الاصطناعي
# ══════════════════════════════════════════════════════
@app.route("/ask_ai", methods=["POST"])
def ask_ai():
    data     = request.json or {}
    id_token = data.get("idToken", "")
    question = data.get("question", "")
    history  = data.get("history", [])

    if not verify_token(id_token):
        return jsonify({"error": "غير مصرح"})

    # جلب بيانات الشيت كسياق للـ AI
    context = ""
    try:
        ss    = get_sheet()
        sheet = ss.sheet1
        rows  = sheet.get_all_values()
        lines = []
        for row in rows[1:]:
            if any(r.strip() for r in row):
                lines.append(" | ".join(r for r in row if r.strip()))
        context = "بيانات المدرسة:\n" + "\n".join(lines[:50])
    except:
        pass

    system_prompt = (
        "أنت مساعد ذكي لنظام تعليمي اسمك 'مساعد نايف'. "
        "أجب باللغة العربية دائماً. إجاباتك مختصرة وواضحة.\n\n"
        f"{context}"
    )

    # جرب Gemini أولاً
    if GEMINI_KEY:
        try:
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"gemini-2.0-flash:generateContent?key={GEMINI_KEY}")
            msgs = [{"role": "user", "parts": [{"text": system_prompt}]}]
            for h in history:
                msgs.append({
                    "role": "user" if h["role"] == "user" else "model",
                    "parts": [{"text": h["content"]}]
                })
            msgs.append({"role": "user", "parts": [{"text": question}]})
            payload = {
                "contents": msgs,
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
            }
            resp = _requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                text = (resp.json()["candidates"][0]
                        ["content"]["parts"][0]["text"])
                return jsonify({"response": text, "model": "Gemini"})
        except:
            pass

    # جرب OpenRouter
    if OPENROUTER_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            }
            msgs = [{"role": "system", "content": system_prompt}]
            msgs += history
            msgs += [{"role": "user", "content": question}]
            payload = {
                "model": "openai/gpt-3.5-turbo",
                "messages": msgs,
                "max_tokens": 1024
            }
            resp = _requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"]
                return jsonify({"response": text, "model": "OpenRouter"})
        except:
            pass

    return jsonify({"error": "فشل الذكاء الاصطناعي"})

# ══════════════════════════════════════════════════════
# 4. الموافقة على طلب انضمام (من التطبيق - المالك فقط)
# ══════════════════════════════════════════════════════
@app.route("/approve_user", methods=["POST"])
def approve_user():
    data         = request.json or {}
    id_token     = data.get("idToken", "")
    target_uid   = data.get("targetUid", "")
    action       = data.get("action", "")  # approve / reject

    decoded = verify_token(id_token)
    if not decoded:
        return jsonify({"error": "غير مصرح"})

    try:
        ss    = get_sheet()
        sheet = ss.worksheet("المستخدمين")
        rows  = sheet.get_all_values()

        for i, row in enumerate(rows[1:], start=2):
            row_uid = row[13].strip() if len(row) > 13 else ""
            if row_uid != target_uid:
                continue

            if action == "approve":
                sheet.update_cell(i, 4, True)  # allowed = TRUE
                # أرسل إشعار للمستخدم
                fcm = row[14].strip() if len(row) > 14 else ""
                if fcm and _firebase_ready:
                    messaging.send(messaging.Message(
                        token=fcm,
                        notification=messaging.Notification(
                            title="✅ تمت الموافقة",
                            body="تمت الموافقة على طلبك! افتح التطبيق."
                        )
                    ))
            elif action == "reject":
                fcm = row[14].strip() if len(row) > 14 else ""
                if fcm and _firebase_ready:
                    messaging.send(messaging.Message(
                        token=fcm,
                        notification=messaging.Notification(
                            title="❌ تم الرفض",
                            body="تم رفض طلبك."
                        )
                    ))

            return jsonify({"success": True})

        return jsonify({"error": "المستخدم غير موجود"})

    except Exception as e:
        return jsonify({"error": str(e)})

# ══════════════════════════════════════════════════════
# 5. الإبلاغ عن تعديل التطبيق
# ══════════════════════════════════════════════════════
@app.route("/report_tamper", methods=["POST"])
def report_tamper():
    data  = request.json or {}
    name  = data.get("name", "مجهول")
    email = data.get("email", "")
    hash_ = data.get("hash", "")

    try:
        ss = get_sheet()

        # احفظ في شيت security_log
        try:
            log = ss.worksheet("security_log")
        except:
            log = ss.add_worksheet("security_log", 100, 5)
            log.append_row(["التاريخ","الاسم","البريد","Hash","الحدث"])

        now = datetime.now(YEMEN_TZ).strftime("%Y-%m-%d %H:%M")
        log.append_row([now, name, email, hash_, "تعديل APK"])

        # إشعار للمالكين
        sheet = ss.worksheet("المستخدمين")
        rows  = sheet.get_all_values()
        _notify_owners(
            title="🚨 تحذير أمان!",
            body=f"تعديل في التطبيق من: {name}",
            data={"type": "tamper", "email": email},
            sheet=sheet, rows=rows
        )
    except:
        pass

    return jsonify({"received": True})

# ══════════════════════════════════════════════════════
# 6. جلب طلبات الانضمام (للمالك)
# ══════════════════════════════════════════════════════
@app.route("/get_requests", methods=["POST"])
def get_requests():
    data     = request.json or {}
    id_token = data.get("idToken", "")

    decoded = verify_token(id_token)
    if not decoded:
        return jsonify({"error": "غير مصرح"})

    try:
        ss    = get_sheet()
        sheet = ss.worksheet("المستخدمين")
        rows  = sheet.get_all_values()
        reqs  = []

        for row in rows[1:]:
            if not any(r.strip() for r in row):
                continue
            allowed = str(row[3]).upper() == "TRUE" if len(row) > 3 else False
            uid_str = row[13].strip() if len(row) > 13 else ""
            name    = row[0].strip()

            # الطلبات = مسجلون لكن غير مسموح لهم
            if not allowed and uid_str and name.startswith("🆕"):
                reqs.append({
                    "name":  name.replace("🆕 ", "").strip(),
                    "email": row[12].strip() if len(row) > 12 else "",
                    "phone": row[1].strip()  if len(row) > 1  else "",
                    "uid":   uid_str
                })

        return jsonify({"requests": reqs})

    except Exception as e:
        return jsonify({"error": str(e)})

# ══════════════════════════════════════════════════════
# Helper — إرسال إشعار FCM للمالكين
# ══════════════════════════════════════════════════════
def _notify_owners(title, body, data, sheet, rows):
    if not _firebase_ready:
        return
    for row in rows[1:]:
        is_owner  = str(row[5]).upper() == "TRUE" if len(row) > 5  else False
        fcm_token = row[14].strip()               if len(row) > 14 else ""
        if is_owner and fcm_token:
            try:
                messaging.send(messaging.Message(
                    token=fcm_token,
                    notification=messaging.Notification(title=title, body=body),
                    data=data
                ))
            except:
                pass

# ── Keep-alive ────────────────────────────────────────
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "service": "SmartStudent Server"})