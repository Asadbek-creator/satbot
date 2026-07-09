# -*- coding: utf-8 -*-
"""
Ma'lumotlar bazasi bilan ishlash (SQLite).
Foydalanuvchilar va ularning yuborgan natijalarini saqlaydi.
"""
import sqlite3
import datetime
import json
from contextlib import contextmanager

DB_PATH = "satbot.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            full_name TEXT,
            registered_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            mock_number INTEGER,
            m1_answers TEXT,
            m2_answers TEXT,
            m1_correct INTEGER,
            m2_correct INTEGER,
            raw_score INTEGER,
            scaled_score INTEGER,
            wrong_m1 TEXT,
            wrong_m2 TEXT,
            submitted_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def upsert_user(tg_id, username, first_name_tg, full_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT tg_id FROM users WHERE tg_id=?", (tg_id,))
    row = cur.fetchone()
    now = datetime.datetime.utcnow().isoformat()
    if row:
        cur.execute(
            "UPDATE users SET username=?, first_name=?, full_name=? WHERE tg_id=?",
            (username, first_name_tg, full_name, tg_id),
        )
    else:
        cur.execute(
            "INSERT INTO users (tg_id, username, first_name, full_name, registered_at) VALUES (?,?,?,?,?)",
            (tg_id, username, first_name_tg, full_name, now),
        )
    conn.commit()
    conn.close()


def get_user(tg_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY registered_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def save_submission(tg_id, mock_number, m1_answers, m2_answers,
                     m1_correct, m2_correct, raw_score, scaled_score,
                     wrong_m1, wrong_m2):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO submissions
        (tg_id, mock_number, m1_answers, m2_answers, m1_correct, m2_correct,
         raw_score, scaled_score, wrong_m1, wrong_m2, submitted_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (tg_id, mock_number, json.dumps(m1_answers, ensure_ascii=False),
          json.dumps(m2_answers, ensure_ascii=False), m1_correct, m2_correct,
          raw_score, scaled_score, json.dumps(wrong_m1, ensure_ascii=False),
          json.dumps(wrong_m2, ensure_ascii=False), now))
    conn.commit()
    conn.close()


def get_all_submissions():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.*, u.full_name, u.username
        FROM submissions s LEFT JOIN users u ON s.tg_id = u.tg_id
        ORDER BY s.submitted_at DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_scores_for_mock(mock_number, exclude_tg_id=None):
    conn = get_conn()
    cur = conn.cursor()
    if exclude_tg_id is not None:
        cur.execute(
            "SELECT scaled_score FROM submissions WHERE mock_number=? AND scaled_score IS NOT NULL AND tg_id != ?",
            (mock_number, exclude_tg_id),
        )
    else:
        cur.execute(
            "SELECT scaled_score FROM submissions WHERE mock_number=? AND scaled_score IS NOT NULL",
            (mock_number,),
        )
    scores = [r["scaled_score"] for r in cur.fetchall()]
    conn.close()
    return scores


def get_user_submissions(tg_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM submissions WHERE tg_id=? ORDER BY submitted_at DESC", (tg_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
