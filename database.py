# -*- coding: utf-8 -*-
import os
import sqlite3

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    import psycopg2

def get_connection():
    if DATABASE_URL:
        # Render'dagi postgres:// prefiksini to'g'rilash
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(url)
    else:
        return sqlite3.connect("olimpiada.db")

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    is_pg = bool(DATABASE_URL)
    auto_id = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"

    # 1. O'quvchilar jadvali
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS oquvchilar (
            id {auto_id},
            fio TEXT NOT NULL,
            telefon TEXT UNIQUE NOT NULL,
            viloyat TEXT NOT NULL,
            tuman TEXT NOT NULL,
            maktab TEXT NOT NULL,
            sinf INTEGER NOT NULL,
            email TEXT,
            telegram_id TEXT,
            parol TEXT NOT NULL,
            royxatdan_otgan_vaqt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. O'qituvchilar jadvali
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS oqituvchilar (
            id {auto_id},
            fio TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            parol TEXT NOT NULL,
            fan TEXT NOT NULL,
            telefon TEXT,
            yaratilgan_vaqt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Natijalar jadvali (avvalgi arxiv va Excel natijalari uchun)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS natijalar (
            id {auto_id},
            oquvchi_id INTEGER NOT NULL,
            tadbir_id INTEGER DEFAULT 1,
            fan TEXT DEFAULT 'Informatika',
            bosqich_turi TEXT DEFAULT 'haftalik',
            hafta_raqami INTEGER DEFAULT 1,
            oy_raqami INTEGER DEFAULT 10,
            oy_nomi TEXT DEFAULT 'Oktyabr',
            ball INTEGER NOT NULL,
            jami_savol INTEGER DEFAULT 100,
            sarflangan_soniya INTEGER DEFAULT 0,
            orin INTEGER DEFAULT 0,
            sana TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (oquvchi_id) REFERENCES oquvchilar (id)
        )
    """)

    # 4. Imtihonlar jadvali (oflayn e'lonlar uchun)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS imtihonlar (
            id {auto_id},
            nomi TEXT NOT NULL,
            fan TEXT NOT NULL,
            sinf TEXT DEFAULT 'Barcha sinflar',
            boshlanish_vaqti TEXT NOT NULL,
            manzil TEXT NOT NULL,
            faol INTEGER DEFAULT 1,
            yaratilgan_vaqt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 5. YANGI: Onlayn Testlar jadvali (kunlik, haftalik, oylik)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS testlar (
            id {auto_id},
            nomi TEXT NOT NULL,
            fan TEXT NOT NULL,
            sinf INTEGER NOT NULL,
            turi TEXT NOT NULL,
            davomiyligi_daqiqa INTEGER DEFAULT 30,
            narxi INTEGER DEFAULT 0,
            boshlanish_vaqti TIMESTAMP,
            tugash_vaqti TIMESTAMP,
            javoblar_ochiq INTEGER DEFAULT 0,
            yaratuvchi_id INTEGER,
            faol INTEGER DEFAULT 1,
            yaratilgan_vaqt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 6. YANGI: Savollar banki (100 talik baza)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS savollar (
            id {auto_id},
            test_id INTEGER NOT NULL,
            savol_matni TEXT NOT NULL,
            rasm_url TEXT,
            variant_a TEXT NOT NULL,
            variant_b TEXT NOT NULL,
            variant_c TEXT NOT NULL,
            variant_d TEXT NOT NULL,
            togri_javob TEXT NOT NULL,
            FOREIGN KEY (test_id) REFERENCES testlar (id) ON DELETE CASCADE
        )
    """)

    # 7. YANGI: Test urinishlari (25 talik generatsiya va o'quvchi javoblari)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS test_urinishlari (
            id {auto_id},
            oquvchi_id INTEGER NOT NULL,
            test_id INTEGER NOT NULL,
            tanlangan_savollar TEXT NOT NULL,
            berilgan_javoblar TEXT DEFAULT '{{}}',
            ball INTEGER DEFAULT 0,
            sarflangan_soniya INTEGER DEFAULT 0,
            holat TEXT DEFAULT 'boshlangan',
            boshlangan_vaqt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tugatilgan_vaqt TIMESTAMP,
            FOREIGN KEY (oquvchi_id) REFERENCES oquvchilar (id),
            FOREIGN KEY (test_id) REFERENCES testlar (id)
        )
    """)

    # 8. YANGI: To'lovlar va cheklar jadvali (1-usul: Chek yuklash)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS tolovlar (
            id {auto_id},
            oquvchi_id INTEGER NOT NULL,
            test_id INTEGER NOT NULL,
            chek_rasm TEXT NOT NULL,
            summa INTEGER NOT NULL,
            holat TEXT DEFAULT 'kutilmoqda',
            tasdiqlagan_admin_id INTEGER,
            yuklangan_vaqt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (oquvchi_id) REFERENCES oquvchilar (id),
            FOREIGN KEY (test_id) REFERENCES testlar (id)
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Baza barcha yangi jadvallar bilan muvaffaqiyatli tayyorlandi!")
