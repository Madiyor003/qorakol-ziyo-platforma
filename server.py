# -*- coding: utf-8 -*-
import io
import os
import re
import sqlite3
import pandas as pd
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
from database import init_db, DB_NAME

app = FastAPI(title="Respublika Olimpiada Platformasi")

init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=20)
    conn.execute("PRAGMA journal_mode=WAL;")
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

# Modellar
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
    boshlanish_vaqti: str # 'YYYY-MM-DDTHH:MM'
    manzil: str

# Sahifalar
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

# 1. O'quvchi
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
    except sqlite3.IntegrityError:
        return JSONResponse(status_code=400, content={"xatolik": "Ushbu telefon raqami allaqachon mavjud!"})
    except Exception as e:
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
            ORDER BY id ASC
        """, (oquvchi_id,))
        rows = cursor.fetchall()

        tarix = []
        for r in rows:
            b_tur = str(r[0]).strip().lower() if r[0] else "haftalik"
            h_raqam = int(r[1]) if r[1] is not None else 1
            o_raqam = int(r[2]) if r[2] is not None else 10
            o_nom = str(r[3]).strip() if r[3] else OY_RAQAM_NOM.get(o_raqam, "Oktyabr")
            b_ball = int(r[4]) if r[4] is not None else 0
            j_savol = int(r[5]) if r[5] is not None else 100
            o_orin = int(r[6]) if r[6] is not None else 1
            s_sana = str(r[7]) if r[7] else ""
            f_fan = str(r[8]).strip() if r[8] else "Informatika"

            tarix.append({
                "id": r[9],
                "bosqich_turi": b_tur,
                "hafta_raqami": h_raqam,
                "oy_raqami": o_raqam,
                "oy_nomi": o_nom,
                "ball": b_ball,
                "jami_savol": j_savol,
                "orin": o_orin,
                "sana": s_sana,
                "fan": f_fan
            })

        return {
            "oquvchi": {"fio": user[0], "viloyat": user[1], "maktab": user[2], "sinf": user[3]},
            "tarix": tarix
        }
    finally:
        conn.close()

# 2. Leaderboard
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
            SELECT o.id, o.fio, o.sinf, o.maktab, o.viloyat, n.ball, n.jami_savol, n.orin
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

        sql += " ORDER BY n.ball DESC, o.fio ASC"

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
                "jami_savol": r[6]
            })

        return {"holat": "Muvaffaqiyatli", "reyting": natijalar}
    finally:
        conn.close()

# 3. IMTIHON VA TESKARI SANOQ (COUNTDOWN) API
@app.post("/api/admin/imtihon_qoshish")
async def add_exam(data: YangiImtihon):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO imtihonlar (nomi, fan, sinf, boshlanish_vaqti, manzil, faol)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (data.nomi.strip(), data.fan.strip(), data.sinf.strip(), data.boshlanish_vaqti.strip(), data.manzil.strip()))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": "Imtihon muvaffaqiyatli e'lon qilindi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        conn.close()

@app.get("/api/admin/imtihonlar")
async def list_exams():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, nomi, fan, sinf, boshlanish_vaqti, manzil, faol FROM imtihonlar ORDER BY id DESC")
        rows = cursor.fetchall()
        return [{"id": r[0], "nomi": r[1], "fan": r[2], "sinf": r[3], "boshlanish_vaqti": r[4], "manzil": r[5], "faol": r[6]} for r in rows]
    finally:
        conn.close()

@app.delete("/api/admin/imtihon_ochirish/{iid}")
async def delete_exam(iid: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM imtihonlar WHERE id = ?", (iid,))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": "Imtihon tizimdan o‘chirildi!"}
    finally:
        conn.close()

@app.get("/api/eng_yaqin_imtihon")
async def get_latest_exam():
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Faol va eng so'nggi kiritilgan imtihonni olish
        cursor.execute("""
            SELECT id, nomi, fan, sinf, boshlanish_vaqti, manzil 
            FROM imtihonlar 
            WHERE faol = 1 
            ORDER BY id DESC LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            return {
                "mavjud": True,
                "imtihon": {
                    "id": row[0],
                    "nomi": row[1],
                    "fan": row[2],
                    "sinf": row[3],
                    "boshlanish_vaqti": row[4],
                    "manzil": row[5]
                }
            }
        return {"mavjud": False}
    finally:
        conn.close()

# 4. O'qituvchi Amallari
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

# 5. Super Admin
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
    except sqlite3.IntegrityError:
        return JSONResponse(status_code=400, content={"xatolik": "Bu login bilan o‘qituvchi allaqachon mavjud!"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
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

@app.delete("/api/admin/statistika_tozalash/{oid}")
async def clear_student_stats(oid: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM natijalar WHERE oquvchi_id = ?", (oid,))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘quvchi natijalari tozalandi!"}
    finally:
        conn.close()

# 6. Natijalar Kiritish va Shablonlar
@app.post("/api/natija_qoshish")
async def add_result_single(
    telefon: str = Form(...),
    fan: str = Form("Informatika"),
    bosqich_turi: str = Form("haftalik"),
    hafta_raqami: int = Form(1),
    oy_nomi: str = Form("Oktyabr"),
    ball: int = Form(...),
    jami_savol: int = Form(100)
):
    conn = get_db()
    cursor = conn.cursor()
    try:
        tel_toza = tozalash_telefon(telefon)
        cursor.execute("SELECT id, telefon FROM oquvchilar")
        barcha = cursor.fetchall()
        oquvchi_id = None
        for u in barcha:
            if tozalash_telefon(u[1]) == tel_toza:
                oquvchi_id = u[0]
                break

        if not oquvchi_id:
            return JSONResponse(status_code=404, content={"xatolik": "Bunday telefonli o‘quvchi topilmadi!"})

        oy_nomi_toza = oy_nomi.strip().capitalize()
        oy_raqami = OY_NOM_RAQAM.get(oy_nomi_toza.lower(), 10)
        haqiqiy_hafta = int(hafta_raqami) if bosqich_turi == "haftalik" else 1

        if bosqich_turi == "haftalik":
            cursor.execute("""
                SELECT COUNT(*) + 1 FROM natijalar
                WHERE fan = ? AND bosqich_turi = 'haftalik' AND oy_nomi = ? AND hafta_raqami = ? AND ball > ?
            """, (fan, oy_nomi_toza, haqiqiy_hafta, ball))
        else:
            cursor.execute("""
                SELECT COUNT(*) + 1 FROM natijalar
                WHERE fan = ? AND bosqich_turi = 'oylik' AND oy_nomi = ? AND ball > ?
            """, (fan, oy_nomi_toza, ball))
            
        auto_orin = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO natijalar (oquvchi_id, tadbir_id, fan, bosqich_turi, hafta_raqami, oy_raqami, oy_nomi, ball, jami_savol, sarflangan_soniya, orin)
            VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (oquvchi_id, fan, bosqich_turi, haqiqiy_hafta, oy_raqami, oy_nomi_toza, ball, jami_savol, auto_orin))
        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": f"Natija saqlandi! ({auto_orin}-o‘rin)"}
    finally:
        conn.close()

@app.get("/api/admin/shablon/haftalik")
async def download_shablon_haftalik(sinf: Optional[str] = "barchasi", fan: Optional[str] = "Informatika"):
    conn = get_db()
    cursor = conn.cursor()
    try:
        sinf_toza = str(sinf).strip().lower()
        if sinf_toza != "barchasi" and sinf_toza.isdigit():
            cursor.execute("SELECT fio, telefon FROM oquvchilar WHERE CAST(sinf AS INTEGER) = ? ORDER BY fio ASC", (int(sinf_toza),))
            fayl_nomi = f"{sinf_toza}_sinf_haftalik_shablon.xlsx"
        else:
            cursor.execute("SELECT fio, telefon FROM oquvchilar ORDER BY sinf ASC, fio ASC")
            fayl_nomi = "barcha_sinflar_haftalik_shablon.xlsx"

        rows = cursor.fetchall()
        data = {
            "fio": [r[0] for r in rows],
            "telefon": [r[1] for r in rows],
            "ball": ["" for _ in rows]
        }
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Natijalar')
        output.seek(0)
        return StreamingResponse(output, headers={'Content-Disposition': f'attachment; filename="{fayl_nomi}"'}, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    finally:
        conn.close()

@app.get("/api/admin/shablon/oylik")
async def download_shablon_oylik(sinf: Optional[str] = "barchasi", fan: Optional[str] = "Informatika"):
    conn = get_db()
    cursor = conn.cursor()
    try:
        sinf_toza = str(sinf).strip().lower()
        if sinf_toza != "barchasi" and sinf_toza.isdigit():
            cursor.execute("SELECT fio, telefon FROM oquvchilar WHERE CAST(sinf AS INTEGER) = ? ORDER BY fio ASC", (int(sinf_toza),))
            fayl_nomi = f"{sinf_toza}_sinf_oylik_shablon.xlsx"
        else:
            cursor.execute("SELECT fio, telefon FROM oquvchilar ORDER BY sinf ASC, fio ASC")
            fayl_nomi = "barcha_sinflar_oylik_shablon.xlsx"

        rows = cursor.fetchall()
        data = {
            "fio": [r[0] for r in rows],
            "telefon": [r[1] for r in rows],
            "ball": ["" for _ in rows]
        }
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Natijalar')
        output.seek(0)
        return StreamingResponse(output, headers={'Content-Disposition': f'attachment; filename="{fayl_nomi}"'}, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    finally:
        conn.close()

@app.post("/api/admin/excel_yuklash")
async def upload_excel_results(
    fayl: UploadFile = File(...),
    bosqich_turi: str = Form("haftalik"),
    tanlangan_oy: Optional[str] = Form("Oktyabr"),
    tanlangan_hafta: Optional[int] = Form(1),
    tanlangan_fan: Optional[str] = Form("Informatika")
):
    conn = get_db()
    cursor = conn.cursor()
    try:
        contents = await fayl.read()
        df = pd.read_excel(io.BytesIO(contents))
        df.columns = [str(c).strip().lower() for c in df.columns]

        if "telefon" not in df.columns or "ball" not in df.columns:
            return JSONResponse(status_code=400, content={"xatolik": "Excelda kamida 'telefon' va 'ball' ustunlari bo‘lishi shart!"})

        cursor.execute("SELECT id, telefon, fio FROM oquvchilar")
        barcha_oquvchilar = cursor.fetchall()
        oquvchi_map = {tozalash_telefon(u[1]): (u[0], u[2]) for u in barcha_oquvchilar}

        muvaffaqiyatli = 0
        b_tur = "oylik" if "oylik" in bosqich_turi.lower() else "haftalik"

        oy_nomi_toza = tanlangan_oy.strip().capitalize() if tanlangan_oy else "Oktyabr"
        oy_raqami = OY_NOM_RAQAM.get(oy_nomi_toza.lower(), 10)
        hafta_val = int(tanlangan_hafta) if b_tur == "haftalik" else 1
        fan_nomi = tanlangan_fan.strip().capitalize() if tanlangan_fan else "Informatika"

        for _, row in df.iterrows():
            val_ball = row["ball"]
            if pd.isna(val_ball) or str(val_ball).strip() == "":
                continue

            try:
                ball_val = int(float(str(val_ball).strip()))
            except:
                continue

            tel_xom = str(row["telefon"]).strip()
            tel_toza = tozalash_telefon(tel_xom)

            if tel_toza not in oquvchi_map:
                continue

            oquvchi_id = oquvchi_map[tel_toza][0]

            if b_tur == "haftalik":
                cursor.execute("""
                    SELECT COUNT(*) + 1 FROM natijalar
                    WHERE fan = ? AND bosqich_turi = 'haftalik' AND oy_nomi = ? AND hafta_raqami = ? AND ball > ?
                """, (fan_nomi, oy_nomi_toza, hafta_val, ball_val))
            else:
                cursor.execute("""
                    SELECT COUNT(*) + 1 FROM natijalar
                    WHERE fan = ? AND bosqich_turi = 'oylik' AND oy_nomi = ? AND ball > ?
                """, (fan_nomi, oy_nomi_toza, ball_val))

            auto_orin = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO natijalar (oquvchi_id, tadbir_id, fan, bosqich_turi, hafta_raqami, oy_raqami, oy_nomi, ball, jami_savol, sarflangan_soniya, orin)
                VALUES (?, 1, ?, ?, ?, ?, ?, ?, 100, 0, ?)
            """, (oquvchi_id, fan_nomi, b_tur, hafta_val, oy_raqami, oy_nomi_toza, ball_val, auto_orin))
            muvaffaqiyatli += 1

        conn.commit()
        return {"holat": "Muvaffaqiyatli", "xabar": f"✅ {muvaffaqiyatli} ta o‘quvchining {oy_nomi_toza} oyi natijasi saqlandi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": f"Xatolik: {str(e)}"})
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)