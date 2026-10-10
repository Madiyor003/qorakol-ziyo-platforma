# --- STATISTIKA, TAHRIRLASH VA MONITORING UCHUN MODELLAR ---

class TestTahrirlash(BaseModel):
    nomi: str
    sinf: int
    turi: str
    davomiyligi_daqiqa: int
    narxi: int

# 1. Test parametrlarini tahrirlash
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

# 2. Testdagi barcha savollarni olish (O'qituvchi ko'rishi va tahrirlashi uchun)
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

# 3. Yakka savolni o'chirish
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

# 4. O'qituvchi uchun test statistikasi (Nechta ishladi, kimlar ishladi, real-vaqt monitoringi)
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

        # Testning barcha to'g'ri javoblari
        cursor.execute(f"SELECT id, togri_javob, savol_matni FROM savollar WHERE test_id = {PH}", (test_id,))
        togri_dict = {r[0]: {"kalit": str(r[1]).strip().upper(), "matn": r[2]} for r in cursor.fetchall()}

        urinishlar = []
        for r in rows:
            u_id, fio, tel, sinf, maktab, ball, soniya, holat, bosh_v, javoblar_raw, paketi_raw = r
            
            # Javoblar tahlili
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

# 5. Real vaqtda ishlab turgan o'quvchini testdan chiqarib yuborish (bloklash / to'xtatish)
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

# 6. O'quvchi uchun o'zining test tahlilini ko'rish
@app.get("/api/oquvchi/test_tahlil/{test_id}/{oquvchi_id}")
async def get_student_test_review(test_id: int, oquvchi_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT javoblar_ochiq FROM testlar WHERE id = {PH}", (test_id,))
        t_row = cursor.fetchone()
        if not t_row or not t_row[0]:
            return JSONResponse(status_code=403, content={"xatolik": "O‘qituvchi hali to‘g‘ri javoblarni ochiqlamagan!"})

        cursor.execute(f"""
            SELECT tanlangan_savollar, berilgan_javoblar, ball 
            FROM test_urinishlari 
            WHERE test_id = {PH} AND oquvchi_id = {PH} AND holat = 'yakunlangan'
            ORDER BY id DESC LIMIT 1
        """, (test_id, oquvchi_id))
        row = cursor.fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"xatolik": "Urinish topilmadi!"})

        paketi = json.loads(row[0])
        javoblar = json.loads(row[1]) if row[1] else {}

        savol_ids = [s["savol_id"] for s in paketi]
        placeholders = ",".join(PH for _ in savol_ids)
        cursor.execute(f"SELECT id, togri_javob FROM savollar WHERE id IN ({placeholders})", tuple(savol_ids))
        togri_dict = dict(cursor.fetchall())

        natija_savollar = []
        for s in paketi:
            sid = s["savol_id"]
            belgilangan = str(javoblar.get(str(sid), "")).strip().upper()
            haqiqiy = str(togri_dict.get(sid, "")).strip().upper()
            natija_savollar.append({
                "savol_matni": s["savol_matni"],
                "variantlar": s["variantlar"],
                "belgilangan": belgilangan or "Javob berilmagan",
                "togri_javob": haqiqiy,
                "togrimi": bool(belgilangan and belgilangan == haqiqiy)
            })

        return {"holat": "Muvaffaqiyatli", "ball": row[2], "savollar": natija_savollar}
    except Exception as e:
        return JSONResponse(status_code=500, content={"xatolik": str(e)})
    finally:
        cursor.close()
        conn.close()
