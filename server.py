# -*- coding: utf-8 -*-
import io
import os
import re
import json
import random
import shutil
from datetime import datetime
import pandas as pd
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict
from database import init_db, get_connection, DATABASE_URL

app = FastAPI(title="Respublika Olimpiada Platformasi")

try:
    init_db()
except Exception as e:
    print(f"init_db xatosi: {e}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

IS_PG = bool(DATABASE_URL)
PH = "%s" if IS_PG else "?"

def get_db():
    return get_connection()

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
    turi: str
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
    togri_javob: str

class TestTopshirish(BaseModel):
    urinish_id: int
    javoblar: Dict[str, str]

class ParolAlmashtirish(BaseModel):
    yangi_parol: str

class TestTahrirlash(BaseModel):
    nomi: str
    sinf: int
    turi: str
    davomiyligi_daqiqa: int
    narxi: int

# --- HTML Sahifalar ---
@app.get("/")
async def root(): return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))

@app.get("/royxat")
async def royxat_page(): return FileResponse(os.path.join(TEMPLATES_DIR, "royxat.html"))

@app.get("/login")
async def login_page(): return FileResponse(os.path.join(TEMPLATES_DIR, "login.html"))

@app.get("/kabinet")
async def kabinet_page(): return FileResponse(os.path.join(TEMPLATES_DIR, "kabinet.html"))

@app.get("/reyting")
async def reyting_page(): return FileResponse(os.path.join(TEMPLATES_DIR, "reyting.html"))

@app.get("/oqituvchi-login")
async def oqituvchi_login_page(): return FileResponse(os.path.join(TEMPLATES_DIR, "oqituvchi_login.html"))

@app.get("/oqituvchi")
async def oqituvchi_panel_page(): return FileResponse(os.path.join(TEMPLATES_DIR, "oqituvchi.html"))

@app.get("/admin-login")
async def admin_login_page(): return FileResponse(os.path.join(TEMPLATES_DIR, "admin_login.html"))

@app.get("/admin")
async def admin_page(): return FileResponse(os.path.join(TEMPLATES_DIR, "admin.html"))

@app.get("/test/{test_id}")
async def online_test_page(test_id: int): return FileResponse(os.path.join(TEMPLATES_DIR, "test_ishlash.html"))

@app.get("/aloqa")
async def aloqa_page(): return FileResponse(os.path.join(TEMPLATES_DIR, "aloqa.html"))

# --- 1. O'quvchi ro'yxatdan o'tish va login ---
@app.post("/api/register")
async def register_student(data: OquvchiRoyxat):
    conn = get_db()
    cursor = conn.cursor()
    try:
        t_toza = tozalash_telefon(data.telefon)
        cursor.execute(f"SELECT id FROM oquvchilar WHERE telefon = {PH}", (t_toza,))
        if cursor.fetchone():
            return JSONResponse(status_code=400, content={"xatolik": "Bu telefon raqami bilan allaqachon ro‘yxatdan o‘tilgan!"})

        if IS_PG:
            sql = f"""
                INSERT INTO oquvchilar (fio, telefon, viloyat, tuman, maktab, sinf, email, telegram_id, parol)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
                RETURNING id
            """
            cursor.execute(sql, (
                data.fio.strip(), t_toza, data.viloyat.strip(), data.tuman.strip(),
                data.maktab.strip(), data.sinf, (data.email or "").strip(),
                (data.telegram_id or "").strip().replace("@", ""), data.parol.strip()
            ))
            yangi_id = cursor.fetchone()[0]
        else:
            sql = f"""
                INSERT INTO oquvchilar (fio, telefon, viloyat, tuman, maktab, sinf, email, telegram_id, parol)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
            """
            cursor.execute(sql, (
                data.fio.strip(), t_toza, data.viloyat.strip(), data.tuman.strip(),
                data.maktab.strip(), data.sinf, (data.email or "").strip(),
                (data.telegram_id or "").strip().replace("@", ""), data.parol.strip()
            ))
            yangi_id = cursor.lastrowid

        return {
            "holat": "Muvaffaqiyatli",
            "oquvchi": {
                "id": yangi_id,
                "fio": data.fio.strip(),
                "sinf": data.sinf,
                "viloyat": data.viloyat.strip(),
                "maktab": data.maktab.strip()
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": f"Xatolik: {str(e)}"})
    finally:
        cursor.close()
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
            if (baza_tel == kirgan_tel or str(u[5]).strip() == kirgan_login) and baza_parol == kirgan_parol:
                return {
                    "holat": "Muvaffaqiyatli",
                    "oquvchi": {"id": u[0], "fio": u[1], "sinf": u[2], "viloyat": u[3], "maktab": u[4]}
                }
        return JSONResponse(status_code=401, content={"xatolik": "Telefon yoki parol noto‘g‘ri!"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.get("/api/oquvchi_natijalari/{oquvchi_id}")
async def get_student_results(oquvchi_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT fio, viloyat, maktab, sinf FROM oquvchilar WHERE id = {PH}", (oquvchi_id,))
        user = cursor.fetchone()
        if not user:
            return JSONResponse(status_code=404, content={"xatolik": "O‘quvchi topilmadi"})

        cursor.execute(f"""
            SELECT bosqich_turi, hafta_raqami, oy_raqami, oy_nomi, ball, jami_savol, orin, sana, fan, id
            FROM natijalar
            WHERE oquvchi_id = {PH}
            ORDER BY id DESC
        """, (oquvchi_id,))
        rows = cursor.fetchall()

        tarix = []
        for r in rows:
            orin_korsatish = r[6] if (r[6] and r[6] > 0) else 1
            tarix.append({
                "id": r[9],
                "bosqich_turi": str(r[0]).strip().lower() if r[0] else "haftalik",
                "hafta_raqami": int(r[1]) if r[1] is not None else 1,
                "oy_raqami": int(r[2]) if r[2] is not None else 10,
                "oy_nomi": str(r[3]).strip() if r[3] else "Oktyabr",
                "ball": int(r[4]) if r[4] is not None else 0,
                "jami_savol": int(r[5]) if r[5] is not None else 100,
                "orin": orin_korsatish,
                "sana": str(r[7]) if r[7] else "",
                "fan": str(r[8]).strip() if r[8] else "Informatika"
            })

        return {
            "oquvchi": {"fio": user[0], "viloyat": user[1], "maktab": user[2], "sinf": user[3]},
            "tarix": tarix
        }
    except Exception as e:
        return {"oquvchi": {}, "tarix": []}
    finally:
        cursor.close()
        conn.close()

# --- 2. O'qituvchilar boshqaruvi ---
@app.post("/api/admin/oqituvchi_qoshish")
async def admin_add_teacher(data: YangiOqituvchi):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT id FROM oqituvchilar WHERE login = {PH}", (data.login.strip(),))
        if cursor.fetchone():
            return JSONResponse(status_code=400, content={"xatolik": "Ushbu login band, boshqa login tanlang!"})

        sql = f"""
            INSERT INTO oqituvchilar (fio, login, parol, fan, telefon)
            VALUES ({PH}, {PH}, {PH}, {PH}, {PH})
        """
        cursor.execute(sql, (
            data.fio.strip(), data.login.strip(), data.parol.strip(),
            data.fan.strip(), (data.telefon or "").strip()
        ))
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘qituvchi muvaffaqiyatli saqlandi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": f"Xatolik: {str(e)}"})
    finally:
        cursor.close()
        conn.close()

@app.get("/api/admin/oqituvchilar")
async def list_teachers():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, fio, login, parol, fan, telefon FROM oqituvchilar ORDER BY id DESC")
        rows = cursor.fetchall()
        return [{"id": r[0], "fio": r[1], "login": r[2], "parol": r[3], "fan": r[4], "telefon": r[5]} for r in rows]
    except Exception as e:
        return []
    finally:
        cursor.close()
        conn.close()

@app.put("/api/admin/oqituvchi_parol/{tid}")
async def admin_change_teacher_password(tid: int, data: ParolAlmashtirish):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE oqituvchilar SET parol = {PH} WHERE id = {PH}", (data.yangi_parol.strip(), tid))
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘qituvchi paroli muvaffaqiyatli o‘zgartirildi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/admin/oqituvchi_ochirish/{tid}")
async def delete_teacher(tid: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM oqituvchilar WHERE id = {PH}", (tid,))
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘qituvchi tizimdan o‘chirildi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.post("/api/oqituvchi/login")
async def login_teacher(data: LoginUniversal):
    conn = get_db()
    cursor = conn.cursor()
    try:
        kirgan_login = (data.login or data.username or data.telefon or "").strip()
        kirgan_parol = (data.parol or data.password or "").strip()
        cursor.execute(f"SELECT id, fio, fan FROM oqituvchilar WHERE login = {PH} AND parol = {PH}", (kirgan_login, kirgan_parol))
        t = cursor.fetchone()
        if t:
            return {"holat": "Muvaffaqiyatli", "oqituvchi": {"id": t[0], "fio": t[1], "fan": t[2]}}
        return JSONResponse(status_code=401, content={"xatolik": "O‘qituvchi logini yoki paroli noto‘g‘ri!"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

# --- 3. Super Admin va Imtihonlar ---
@app.post("/api/admin/login")
async def admin_login(data: LoginUniversal):
    kirgan_login = (data.login or data.username or "").strip()
    kirgan_parol = (data.parol or data.password or "").strip()
    if kirgan_login == "admin" and kirgan_parol == "admin2026":
        return {"holat": "Muvaffaqiyatli", "token": "super_admin_2026"}
    return JSONResponse(status_code=401, content={"xatolik": "Super Admin logini yoki paroli xato!"})

@app.post("/api/admin/imtihon_qoshish")
async def add_exam(data: YangiImtihon):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            INSERT INTO imtihonlar (nomi, fan, sinf, boshlanish_vaqti, manzil, faol)
            VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, 1)
        """, (data.nomi.strip(), data.fan.strip(), data.sinf.strip(), data.boshlanish_vaqti.strip(), data.manzil.strip()))
        return {"holat": "Muvaffaqiyatli", "xabar": "Imtihon e'lon qilindi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.get("/api/admin/imtihonlar")
async def list_exams():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, nomi, fan, sinf, boshlanish_vaqti, manzil, faol FROM imtihonlar ORDER BY id DESC")
        rows = cursor.fetchall()
        return [{"id": r[0], "nomi": r[1], "fan": r[2], "sinf": r[3], "boshlanish_vaqti": r[4], "manzil": r[5], "faol": r[6]} for r in rows]
    except:
        return []
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/admin/imtihon_ochirish/{iid}")
async def delete_exam(iid: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM imtihonlar WHERE id = {PH}", (iid,))
        return {"holat": "Muvaffaqiyatli", "xabar": "Imtihon o‘chirildi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.get("/api/admin/oquvchilar")
async def list_students():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, fio, telefon, maktab, sinf, parol, viloyat FROM oquvchilar ORDER BY sinf ASC, fio ASC")
        rows = cursor.fetchall()
        return [{"id": r[0], "fio": r[1], "telefon": r[2], "maktab": r[3], "sinf": r[4], "parol": r[5], "viloyat": r[6] if len(r)>6 else "Buxoro"} for r in rows]
    except:
        return []
    finally:
        cursor.close()
        conn.close()

@app.put("/api/admin/oquvchi_parol/{oid}")
async def admin_change_student_password(oid: int, data: ParolAlmashtirish):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE oquvchilar SET parol = {PH} WHERE id = {PH}", (data.yangi_parol.strip(), oid))
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘quvchi paroli muvaffaqiyatli o‘zgartirildi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/admin/oquvchi_tarix_tozalash/{oid}")
async def admin_clear_student_history(oid: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM natijalar WHERE oquvchi_id = {PH}", (oid,))
        cursor.execute(f"DELETE FROM test_urinishlari WHERE oquvchi_id = {PH}", (oid,))
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘quvchining barcha natijalari va test urinishlari tozalandi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/admin/oquvchi_ochirish/{oid}")
async def delete_student(oid: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM natijalar WHERE oquvchi_id = {PH}", (oid,))
        cursor.execute(f"DELETE FROM test_urinishlari WHERE oquvchi_id = {PH}", (oid,))
        cursor.execute(f"DELETE FROM oquvchilar WHERE id = {PH}", (oid,))
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘quvchi tizimdan to‘liq o‘chirildi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

# --- 4. To'lovlar va cheklar ---
@app.post("/api/tolov/chek_yuklash")
async def upload_payment_receipt(oquvchi_id: int = Form(...), test_id: int = Form(...), summa: int = Form(10000), chek: UploadFile = File(...)):
    conn = get_db()
    cursor = conn.cursor()
    try:
        fayl_kengaytma = chek.filename.split(".")[-1]
        yangi_nom = f"chek_{oquvchi_id}_{test_id}_{int(datetime.now().timestamp())}.{fayl_kengaytma}"
        fayl_manzili = os.path.join(UPLOADS_DIR, yangi_nom)

        with open(fayl_manzili, "wb") as buffer:
            shutil.copyfileobj(chek.file, buffer)

        db_url = f"/static/uploads/{yangi_nom}"
        cursor.execute(f"""
            INSERT INTO tolovlar (oquvchi_id, test_id, chek_rasm, summa, holat)
            VALUES ({PH}, {PH}, {PH}, {PH}, 'kutilmoqda')
        """, (oquvchi_id, test_id, db_url, summa))
        return {"holat": "Muvaffaqiyatli", "xabar": "To‘lov chekingiz qabul qilindi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.get("/api/admin/kutilayotgan_tolovlar")
async def get_pending_payments():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, oquvchi_id, test_id, summa, chek_rasm, yuklangan_vaqt FROM tolovlar WHERE holat = 'kutilmoqda' ORDER BY id DESC")
        rows = cursor.fetchall()
        natija = []
        for r in rows:
            cursor.execute(f"SELECT fio, telefon FROM oquvchilar WHERE id = {PH}", (r[1],))
            o = cursor.fetchone()
            cursor.execute(f"SELECT nomi FROM testlar WHERE id = {PH}", (r[2],))
            t = cursor.fetchone()
            natija.append({
                "id": r[0],
                "fio": o[0] if o else "Noma'lum",
                "telefon": o[1] if o else "-",
                "test_nomi": t[0] if t else "Test",
                "summa": r[3],
                "chek_rasm": r[4],
                "vaqt": str(r[5])
            })
        return natija
    except:
        return []
    finally:
        cursor.close()
        conn.close()

@app.put("/api/admin/tolov_tasdiqlash/{tolov_id}")
async def approve_payment(tolov_id: int, holat: str = "tasdiqlandi"):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE tolovlar SET holat = {PH} WHERE id = {PH}", (holat, tolov_id))
        return {"holat": "Muvaffaqiyatli", "xabar": f"To‘lov holati '{holat}' ga o‘zgartirildi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

# --- 5. Onlayn testlar yaratish va tahrirlash ---
@app.post("/api/admin/online_test_yaratish")
async def create_online_test(data: YangiOnlineTest):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            INSERT INTO testlar (nomi, fan, sinf, turi, davomiyligi_daqiqa, narxi, boshlanish_vaqti, tugash_vaqti, yaratuvchi_id, javoblar_ochiq)
            VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, 0)
        """, (data.nomi.strip(), data.fan.strip(), data.sinf, data.turi.strip(), data.davomiyligi_daqiqa, data.narxi, data.boshlanish_vaqti, data.tugash_vaqti, data.yaratuvchi_id))
        return {"holat": "Muvaffaqiyatli", "xabar": "Yangi test bazasi yaratildi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.put("/api/test/tahrirlash/{test_id}")
async def edit_test_details(test_id: int, data: TestTahrirlash):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            UPDATE testlar 
            SET nomi = {PH}, sinf = {PH}, turi = {PH}, davomiyligi_daqiqa = {PH}, narxi = {PH}
            WHERE id = {PH}
        """, (data.nomi.strip(), data.sinf, data.turi.strip(), data.davomiyligi_daqiqa, data.narxi, test_id))
        return {"holat": "Muvaffaqiyatli", "xabar": "Test muvaffaqiyatli tahrirlandi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/test/ochirish/{test_id}")
async def delete_test(test_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM savollar WHERE test_id = {PH}", (test_id,))
        cursor.execute(f"DELETE FROM test_urinishlari WHERE test_id = {PH}", (test_id,))
        cursor.execute(f"DELETE FROM natijalar WHERE tadbir_id = {PH}", (test_id,))
        cursor.execute(f"DELETE FROM tolovlar WHERE test_id = {PH}", (test_id,))
        cursor.execute(f"DELETE FROM testlar WHERE id = {PH}", (test_id,))
        return {"holat": "Muvaffaqiyatli", "xabar": "Test va unga tegishli savollar butunlay o‘chirildi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.get("/api/testlar/royxat")
async def get_test_list(sinf: Optional[int] = None, fan: Optional[str] = None, oquvchi_id: Optional[int] = None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        sql = "SELECT id, nomi, fan, sinf, turi, davomiyligi_daqiqa, narxi, boshlanish_vaqti, tugash_vaqti, javoblar_ochiq FROM testlar WHERE faol = 1"
        params = []
        if sinf:
            sql += f" AND (sinf = {PH} OR sinf = 0)"
            params.append(sinf)
        if fan:
            sql += f" AND fan = {PH}"
            params.append(fan)
        sql += " ORDER BY id DESC"
        cursor.execute(sql, tuple(params))
        tests = cursor.fetchall()

        natija = []
        hozir = datetime.now()

        for t in tests:
            test_id, nomi, t_fan, t_sinf, turi, daqiqa, narxi, bosh_v, tug_v, j_ochiq = t
            holat = "faol"

            if bosh_v:
                try:
                    bosh_dt = datetime.fromisoformat(str(bosh_v))
                    if hozir < bosh_dt: holat = "kutilmoqda"
                except: pass
            if tug_v:
                try:
                    tug_dt = datetime.fromisoformat(str(tug_v))
                    if hozir > tug_dt: holat = "otkazildi"
                except: pass

            ishlangan = False
            toplagan_ball = None
            tolangan = False if narxi > 0 else True

            if oquvchi_id:
                cursor.execute(f"SELECT holat, ball FROM test_urinishlari WHERE test_id = {PH} AND oquvchi_id = {PH}", (test_id, oquvchi_id))
                u = cursor.fetchone()
                if u:
                    ishlangan = True
                    toplagan_ball = u[1]

                if narxi > 0:
                    cursor.execute(f"SELECT holat FROM tolovlar WHERE test_id = {PH} AND oquvchi_id = {PH} AND holat = 'tasdiqlandi'", (test_id, oquvchi_id))
                    if cursor.fetchone():
                        tolangan = True

            cursor.execute(f"SELECT COUNT(*) FROM savollar WHERE test_id = {PH}", (test_id,))
            s_soni = cursor.fetchone()[0]

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
                "javoblar_ochiq": bool(j_ochiq),
                "savollar_soni": s_soni,
                "boshlanish_vaqti": str(bosh_v) if bosh_v else None,
                "tugash_vaqti": str(tug_v) if tug_v else None
            })

        return {"holat": "Muvaffaqiyatli", "testlar": natija}
    except Exception as e:
        return {"holat": "Xatolik", "testlar": []}
    finally:
        cursor.close()
        conn.close()

# --- 6. Savollar va Test Ishlash Mexanizmi ---
@app.get("/api/test/savollari/{test_id}")
async def get_test_questions_for_teacher(test_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            SELECT id, savol_matni, variant_a, variant_b, variant_c, variant_d, togri_javob 
            FROM savollar WHERE test_id = {PH} ORDER BY id ASC
        """, (test_id,))
        rows = cursor.fetchall()
        savollar = []
        for r in rows:
            savollar.append({
                "id": r[0], "savol_matni": r[1],
                "a": r[2], "b": r[3], "c": r[4], "d": r[5],
                "togri_javob": r[6]
            })
        return {"holat": "Muvaffaqiyatli", "savollar": savollar}
    except Exception as e:
        return {"holat": "Xatolik", "savollar": []}
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/savol/ochirish/{savol_id}")
async def delete_single_question(savol_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM savollar WHERE id = {PH}", (savol_id,))
        return {"holat": "Muvaffaqiyatli", "xabar": "Savol o‘chirildi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.get("/api/test/boshlash/{test_id}")
async def start_test(test_id: int, oquvchi_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT id, tanlangan_savollar, holat, boshlangan_vaqt FROM test_urinishlari WHERE test_id = {PH} AND oquvchi_id = {PH}", (test_id, oquvchi_id))
        eski_urinish = cursor.fetchone()

        if eski_urinish:
            if eski_urinish[2] == "yakunlangan":
                return JSONResponse(status_code=400, content={"xatolik": "Siz ushbu testni allaqachon topshirgansiz!"})
            urinish_id = eski_urinish[0]
            savollar_paketi = json.loads(eski_urinish[1])
            return {"urinish_id": urinish_id, "savollar": savollar_paketi, "boshlangan_vaqt": str(eski_urinish[3])}

        cursor.execute(f"SELECT id, savol_matni, rasm_url, variant_a, variant_b, variant_c, variant_d, togri_javob FROM savollar WHERE test_id = {PH}", (test_id,))
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

        hozir_iso = datetime.now().isoformat()
        if IS_PG:
            cursor.execute(f"""
                INSERT INTO test_urinishlari (oquvchi_id, test_id, tanlangan_savollar, holat, boshlangan_vaqt)
                VALUES ({PH}, {PH}, {PH}, 'boshlangan', CURRENT_TIMESTAMP) RETURNING id, boshlangan_vaqt
            """, (oquvchi_id, test_id, json.dumps(savollar_paketi)))
            row_res = cursor.fetchone()
            yangi_urinish_id = row_res[0]
            bosh_vaqt = str(row_res[1])
        else:
            cursor.execute(f"""
                INSERT INTO test_urinishlari (oquvchi_id, test_id, tanlangan_savollar, holat, boshlangan_vaqt)
                VALUES ({PH}, {PH}, {PH}, 'boshlangan', {PH})
            """, (oquvchi_id, test_id, json.dumps(savollar_paketi), hozir_iso))
            yangi_urinish_id = cursor.lastrowid
            bosh_vaqt = hozir_iso

        return {"urinish_id": yangi_urinish_id, "savollar": savollar_paketi, "boshlangan_vaqt": bosh_vaqt}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.post("/api/test/topshirish")
async def submit_test(data: TestTopshirish):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT oquvchi_id, test_id, tanlangan_savollar, boshlangan_vaqt, holat FROM test_urinishlari WHERE id = {PH}", (data.urinish_id,))
        urinish = cursor.fetchone()

        if not urinish:
            return JSONResponse(status_code=404, content={"xatolik": "Urinish topilmadi!"})
        if urinish[4] == "yakunlangan":
            return JSONResponse(status_code=400, content={"xatolik": "Test allaqachon topshirilgan!"})

        oquvchi_id, test_id, paketi_str, bosh_v, _ = urinish
        paketi = json.loads(paketi_str)
        savol_ids = [s["savol_id"] for s in paketi]

        placeholders = ",".join(PH for _ in savol_ids)
        cursor.execute(f"SELECT id, togri_javob FROM savollar WHERE id IN ({placeholders})", tuple(savol_ids))
        togri_javoblar = dict(cursor.fetchall())

        ball = 0
        tafsilotlar = []
        for s in paketi:
            sid = str(s["savol_id"])
            belgilangan = data.javoblar.get(sid, "").strip().upper()
            haqiqiy_togri = togri_javoblar.get(int(sid), "").strip().upper()
            togrimi = bool(belgilangan and haqiqiy_togri and belgilangan == haqiqiy_togri)
            if togrimi:
                ball += 4
            tafsilotlar.append({
                "savol_id": int(sid),
                "savol_matni": s["savol_matni"],
                "belgilangan": belgilangan,
                "togri_javob": haqiqiy_togri,
                "togrimi": togrimi
            })

        hozir = datetime.now()
        sarflangan = 0
        if bosh_v:
            try:
                bosh_str = str(bosh_v).replace("Z", "")
                if "T" in bosh_str:
                    bosh_dt = datetime.fromisoformat(bosh_str)
                else:
                    bosh_dt = datetime.strptime(bosh_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
                sarflangan = max(1, int((hozir - bosh_dt).total_seconds()))
            except:
                sarflangan = 60

        cursor.execute(f"""
            UPDATE test_urinishlari
            SET berilgan_javoblar = {PH}, ball = {PH}, sarflangan_soniya = {PH}, holat = 'yakunlangan', tugatilgan_vaqt = CURRENT_TIMESTAMP
            WHERE id = {PH}
        """, (json.dumps(data.javoblar), ball, sarflangan, data.urinish_id))

        cursor.execute(f"SELECT fan, turi FROM testlar WHERE id = {PH}", (test_id,))
        t_info = cursor.fetchone()
        fan_n = t_info[0] if t_info else "Informatika"
        b_tur = t_info[1] if t_info else "kunlik"

        cursor.execute(f"""
            SELECT COUNT(*) FROM natijalar 
            WHERE fan = {PH} AND bosqich_turi = {PH} AND (ball > {PH} OR (ball = {PH} AND sarflangan_soniya < {PH}))
        """, (fan_n, b_tur, ball, ball, sarflangan))
        yangi_orin = (cursor.fetchone()[0] or 0) + 1

        cursor.execute(f"""
            INSERT INTO natijalar (oquvchi_id, tadbir_id, fan, bosqich_turi, ball, jami_savol, sarflangan_soniya, orin)
            VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, 100, {PH}, {PH})
        """, (oquvchi_id, test_id, fan_n, b_tur, ball, sarflangan, yangi_orin))

        cursor.execute(f"SELECT javoblar_ochiq FROM testlar WHERE id = {PH}", (test_id,))
        j_ochiq = bool(cursor.fetchone()[0])

        daq = sarflangan // 60
        son = sarflangan % 60

        return {
            "holat": "Muvaffaqiyatli",
            "ball": ball,
            "sarflangan_soniya": sarflangan,
            "vaqt_matn": f"{daq} daqiqa {son} soniya",
            "orin": yangi_orin,
            "javoblar_ochiq": j_ochiq,
            "tafsilotlar": tafsilotlar if j_ochiq else []
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.put("/api/test/javoblarni_ochish/{test_id}")
async def toggle_answers(test_id: int, ochish: bool = True):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE testlar SET javoblar_ochiq = {PH} WHERE id = {PH}", (1 if ochish else 0, test_id))
        return {"holat": "Muvaffaqiyatli", "xabar": "To‘g‘ri javoblar ochildi!" if ochish else "Javoblar yopildi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.post("/api/test/savol_qoshish")
async def add_single_question(data: BittalikSavol):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            INSERT INTO savollar (test_id, savol_matni, rasm_url, variant_a, variant_b, variant_c, variant_d, togri_javob)
            VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
        """, (data.test_id, data.savol_matni.strip(), data.rasm_url, data.variant_a.strip(), data.variant_b.strip(), data.variant_c.strip(), data.variant_d.strip(), data.togri_javob.strip().upper()))
        return {"holat": "Muvaffaqiyatli", "xabar": "Savol qo‘shildi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.post("/api/test/savollar_matn_yuklash")
async def upload_text_questions(test_id: int = Form(...), matn: str = Form(...)):
    conn = get_db()
    cursor = conn.cursor()
    try:
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

            cursor.execute(f"""
                INSERT INTO savollar (test_id, savol_matni, variant_a, variant_b, variant_c, variant_d, togri_javob)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
            """, (test_id, s_matn.strip(), va.strip(), vb.strip(), vc.strip(), vd.strip(), togri_harf))
            qoshildi += 1
        return {"holat": "Muvaffaqiyatli", "xabar": f"✅ {qoshildi} ta savol saqlandi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

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
            cursor.execute(f"""
                INSERT INTO savollar (test_id, savol_matni, variant_a, variant_b, variant_c, variant_d, togri_javob)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
            """, (test_id, str(row["savol"]).strip(), str(row["a"]).strip(), str(row["b"]).strip(), str(row["c"]).strip(), str(row["d"]).strip(), str(row["javob"]).strip().upper()))
            qoshildi += 1

        return {"holat": "Muvaffaqiyatli", "xabar": f"✅ Exceldan {qoshildi} ta savol muvaffaqiyatli yuklandi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": f"Excel o‘qishda xatolik: {str(e)}"})
    finally:
        cursor.close()
        conn.close()

# --- 7. Statistika, Jonli Monitoring va O'quvchi Tahlili ---
@app.get("/api/test/statistika/{test_id}")
async def get_test_statistics(test_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            SELECT u.id, o.fio, o.telefon, o.sinf, o.maktab, u.ball, u.sarflangan_soniya, u.holat, u.boshlangan_vaqt, u.berilgan_javoblar, u.tanlangan_savollar
            FROM test_urinishlari u
            JOIN oquvchilar o ON u.oquvchi_id = o.id
            WHERE u.test_id = {PH}
            ORDER BY u.id DESC
        """, (test_id,))
        rows = cursor.fetchall()

        cursor.execute(f"SELECT id, togri_javob, savol_matni FROM savollar WHERE test_id = {PH}", (test_id,))
        togri_dict = {r[0]: {"kalit": str(r[1]).strip().upper(), "matn": r[2]} for r in cursor.fetchall()}

        urinishlar = []
        for r in rows:
            u_id, fio, tel, sinf, maktab, ball, soniya, holat, bosh_v, javoblar_raw, paketi_raw = r
            
            javoblar = json.loads(javoblar_raw) if javoblar_raw else {}
            tahlil = []
            if paketi_raw:
                try:
                    paketi = json.loads(paketi_raw)
                    for s in paketi:
                        sid = s["savol_id"]
                        belgilangan = str(javoblar.get(str(sid), "")).strip().upper()
                        asl_togri = togri_dict.get(sid, {}).get("kalit", "")
                        tahlil.append({
                            "savol_id": sid,
                            "savol_matni": s.get("savol_matni", ""),
                            "belgilangan": belgilangan or "Javobsiz",
                            "togri": asl_togri,
                            "togrimi": bool(belgilangan and belgilangan == asl_togri)
                        })
                except: pass

            urinishlar.append({
                "urinish_id": u_id,
                "fio": fio,
                "telefon": tel,
                "sinf": sinf,
                "maktab": maktab,
                "ball": ball or 0,
                "sarflangan_soniya": soniya or 0,
                "holat": holat,
                "boshlangan_vaqt": str(bosh_v),
                "tahlil": tahlil
            })

        return {"holat": "Muvaffaqiyatli", "urinishlar": urinishlar}
    except Exception as e:
        return {"holat": "Xatolik", "urinishlar": [], "xatolik": str(e)}
    finally:
        cursor.close()
        conn.close()

@app.put("/api/test/chiqarib_yuborish/{urinish_id}")
async def kick_student_from_test(urinish_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            UPDATE test_urinishlari 
            SET holat = 'yakunlangan', ball = 0 
            WHERE id = {PH}
        """, (urinish_id,))
        return {"holat": "Muvaffaqiyatli", "xabar": "O‘quvchi testdan chiqarib yuborildi va urinishi bekor qilindi!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()

@app.get("/api/oquvchi/test_tahlil/{test_id}/{oquvchi_id}")
async def get_student_test_review(test_id: int, oquvchi_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            SELECT tanlangan_savollar, berilgan_javoblar, ball 
            FROM test_urinishlari 
            WHERE test_id = {PH} AND oquvchi_id = {PH}
            ORDER BY id DESC LIMIT 1
        """, (test_id, oquvchi_id))
        row = cursor.fetchone()
        
        if not row:
            return JSONResponse(status_code=404, content={"xatolik": "Siz ushbu testni hali ishlamagansiz!"})

        paketi_raw, javoblar_raw, ball = row
        paketi = json.loads(paketi_raw) if paketi_raw else []
        javoblar = json.loads(javoblar_raw) if javoblar_raw else {}

        savol_ids = [s.get("savol_id") for s in paketi if isinstance(s, dict) and "savol_id" in s]
        togri_dict = {}
        if savol_ids:
            placeholders = ",".join(PH for _ in savol_ids)
            cursor.execute(f"SELECT id, togri_javob FROM savollar WHERE id IN ({placeholders})", tuple(savol_ids))
            for r in cursor.fetchall():
                togri_dict[r[0]] = str(r[1]).strip().upper()

        natija_savollar = []
        for s in paketi:
            sid = s.get("savol_id")
            belgilangan = str(javoblar.get(str(sid), "")).strip().upper()
            haqiqiy = str(togri_dict.get(sid, "")).strip().upper()
            
            natija_savollar.append({
                "savol_matni": s.get("savol_matni", "Savol matni mavjud emas"),
                "variantlar": s.get("variantlar", []),
                "belgilangan": belgilangan if belgilangan else "Belgilanmagan",
                "togri_javob": haqiqiy if haqiqiy else "Ko‘rsatilmagan",
                "togrimi": bool(belgilangan and haqiqiy and belgilangan == haqiqiy)
            })

        return {
            "holat": "Muvaffaqiyatli",
            "ball": ball or 0,
            "savollar": natija_savollar
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": f"Tahlil xatosi: {str(e)}"})
    finally:
        cursor.close()
        conn.close()

# --- 8. REYTING ---
@app.get("/api/reyting")
async def get_leaderboard(fan: Optional[str] = "Informatika", bosqich_turi: Optional[str] = "haftalik", oy_nomi: Optional[str] = "Oktyabr", hafta_raqami: Optional[int] = 1, sinf: Optional[str] = "barchasi"):
    conn = get_db()
    cursor = conn.cursor()
    try:
        b_tur = "oylik" if "oylik" in str(bosqich_turi).lower() else "haftalik"
        oy_nomi_toza = str(oy_nomi).strip().capitalize() if oy_nomi else "Oktyabr"
        fan_toza = str(fan).strip().capitalize() if fan else "Informatika"

        sql = f"""
            SELECT o.id, o.fio, o.sinf, o.maktab, o.viloyat, n.ball, n.jami_savol, n.sarflangan_soniya
            FROM natijalar n
            JOIN oquvchilar o ON n.oquvchi_id = o.id
            WHERE n.fan = {PH} AND n.bosqich_turi = {PH} AND n.oy_nomi = {PH}
        """
        params = [fan_toza, b_tur, oy_nomi_toza]

        if b_tur == "haftalik":
            sql += f" AND n.hafta_raqami = {PH}"
            params.append(int(hafta_raqami or 1))

        if sinf and sinf != "barchasi" and sinf.isdigit():
            sql += f" AND CAST(o.sinf AS INTEGER) = {PH}"
            params.append(int(sinf))

        sql += " ORDER BY n.ball DESC, n.sarflangan_soniya ASC, o.fio ASC"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()

        natijalar = []
        for index, r in enumerate(rows, start=1):
            natijalar.append({
                "orin": index, "oquvchi_id": r[0], "fio": r[1],
                "sinf": r[2], "maktab": r[3], "viloyat": r[4],
                "ball": r[5], "jami_savol": r[6], "sarflangan_soniya": r[7]
            })
        return {"holat": "Muvaffaqiyatli", "reyting": natijalar}
    except:
        return {"holat": "Muvaffaqiyatli", "reyting": []}
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
