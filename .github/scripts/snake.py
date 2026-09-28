#!/usr/bin/env python3
"""
Generator animasi snake untuk grafik kontribusi GitHub.
Setiap kali snake memakan sel yang punya kontribusi, ekornya bertambah panjang.

Pemakaian:
    GITHUB_TOKEN=xxx python3 snake.py --user elvadsah --out dist/github-snake.svg
    python3 snake.py --demo --out demo.svg        # data acak, untuk uji coba
"""
import argparse
import json
import os
import random
import sys
import urllib.request

# ───────────── PENGATURAN (silakan ubah) ─────────────
CELL = 10                 # ukuran kotak
GAP = 3                   # jarak antar kotak
PAD = 16                  # jarak tepi
BASE_LEN = 4              # panjang awal snake
MAX_LEN = 40              # batas panjang maksimal snake
DT = 0.06                 # detik per langkah (kecil = lebih cepat)
SNAKE_COLOR = "#000000"   # warna badan snake
HEAD_COLOR = "#3b8bff"    # warna kepala snake
LEVELS = ["#ebedf0", "#cfe3ff", "#8ec1ff", "#3b8bff", "#0a54d6"]  # kotak kontribusi
# ──────────────────────────────────────────────────────

STEP = CELL + GAP
LEVEL_MAP = {
    "NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4,
}
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""


def fetch(user, token):
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "snake-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data or not data.get("data", {}).get("user"):
        sys.exit(f"Gagal mengambil data kontribusi: {data.get('errors') or 'user tidak ditemukan'}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [
        [(d["weekday"], d["contributionCount"], LEVEL_MAP.get(d["contributionLevel"], 0))
         for d in w["contributionDays"]]
        for w in weeks
    ]


def demo():
    random.seed(7)
    weeks = []
    for w in range(53):
        start = 3 if w == 0 else 0
        end = 4 if w == 52 else 7
        days = []
        for wd in range(start, end):
            cnt = random.choice([0, 0, 0, 1, 2, 4, 7, 12])
            lvl = 0 if cnt == 0 else min(4, 1 + cnt // 4)
            days.append((wd, cnt, lvl))
        weeks.append(days)
    return weeks


def k(x):
    return f"{x:.5f}".rstrip("0").rstrip(".") or "0"


def build(weeks):
    # Jalur: turun di kolom genap, naik di kolom ganjil (melewati semua sel)
    path = []
    for wi, days in enumerate(weeks):
        days = sorted(days, key=lambda d: d[0])
        if wi % 2 == 1:
            days = days[::-1]
        for wd, cnt, lvl in days:
            path.append((wi, wd, cnt, lvl))

    n = len(path)
    if n == 0:
        sys.exit("Tidak ada data kontribusi.")

    # Panjang snake di setiap langkah: bertambah 1 tiap memakan kontribusi
    lens, eaten = [], 0
    for _, _, cnt, _ in path:
        if cnt > 0:
            eaten += 1
        lens.append(min(BASE_LEN + eaten, MAX_LEN))
    final = lens[-1]

    def length_at(step):
        return lens[min(step, n - 1)]

    total_steps = n + final + 2
    total = total_steps * DT

    width = PAD * 2 + len(weeks) * STEP - GAP
    height = PAD * 2 + 7 * STEP - GAP

    def pos(wi, wd):
        return PAD + wi * STEP, PAD + wd * STEP

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="Snake memakan kontribusi GitHub">',
        "<title>Snake memakan kontribusi</title>",
    ]

    dur = f'dur="{total:.3f}s" repeatCount="indefinite"'

    # 1) Kotak kontribusi (berubah jadi kosong saat dimakan)
    for j, (wi, wd, cnt, lvl) in enumerate(path):
        x, y = pos(wi, wd)
        color = LEVELS[lvl]
        if cnt > 0:
            a = max(j * DT / total, 1e-5)
            out.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}">'
                f'<animate attributeName="fill" values="{color};{LEVELS[0]};{LEVELS[0]}" '
                f'keyTimes="0;{k(a)};1" calcMode="discrete" {dur}/></rect>'
            )
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>')

    # 2) Badan snake: tiap sel tampil sejak kepala tiba sampai ekor meninggalkannya
    for j, (wi, wd, _, _) in enumerate(path):
        x, y = pos(wi, wd)
        step = j
        while step - length_at(step) < j:
            step += 1
        a = max(j * DT / total, 1e-5)
        b = min(step * DT / total, 0.99999)
        out.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{SNAKE_COLOR}" opacity="0">'
            f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="0;{k(a)};{k(b)};1" '
            f'calcMode="discrete" {dur}/></rect>'
        )

    # 3) Kepala snake (berwarna aksen biru)
    for j, (wi, wd, _, _) in enumerate(path):
        x, y = pos(wi, wd)
        a = max(j * DT / total, 1e-5)
        b = min((j + 1) * DT / total, 0.99999)
        out.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="4" fill="{HEAD_COLOR}" opacity="0">'
            f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="0;{k(a)};{k(b)};1" '
            f'calcMode="discrete" {dur}/></rect>'
        )

    out.append("</svg>")
    return "\n".join(out), n, lens, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user")
    ap.add_argument("--out", default="dist/github-snake.svg")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    if args.demo:
        weeks = demo()
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not args.user or not token:
            sys.exit("Butuh --user dan environment variable GITHUB_TOKEN.")
        weeks = fetch(args.user, token)

    svg, n, lens, total = build(weeks)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"OK: {n} sel, panjang snake {lens[0]} -> {lens[-1]}, durasi {total:.1f}s, "
          f"{len(svg) / 1024:.0f} KB -> {args.out}")


if __name__ == "__main__":
    main()
