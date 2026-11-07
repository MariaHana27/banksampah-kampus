import os, time, functools
import jwt, psycopg2, psycopg2.extras
from flask import request, jsonify, g

SECRET = os.environ.get("JWT_SECRET", "dev-secret-ganti-di-produksi")
INTERNAL = os.environ.get("INTERNAL_KEY", "internal-dev-key")
DB_URL = os.environ.get("DATABASE_URL", "postgresql://bank:bank@db:5432/banksampah")
FAKULTAS = ["Bisnis", "Informatika"]


def conn():
    return psycopg2.connect(DB_URL)


def wait_db(retries=30):
    for _ in range(retries):
        try:
            conn().close()
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Database tidak bisa dihubungi")


def query(sql, args=(), one=False):
    c = conn()
    try:
        with c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, args)
            rows = cur.fetchall() if cur.description else []
        if one:
            return rows[0] if rows else None
        return rows
    finally:
        c.close()


def auth(roles=None):
    def deco(f):
        @functools.wraps(f)
        def wrapper(*a, **k):
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            try:
                g.user = jwt.decode(token, SECRET, algorithms=["HS256"])
            except Exception:
                return jsonify(error="Sesi tidak valid, silakan login ulang"), 401
            if roles and g.user.get("role") not in roles:
                return jsonify(error="Akses ditolak untuk peran Anda"), 403
            return f(*a, **k)
        return wrapper
    return deco


def internal(f):
    @functools.wraps(f)
    def wrapper(*a, **k):
        if request.headers.get("X-Internal-Key") != INTERNAL:
            return jsonify(error="Hanya untuk komunikasi antar service"), 403
        return f(*a, **k)
    return wrapper
