import os
from app import app, rekap_data, leaderboard_data, fakultas_data

DATA = [
    {"user_id": 1, "user_nim": "1", "user_nama": "A", "fakultas": "Bisnis", "jenis": "Kaca", "berat_kg": 2.0, "poin": 80, "bulan": "2026-10"},
    {"user_id": 2, "user_nim": "2", "user_nama": "B", "fakultas": "Informatika", "jenis": "Kaleng/logam", "berat_kg": 1.0, "poin": 150, "bulan": "2026-10"},
]


def test_health():
    assert app.test_client().get("/health").status_code == 200


def test_rekap():
    r = rekap_data(DATA)
    assert r["total_kg"] == 3.0 and r["total_poin"] == 230


def test_leaderboard_urut_poin():
    assert leaderboard_data(DATA)[0]["nama"] == "B"


def test_fakultas():
    f = {x["fakultas"]: x for x in fakultas_data(DATA)}
    assert f["Bisnis"]["poin"] == 80 and f["Informatika"]["peserta"] == 1
