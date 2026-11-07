import os
import requests
from flask import Flask, jsonify, request, g
from common import *

app = Flask(__name__)
SETORAN_URL = os.environ.get("SETORAN_URL", "http://setoran:5000")
HADIAH_AWAL = [("Tumbler Ramah Lingkungan", 1500, 10), ("Tote Bag Kampus", 800, 20),
               ("Voucher Kantin Rp10.000", 500, 30), ("Pulpen Daur Ulang", 150, 50),
               ("Tanaman Hias Mini", 300, 15)]


def init_db():
    wait_db()
    query("""CREATE TABLE IF NOT EXISTS hadiah(
        id SERIAL PRIMARY KEY, nama TEXT UNIQUE NOT NULL, biaya_poin INTEGER NOT NULL, stok INTEGER NOT NULL)""")
    query("""CREATE TABLE IF NOT EXISTS penukaran(
        id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, hadiah_id INTEGER, hadiah_nama TEXT,
        poin INTEGER NOT NULL, tanggal TIMESTAMP DEFAULT now())""")
    for n, b, s in HADIAH_AWAL:
        query("INSERT INTO hadiah(nama,biaya_poin,stok) VALUES(%s,%s,%s) ON CONFLICT (nama) DO NOTHING", (n, b, s))


def poin_didapat(uid):
    # komunikasi antar container: Reward -> Setoran
    r = requests.get(f"{SETORAN_URL}/internal/earned/{uid}", headers={"X-Internal-Key": INTERNAL}, timeout=5)
    r.raise_for_status()
    return r.json()["total"]


def poin_terpakai(uid):
    return int(query("SELECT COALESCE(SUM(poin),0) AS s FROM penukaran WHERE user_id=%s", (uid,), one=True)["s"])


@app.get("/health")
def health():
    return jsonify(status="ok", service="reward")


@app.get("/saldo")
@auth(["warga"])
def saldo():
    try:
        dapat = poin_didapat(g.user["uid"])
    except requests.RequestException:
        return jsonify(error="Service Setoran sedang tidak bisa dihubungi"), 503
    pakai = poin_terpakai(g.user["uid"])
    return jsonify(saldo=dapat - pakai, total_didapat=dapat, total_dipakai=pakai)


@app.get("/hadiah")
@auth()
def hadiah():
    return jsonify(query("SELECT id,nama,biaya_poin,stok FROM hadiah ORDER BY biaya_poin"))


@app.post("/tukar")
@auth(["warga"])
def tukar():
    d = request.get_json(force=True, silent=True) or {}
    h = query("SELECT * FROM hadiah WHERE id=%s", (d.get("hadiah_id"),), one=True)
    if not h:
        return jsonify(error="Hadiah tidak ditemukan"), 404
    if h["stok"] <= 0:
        return jsonify(error="Stok hadiah habis"), 400
    uid = g.user["uid"]
    try:
        sisa = poin_didapat(uid) - poin_terpakai(uid)
    except requests.RequestException:
        return jsonify(error="Service Setoran sedang tidak bisa dihubungi"), 503
    if sisa < h["biaya_poin"]:
        return jsonify(error=f"Poin kurang. Saldo {sisa}, butuh {h['biaya_poin']}"), 400
    ok = query("UPDATE hadiah SET stok=stok-1 WHERE id=%s AND stok>0 RETURNING id", (h["id"],), one=True)
    if not ok:
        return jsonify(error="Stok hadiah habis"), 400
    query("INSERT INTO penukaran(user_id,hadiah_id,hadiah_nama,poin) VALUES(%s,%s,%s,%s)",
          (uid, h["id"], h["nama"], h["biaya_poin"]))
    return jsonify(ok=True, sisa=sisa - h["biaya_poin"]), 201


@app.get("/riwayat")
@auth(["warga"])
def riwayat():
    return jsonify(query("""SELECT id,hadiah_nama,poin,to_char(tanggal,'YYYY-MM-DD HH24:MI') AS tanggal
        FROM penukaran WHERE user_id=%s ORDER BY id DESC""", (g.user["uid"],)))


if not os.environ.get("SKIP_DB_INIT"):
    init_db()
