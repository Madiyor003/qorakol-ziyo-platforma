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

    # 3. Natijalar jadvali
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

    # 4. Imtihonlar jadvali
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

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Baza muvaffaqiyatli tayyorlandi!")
