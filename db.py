from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import config


def connect():
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


def query(sql_text, params=None):
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql_text, params or [])
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def execute(sql_text, params=None):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql_text, params or [])
        conn.commit()
    finally:
        conn.close()


def execute_script_file(path):
    script_path = Path(path)
    sql_text = script_path.read_text(encoding="utf-8")
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql_text)
        conn.commit()
    finally:
        conn.close()
