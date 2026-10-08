# -*- coding: utf-8 -*-
import io
import os
import re
import json
import random
import shutil
import sqlite3
from datetime import datetime
import pandas as pd
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from database import init_db, get_connection

app = FastAPI(title="Respublika Olimpiada Platformasi")

init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def get_db():
    conn = get_connection()
    return conn

OY_NOM_RAQAM = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4,
    "may": 5, "iyun": 6, "iyul": 7, "avgust": 8,
    "sentyabr": 9, "oktyabr": 10, "noyabr": 11, "dekabr": 12
}
OY_RAQAM_NOM = {
    1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
    5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
    9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr"
}

def tozalash_telefon(tel):
    raqamlar = re.sub(r"\D", "", str(tel))
    if len(raqamlar) >= 9:
        return raqamlar[-9:]
    return raqamlar

# --- Pydantic Modellar ---
class OquvchiRoyxat(BaseModel):
    fio: str
    telefon: str
    viloyat: str
    tuman: str
    maktab: str
    sinf: int
    email: Optional[str] = None
    telegram_id: Optional[str] = None
    parol: str

class LoginUniversal(BaseModel):
    telefon: Optional[str] = None
    login: Optional[str] = None
    username: Optional[str] = None
    parol: Optional[str] = None
    password: Optional[str] = None

class YangiOqituvchi(BaseModel):
    fio: str
    login: str
    parol: str
    fan: str
    telefon: Optional[str] = ""

class ParolOzgartirish(BaseModel):
    id: int
    turi: str
    yangi_parol: str

class OquvchiTahrirlash(BaseModel):
    id: int
    fio: str
    telefon: str
    sinf: int
    maktab: str
    viloyat: Optional[str] = "Buxoro"

class YangiImtihon(BaseModel):
    nomi: str
    fan: str
    sinf: str
    boshlanish_vaqti: str
    manzil: str

class YangiOnlineTest(BaseModel):
    nomi: str
    fan: str
    sinf: int
    turi: str  # kunlik, haftalik, oylik
    davomiyligi_daqiqa: int = 30
    narxi: int = 0
    boshlanish_vaqti: Optional[str] = None
    tugash_vaqti: Optional[str] = None
    yaratuvchi_id: Optional[int] = 1

class BittalikSavol(BaseModel):
    test_id: int
    savol_matni: str
    rasm_url: Optional[str] = ""
    variant_a: str
    variant_b: str
    variant_c: str
    variant_d: str
    togri_javob: str  # A, B, C yoki D

class TestTopshirish(BaseModel):
    urinish_id: int
    javoblar: Dict[str, str]  # {"savol_id": "tanlangan_javob"}

# --- Sahifalar Yo'nalishi ---
@app.get("/")
async def root():
    return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))

@app.get("/royxat")
async def royxat_page():
    return FileResponse(os.path.join(TEMPLATES_DIR, "royxat.html"))

@app.get("/login")
async def login_page():
    return FileResponse(os.path.join(TEMPLATES_DIR, "login.html"))

@app.get("/kabinet")
async def kabinet_page():
    return FileResponse(os.path.join(TEMPLATES_DIR, "kabinet.html"))

@app.get("/reyting")
async def reyting_page():
    return FileResponse(os.path.join(TEMPLATES_DIR, "reyting.html"))

@app.get("/oqituvchi-login")
async def oqituvchi_login_page():
    return FileResponse(os.path.join(TEMPLATES_DIR, "oqituvchi_login.html"))

@app.get("/oqituvchi")
async def oqituvchi_panel_page():
    return FileResponse(os.path.join(TEMPLATES_DIR, "oqituvchi.html"))

@app.get("/admin-login")
async def admin_login_page():
    return FileResponse(os.path.join(TEMPLATES_DIR, "admin_login.html"))

@app.get("/admin")
async def admin_page():
    return FileResponse(os.path.join(TEMPLATES_DIR, "admin.html"))

@app.get("/test/{test_id}")
async def online_test_page(test_id: int):
    return FileResponse(os.path.join(TEMPLATES_DIR, "test_ishlash.html"))

@app.get("/aloqa")
async def aloqa_page():
    return FileResponse(os.path.join(TEMPLATES_DIR, "aloqa.html"))

# ==========================================
# 1. O'QUVCHI ROYXAT VA LOGIN
# ==========================================
@app.post("/api/register")
async def register_student(data: OquvchiRoyxat):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO oquvchilar (fio, telefon, viloyat, tuman, maktab, sinf, email, telegram_id, parol)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.fio.strip(),
                data.telefon.strip(),
                data.viloyat.strip(),
                data.tuman.strip(),
                data.maktab.strip(),
                data.sinf,
                (data.email or "").strip(),
                (data.telegram_id or "").strip().replace("@", ""),
                data.parol.strip()
            )
        )
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "oquvchi_id": cursor.lastrowid}
    except Exception as e:
        if "UNIQUE" in str(e).upper() or "oquvchilar_telefon_key" in str(e).lower():
            return JSONResponse(status_code=400, content={"xatolik": "Ushbu telefon raqami allaqachon mavjud!"})
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        conn.close()

@app.post("/api/login")
async def login_student(data: LoginUniversal):
    conn = get_db()
    cursor = conn.cursor()
    try:
        kirgan_login = (data.telefon or data.login or data.username or "").strip()
        kirgan_parol = (data.parol or data.password or "").strip()
        kirgan_tel = tozalash_telefon(kirgan_login)

        cursor.execute("SELECT id, fio, sinf, viloyat, maktab, telefon, parol FROM oquvchilar")
        barcha = cursor.fetchall()
        for u in barcha:
            baza_tel = tozalash_telefon(u[5])
            baza_parol = str(u[6]).strip()
            if baza_tel == kirgan_tel and baza_parol == kirgan_parol:
                return {
                    "holat": "Muvaffaqiyatli",
                    "oquvchi": {"id": u[0], "fio": u[1], "sinf": u[2], "viloyat": u[3], "maktab": u[4]}
                }
        return JSONResponse(status_code=401, content={"xatolik": "Telefon yoki parol noto‘g‘ri!"})
    finally:
        conn.close()

@app.get("/api/oquvchi_natijalari/{oquvchi_id}")
async def get_student_results(oquvchi_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT fio, viloyat, maktab, sinf FROM oquvchilar WHERE id = ?", (oquvchi_id,))
        user = cursor.fetchone()
        if not user:
            return JSONResponse(status_code=404, content={"xatolik": "O‘quvchi topilmadi"})

        cursor.execute("""
            SELECT bosqich_turi, hafta_raqami, oy_raqami, oy_nomi, ball, jami_savol, orin, sana, fan, id
            FROM natijalar
            WHERE oquvchi_id = ?
            ORDER BY id DESC
        """, (oquvchi_id,))
        rows = cursor.fetchall()

        tarix = []
        for r in rows:
            tarix.append({
                "id": r[9],
                "bosqich_turi": str(r[0]).strip().lower() if r[0] else "haftalik",
                "hafta_raqami": int(r[1]) if r[1] is not None else 1,
                "oy_raqami": int(r[2]) if r[2] is not None else 10,
                "oy_nomi": str(r[3]).strip() if r[3] else "Oktyabr",
                "ball": int(r[4]) if r[4] is not None else 0,
                "jami_savol": int(r[5]) if r[5] is not None else 100,
                "orin": int(r[6]) if r[6] is not None else 1,
                "sana": str(r[7]) if r[7] else "",
                "fan": str(r[8]).strip() if r[8] else "Informatika"
            })

        return {
            "oquvchi": {"fio": user[0], "viloyat": user[1], "maktab": user[2], "sinf": user[3]},
            "tarix": tarix
        }
    finally:
        conn.close()

# ==========================================
# 2. ONLAYN TEST TIZIMI (GENERATSIYA VA YECHISH)
# ==========================================
@app.post("/api/admin/online_test_yaratish")
async def create_online_test(data: YangiOnlineTest):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO testlar (nomi, fan, sinf, turi, davomiyligi_daqiqa, narxi, boshlanish_vaqti, tugash_vaqti, yaratuvchi_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.nomi.strip(), data.fan.strip(), data.sinf, data.turi.strip(), data.davomiyligi_daqiqa, data.narxi, data.boshlanish_vaqti, data.tugash_vaqti, data.yaratuvchi_id))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": "Yangi test bazasi yaratildi!", "test_id": cursor.lastrowid}
    finally:
        conn.close()

@app.get("/api/testlar/royxat")
async def get_test_list(sinf: Optional[int] = None, fan: Optional[str] = None, oquvchi_id: Optional[int] = None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        sql = "SELECT id, nomi, fan, sinf, turi, davomiyligi_daqiqa, narxi, boshlanish_vaqti, tugash_vaqti, javoblar_ochiq FROM testlar WHERE faol = 1"
        params = []
        if sinf:
            sql += " AND (sinf = ? OR sinf = 0)"
            params.append(sinf)
        if fan:
            sql += " AND fan = ?"
            params.append(fan)
        sql += " ORDER BY id DESC"
        cursor.execute(sql, tuple(params))
        tests = cursor.fetchall()

        natija = []
        hozir = datetime.now()

        for t in tests:
            test_id, nomi, t_fan, t_sinf, turi, daqiqa, narxi, bosh_v, tug_v, j_ochiq = t
            holat = "faol"

            # Muddatni tekshirish
            if bosh_v:
                bosh_dt = datetime.fromisoformat(str(bosh_v))
                if hozir < bosh_dt:
                    holat = "kutilmoqda"
            if tug_v:
                tug_dt = datetime.fromisoformat(str(tug_v))
                if hozir > tug_dt:
                    holat = "otkazildi"

            # O'quvchi ishlaganmi yoki to'lov qilganmi tekshirish
            ishlangan = False
            toplagan_ball = None
            tolangan = False if narxi > 0 else True

            if oquvchi_id:
                cursor.execute("SELECT holat, ball FROM test_urinishlari WHERE test_id = ? AND oquvchi_id = ?", (test_id, oquvchi_id))
                u = cursor.fetchone()
                if u:
                    ishlangan = True
                    toplagan_ball = u[1]

                if narxi > 0:
                    cursor.execute("SELECT holat FROM tolovlar WHERE test_id = ? AND oquvchi_id = ? AND holat = 'tasdiqlandi'", (test_id, oquvchi_id))
                    if cursor.fetchone():
                        tolangan = True

            natija.append({
                "id": test_id,
                "nomi": nomi,
                "fan": t_fan,
                "sinf": t_sinf,
                "turi": turi,
                "davomiyligi_daqiqa": daqiqa,
                "narxi": narxi,
                "holat": holat,
                "ishlangan": ishlangan,
                "toplagan_ball": toplagan_ball,
                "tolangan": tolangan,
                "javoblar_ochiq": bool(j_ochiq)
            })

        return {"holat": "Muvaffaqiyatli", "testlar": natija}
    finally:
        conn.close()

# 25 talik testni generatsiya qilib boshlash
@app.get("/api/test/boshlash/{test_id}")
async def start_test(test_id: int, oquvchi_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        # 1. Avval boshlangan sessiya bormi (F5 himoyasi)?
        cursor.execute("SELECT id, tanlangan_savollar, holat FROM test_urinishlari WHERE test_id = ? AND oquvchi_id = ?", (test_id, oquvchi_id))
        eski_urinish = cursor.fetchone()

        if eski_urinish:
            if eski_urinish[2] == "yakunlangan":
                return JSONResponse(status_code=400, content={"xatolik": "Siz ushbu testni allaqachon topshirgansiz!"})
            urinish_id = eski_urinish[0]
            savollar_paketi = json.loads(eski_urinish[1])
            return {"urinish_id": urinish_id, "savollar": savollar_paketi}

        # 2. Savollar bankidan 25 tasini random tanlash
        cursor.execute("SELECT id, savol_matni, rasm_url, variant_a, variant_b, variant_c, variant_d, togri_javob FROM savollar WHERE test_id = ?", (test_id,))
        bank = cursor.fetchall()

        if len(bank) == 0:
            return JSONResponse(status_code=400, content={"xatolik": "Ushbu testga hali savollar yuklanmagan!"})

        tanlanganlar = random.sample(bank, min(len(bank), 25))
        savollar_paketi = []

        for row in tanlanganlar:
            s_id, matn, rasm, va, vb, vc, vd, togri = row
            variantlar = [
                {"kalit": "A", "matn": va},
                {"kalit": "B", "matn": vb},
                {"kalit": "C", "matn": vc},
                {"kalit": "D", "matn": vd}
            ]
            random.shuffle(variantlar)

            savollar_paketi.append({
                "savol_id": s_id,
                "savol_matni": matn,
                "rasm_url": rasm,
                "variantlar": variantlar
            })

        cursor.execute("""
            INSERT INTO test_urinishlari (oquvchi_id, test_id, tanlangan_savollar, holat)
            VALUES (?, ?, ?, 'boshlangan')
        """, (oquvchi_id, test_id, json.dumps(savollar_paketi)))
        conn.commit()
        yangi_urinish_id = cursor.lastrowid

        return {"urinish_id": yangi_urinish_id, "savollar": savollar_paketi}
    finally:
        conn.close()

# Testni topshirish va natijani hisoblash
@app.post("/api/test/topshirish")
async def submit_test(data: TestTopshirish):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT oquvchi_id, test_id, tanlangan_savollar, boshlangan_vaqt, holat FROM test_urinishlari WHERE id = ?", (data.urinish_id,))
        urinish = cursor.fetchone()

        if not urinish:
            return JSONResponse(status_code=404, content={"xatolik": "Urinish topilmadi!"})
        if urinish[4] == "yakunlangan":
            return JSONResponse(status_code=400, content={"xatolik": "Test allaqachon topshirilgan!"})

        oquvchi_id, test_id, paketi_str, bosh_v, _ = urinish
        paketi = json.loads(paketi_str)
        savol_ids = [s["savol_id"] for s in paketi]

        # Barcha to'g'ri javoblarni bazadan olish
        placeholders = ",".join("?" for _ in savol_ids)
        cursor.execute(f"SELECT id, togri_javob FROM savollar WHERE id IN ({placeholders})", tuple(savol_ids))
        togri_javoblar = dict(cursor.fetchall())

        ball = 0
        for s in paketi:
            sid = str(s["savol_id"])
            belgilangan = data.javoblar.get(sid)
            haqiqiy_togri = togri_javoblar.get(int(sid))
            if belgilangan and haqiqiy_togri and belgilangan.strip().upper() == haqiqiy_togri.strip().upper():
                ball += 4  # 25 ta savol * 4 ball = 100 ball

        # Sarflangan soniyani hisoblash
        hozir = datetime.now()
        bosh_dt = datetime.fromisoformat(str(bosh_v)) if "T" in str(bosh_v) else datetime.strptime(str(bosh_v), "%Y-%m-%d %H:%M:%S")
        sarflangan = int((hozir - bosh_dt).total_seconds())

        cursor.execute("""
            UPDATE test_urinishlari
            SET berilgan_javoblar = ?, ball = ?, sarflangan_soniya = ?, holat = 'yakunlangan', tugatilgan_vaqt = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (json.dumps(data.javoblar), ball, sarflangan, data.urinish_id))

        # Umumiy natijalar jadvaliga ham qo'shib qo'yish
        cursor.execute("SELECT fan, turi FROM testlar WHERE id = ?", (test_id,))
        t_info = cursor.fetchone()
        fan_n = t_info[0] if t_info else "Informatika"
        b_tur = t_info[1] if t_info else "kunlik"

        cursor.execute("""
            INSERT INTO natijalar (oquvchi_id, tadbir_id, fan, bosqich_turi, ball, jami_savol, sarflangan_soniya)
            VALUES (?, ?, ?, ?, ?, 100, ?)
        """, (oquvchi_id, test_id, fan_n, b_tur, ball, sarflangan))

        conn.commit()
        return {"holat": "Muvaffaqiyatli", "ball": ball, "sarflangan_soniya": sarflangan}
    finally:
        conn.close()

# To'g'ri javoblarni o'qituvchi tomonidan ochish/yopish
@app.put("/api/test/javoblarni_ochish/{test_id}")
async def toggle_answers(test_id: int, ochish: bool = True):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE testlar SET javoblar_ochiq = ? WHERE id = ?", (1 if ochish else 0, test_id))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": "To‘g‘ri javoblar o‘quvchilar uchun ochildi!" if ochish else "Javoblar yopildi!"}
    finally:
        conn.close()

# O'quvchi uchun test tahlili (faqat o'qituvchi ochganda)
@app.get("/api/test/tahlil/{urinish_id}")
async def get_test_analysis(urinish_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT u.tanlangan_savollar, u.berilgan_javoblar, u.ball, t.javoblar_ochiq, t.nomi
            FROM test_urinishlari u
            JOIN testlar t ON u.test_id = t.id
            WHERE u.id = ?
        """, (urinish_id,))
        row = cursor.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"xatolik": "Natija topilmadi!"})

        if not row[3]:
            return JSONResponse(status_code=403, content={"xatolik": "Ustoz hali to‘g‘ri javoblarni ko‘rishga ruxsat bermadi!"})

        paketi = json.loads(row[0])
        javoblar = json.loads(row[1])
        s_ids = [s["savol_id"] for s in paketi]
        placeholders = ",".join("?" for _ in s_ids)
        cursor.execute(f"SELECT id, togri_javob FROM savollar WHERE id IN ({placeholders})", tuple(s_ids))
        togri_dict = dict(cursor.fetchall())

        tahlil = []
        for s in paketi:
            sid = s["savol_id"]
            tahlil.append({
                "savol_matni": s["savol_matni"],
                "variantlar": s["variantlar"],
                "tanlagan_javobi": javoblar.get(str(sid), "Belgilanmagan"),
                "haqiqiy_togri_javob": togri_dict.get(sid)
            })

        return {"holat": "Muvaffaqiyatli", "test_nomi": row[4], "ball": row[2], "tahlil": tahlil}
    finally:
        conn.close()

# ==========================================
# 3. O'QITUVCHI UCHUN SAVOLLARNI YUKLASH (3 XIL USUL)
# ==========================================
# 1-usul: Bittalab qo'lda qo'shish
@app.post("/api/test/savol_qoshish")
async def add_single_question(data: BittalikSavol):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO savollar (test_id, savol_matni, rasm_url, variant_a, variant_b, variant_c, variant_d, togri_javob)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.test_id, data.savol_matni.strip(), data.rasm_url, data.variant_a.strip(), data.variant_b.strip(), data.variant_c.strip(), data.variant_d.strip(), data.togri_javob.strip().upper()))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": "Savol qo‘shildi!"}
    finally:
        conn.close()

# 2-usul: Matndan nusxa olib qo'yish (Parser)
@app.post("/api/test/savollar_matn_yuklash")
async def upload_text_questions(test_id: int = Form(...), matn: str = Form(...)):
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Regex orqali savol, variantlar va to'g'ri javobni ajratish
        pattern = re.compile(
            r"(?:(\d+)[\.\)]\s*)?(.*?)\n[AАaа][\.\)]\s*(.*?)\n[BВbв][\.\)]\s*(.*?)\n[CСcс][\.\)]\s*(.*?)\n[DДdд][\.\)]\s*(.*?)\n(?:Javob|J|To'g'ri javob|Ответ):\s*([A-Da-dА-Яа-я])",
            re.DOTALL | re.IGNORECASE
        )

        matches = pattern.findall(matn.strip() + "\n")
        qoshildi = 0

        for m in matches:
            _, s_matn, va, vb, vc, vd, togri = m
            togri_harf = togri.strip().upper()
            if togri_harf in ['А']: togri_harf = 'A'
            if togri_harf in ['В']: togri_harf = 'B'
            if togri_harf in ['С']: togri_harf = 'C'

            cursor.execute("""
                INSERT INTO savollar (test_id, savol_matni, variant_a, variant_b, variant_c, variant_d, togri_javob)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (test_id, s_matn.strip(), va.strip(), vb.strip(), vc.strip(), vd.strip(), togri_harf))
            qoshildi += 1

        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": f"✅ {qoshildi} ta savol muvaffaqiyatli ajratib olindi va bazaga saqlandi!"}
    finally:
        conn.close()

# 3-usul: Excel fayldan ommaviy yuklash
@app.post("/api/test/savollar_excel_yuklash")
async def upload_excel_questions(test_id: int = Form(...), fayl: UploadFile = File(...)):
    conn = get_db()
    cursor = conn.cursor()
    try:
        contents = await fayl.read()
        df = pd.read_excel(io.BytesIO(contents))
        df.columns = [str(c).strip().lower() for c in df.columns]

        kerakli = ["savol", "a", "b", "c", "d", "javob"]
        for k in kerakli:
            if k not in df.columns:
                return JSONResponse(status_code=400, content={"xatolik": f"Excel jadvalida '{k}' ustuni topilmadi!"})

        qoshildi = 0
        for _, row in df.iterrows():
            if pd.isna(row["savol"]): continue
            cursor.execute("""
                INSERT INTO savollar (test_id, savol_matni, variant_a, variant_b, variant_c, variant_d, togri_javob)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (test_id, str(row["savol"]).strip(), str(row["a"]).strip(), str(row["b"]).strip(), str(row["c"]).strip(), str(row["d"]).strip(), str(row["javob"]).strip().upper()))
            qoshildi += 1

        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": f"✅ Exceldan {qoshildi} ta savol bazaga yuklandi!"}
    finally:
        conn.close()

# ==========================================
# 4. TO'LOV VA CHEK YUKLASH (OYLIK OLIMPIADA)
# ==========================================
@app.post("/api/tolov/chek_yuklash")
async def upload_payment_receipt(
    oquvchi_id: int = Form(...),
    test_id: int = Form(...),
    summa: int = Form(10000),
    chek: UploadFile = File(...)
):
    conn = get_db()
    cursor = conn.cursor()
    try:
        fayl_kengaytma = chek.filename.split(".")[-1]
        yangi_nom = f"chek_{oquvchi_id}_{test_id}_{int(datetime.now().timestamp())}.{fayl_kengaytma}"
        fayl_manzili = os.path.join(UPLOADS_DIR, yangi_nom)

        with open(fayl_manzili, "wb") as buffer:
            shutil.copyfileobj(chek.file, buffer)

        db_url = f"/static/uploads/{yangi_nom}"
        cursor.execute("""
            INSERT INTO tolovlar (oquvchi_id, test_id, chek_rasm, summa, holat)
            VALUES (?, ?, ?, ?, 'kutilmoqda')
        """, (oquvchi_id, test_id, db_url, summa))
        conn.commit()

        return {"holat": "Muvaffaqiyatli", "xabar": "To‘lov chekingiz qabul qilindi. Tez orada admin tomonidan tasdiqlanadi!"}
    finally:
        conn.close()

@app.get("/api/admin/kutilayotgan_tolovlar")
async def get_pending_payments():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT t.id, o.fio, o.telefon, te.nomi, t.summa, t.chek_rasm, t.yuklangan_vaqt
            FROM tolovlar t
            JOIN oquvchilar o ON t.oquvchi_id = o.id
            JOIN testlar te ON t.test_id = te.id
            WHERE t.holat = 'kutilmoqda'
            ORDER BY t.id DESC
        """)
        rows = cursor.fetchall()
        return [{
            "id": r[0], "fio": r[1], "telefon": r[2], "test_nomi": r[3],
            "summa": r[4], "chek_rasm": r[5], "vaqt": str(r[6])
        } for r in rows]
    finally:
        conn.close()

@app.put("/api/admin/tolov_tasdiqlash/{tolov_id}")
async def approve_payment(tolov_id: int, holat: str = "tasdiqlandi"):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE tolovlar SET holat = ? WHERE id = ?", (holat, tolov_id))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": f"To‘lov holati '{holat}' ga o‘zgartirildi!"}
    finally:
        conn.close()

# ==========================================
# 5. SUPER ADMIN VA NATIJALAR BO'LIMI
# ==========================================
@app.post("/api/admin/login")
async def admin_login(data: LoginUniversal):
    kirgan_login = (data.login or data.username or "").strip()
    kirgan_parol = (data.parol or data.password or "").strip()

    if kirgan_login == "admin" and kirgan_parol == "admin2026":
        return {"holat": "Muvaffaqiyatli", "token": "super_admin_2026"}
    return JSONResponse(status_code=401, content={"xatolik": "Super Admin login yoki paroli xato!"})

@app.post("/api/admin/oqituvchi_qoshish")
async def admin_add_teacher(data: YangiOqituvchi):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO oqituvchilar (fio, login, parol, fan, telefon)
            VALUES (?, ?, ?, ?, ?)
        """, (data.fio.strip(), data.login.strip(), data.parol.strip(), data.fan.strip(), data.telefon.strip()))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘qituvchi muvaffaqiyatli biriktirildi!"}
    except Exception as e:
        return JSONResponse(status_code=400, content={"xatolik": "Bu login bilan o‘qituvchi mavjud yoki boshqa xatolik!"})
    finally:
        conn.close()

@app.get("/api/admin/oqituvchilar")
async def list_teachers():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, fio, login, parol, fan, telefon FROM oqituvchilar ORDER BY id DESC")
        rows = cursor.fetchall()
        return [{"id": r[0], "fio": r[1], "login": r[2], "parol": r[3], "fan": r[4], "telefon": r[5]} for r in rows]
    finally:
        conn.close()

@app.delete("/api/admin/oqituvchi_ochirish/{tid}")
async def delete_teacher(tid: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM oqituvchilar WHERE id = ?", (tid,))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘qituvchi tizimdan o‘chirildi!"}
    finally:
        conn.close()

@app.post("/api/admin/parol_yangilash")
async def admin_parol_yangilash(data: ParolOzgartirish):
    conn = get_db()
    cursor = conn.cursor()
    try:
        if len(data.yangi_parol.strip()) < 4:
            return JSONResponse(status_code=400, content={"xatolik": "Parol kamida 4 ta belgidan iborat bo‘lsin!"})

        if data.turi == 'oqituvchi':
            cursor.execute("UPDATE oqituvchilar SET parol = ? WHERE id = ?", (data.yangi_parol.strip(), data.id))
        else:
            cursor.execute("UPDATE oquvchilar SET parol = ? WHERE id = ?", (data.yangi_parol.strip(), data.id))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": "Yangi parol o‘rnatildi!"}
    finally:
        conn.close()

@app.put("/api/admin/oquvchi_tahrirlash")
async def admin_edit_student(data: OquvchiTahrirlash):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE oquvchilar 
            SET fio = ?, telefon = ?, sinf = ?, maktab = ?, viloyat = ?
            WHERE id = ?
        """, (data.fio.strip(), data.telefon.strip(), data.sinf, data.maktab.strip(), data.viloyat.strip(), data.id))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘quvchi ma'lumotlari yangilandi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        conn.close()

@app.delete("/api/admin/oquvchi_ochirish/{oid}")
async def delete_student(oid: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM natijalar WHERE oquvchi_id = ?", (oid,))
        cursor.execute("DELETE FROM oquvchilar WHERE id = ?", (oid,))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘quvchi butunlay o‘chirildi!"}
    finally:
        conn.close()

@app.get("/api/admin/oquvchilar")
async def list_students():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, fio, telefon, maktab, sinf, parol, viloyat FROM oquvchilar ORDER BY sinf ASC, fio ASC")
        rows = cursor.fetchall()
        return [{"id": r[0], "fio": r[1], "telefon": r[2], "maktab": r[3], "sinf": r[4], "parol": r[5], "viloyat": r[6] if len(r)>6 else "Buxoro"} for r in rows]
    finally:
        conn.close()

# Leaderboard (Peshqadamlar)
@app.get("/api/reyting")
async def get_leaderboard(
    fan: Optional[str] = "Informatika",
    bosqich_turi: Optional[str] = "haftalik",
    oy_nomi: Optional[str] = "Oktyabr",
    hafta_raqami: Optional[int] = 1,
    sinf: Optional[str] = "barchasi"
):
    conn = get_db()
    cursor = conn.cursor()
    try:
        b_tur = "oylik" if "oylik" in str(bosqich_turi).lower() else "haftalik"
        oy_nomi_toza = str(oy_nomi).strip().capitalize() if oy_nomi else "Oktyabr"
        fan_toza = str(fan).strip().capitalize() if fan else "Informatika"

        sql = """
            SELECT o.id, o.fio, o.sinf, o.maktab, o.viloyat, n.ball, n.jami_savol, n.sarflangan_soniya
            FROM natijalar n
            JOIN oquvchilar o ON n.oquvchi_id = o.id
            WHERE n.fan = ? AND n.bosqich_turi = ? AND n.oy_nomi = ?
        """
        params = [fan_toza, b_tur, oy_nomi_toza]

        if b_tur == "haftalik":
            sql += " AND n.hafta_raqami = ?"
            params.append(int(hafta_raqami or 1))

        if sinf and sinf != "barchasi" and sinf.isdigit():
            sql += " AND CAST(o.sinf AS INTEGER) = ?"
            params.append(int(sinf))

        # Ball bo'yicha kamayish, teng bo'lsa sarflangan soniya bo'yicha o'sish tartibida saralash
        sql += " ORDER BY n.ball DESC, n.sarflangan_soniya ASC, o.fio ASC"

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()

        natijalar = []
        for index, r in enumerate(rows, start=1):
            natijalar.append({
                "orin": index,
                "oquvchi_id": r[0],
                "fio": r[1],
                "sinf": r[2],
                "maktab": r[3],
                "viloyat": r[4],
                "ball": r[5],
                "jami_savol": r[6],
                "sarflangan_soniya": r[7]
            })

        return {"holat": "Muvaffaqiyatli", "reyting": natijalar}
    finally:
        conn.close()

# O'qituvchi login
@app.post("/api/oqituvchi/login")
async def login_teacher(data: LoginUniversal):
    conn = get_db()
    cursor = conn.cursor()
    try:
        kirgan_login = (data.login or data.username or data.telefon or "").strip()
        kirgan_parol = (data.parol or data.password or "").strip()

        cursor.execute("SELECT id, fio, fan FROM oqituvchilar WHERE login = ? AND parol = ?", (kirgan_login, kirgan_parol))
        t = cursor.fetchone()
        if t:
            return {"holat": "Muvaffaqiyatli", "oqituvchi": {"id": t[0], "fio": t[1], "fan": t[2]}}
        return JSONResponse(status_code=401, content={"xatolik": "O‘qituvchi logini yoki paroli noto‘g‘ri!"})
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
