import os
from collections import defaultdict
import requests
from flask import Flask, jsonify
from common import *

app = Flask(__name__)
SETORAN_URL = os.environ.get("SETORAN_URL", "http://setoran:5000")


def ambil_data():
    r = requests.get(f"{SETORAN_URL}/internal/verified", headers={"X-Internal-Key": INTERNAL}, timeout=5)
    r.raise_for_status()
    return r.json()


def rekap_data(rows):
    per_jenis, per_bulan = defaultdict(float), defaultdict(float)
    for r in rows:
        per_jenis[r["jenis"]] += r["berat_kg"]
        per_bulan[r["bulan"]] += r["berat_kg"]
    return {"total_kg": round(sum(r["berat_kg"] for r in rows), 2),
            "total_poin": sum(r["poin"] for r in rows), "jumlah_setoran": len(rows),
            "per_jenis": [{"jenis": k, "kg": round(v, 2)} for k, v in sorted(per_jenis.items(), key=lambda x: -x[1])],
            "per_bulan": [{"bulan": k, "kg": round(v, 2)} for k, v in sorted(per_bulan.items())]}


def leaderboard_data(rows, limit=10):
    u = {}
    for r in rows:
        x = u.setdefault(r["user_id"], {"nama": r["user_nama"], "nim": r["user_nim"],
                                        "fakultas": r["fakultas"], "kg": 0.0, "poin": 0})
        x["kg"] += r["berat_kg"]
        x["poin"] += r["poin"]
    top = sorted(u.values(), key=lambda x: -x["poin"])[:limit]
    for x in top:
        x["kg"] = round(x["kg"], 2)
    return top


def fakultas_data(rows):
    hasil = {f: {"fakultas": f, "kg": 0.0, "poin": 0, "peserta": set()} for f in FAKULTAS}
    for r in rows:
        if r["fakultas"] in hasil:
            h = hasil[r["fakultas"]]
            h["kg"] += r["berat_kg"]
            h["poin"] += r["poin"]
            h["peserta"].add(r["user_id"])
    return [{"fakultas": h["fakultas"], "kg": round(h["kg"], 2), "poin": h["poin"],
             "peserta": len(h["peserta"])} for h in hasil.values()]


def lewat(fungsi):
    try:
        return jsonify(fungsi(ambil_data()))
    except requests.RequestException:
        return jsonify(error="Service Setoran sedang tidak bisa dihubungi"), 503


@app.get("/health")
def health():
    return jsonify(status="ok", service="laporan")


@app.get("/rekap")
@auth(["petugas"])
def rekap():
    return lewat(rekap_data)


@app.get("/leaderboard")
@auth()
def leaderboard():
    return lewat(leaderboard_data)


@app.get("/fakultas")
@auth()
def fakultas():
    return lewat(fakultas_data)
