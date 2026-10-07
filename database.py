# -*- coding: utf-8 -*-
import sqlite3

DB_NAME = "olimpiada.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. O'quvchilar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oquvchilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oqituvchilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fio TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            parol TEXT NOT NULL,
            fan TEXT NOT NULL,
            telefon TEXT,
            yaratilgan_vaqt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Natijalar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS natijalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # 4. Imtihonlar va Teskari sanoq jadvali (Yangi)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS imtihonlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
