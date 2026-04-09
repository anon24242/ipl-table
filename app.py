#!/usr/bin/env python3
"""IPL 2026 Points Table - Flask Web Application"""

from flask import Flask, render_template, jsonify, Response
import requests
import json
import re
import csv
import io
from datetime import datetime

app = Flask(__name__)

FEED_BASE = "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/feeds/stats"
COMP_ID = "284"

TEAM_COLORS = {
    "CSK": "#FCCA06", "MI": "#004BA0", "RCB": "#EC1C24", "KKR": "#3A225D",
    "DC": "#0078BC", "SRH": "#F26522", "PBKS": "#D71920", "RR": "#EA1A85",
    "GT": "#1C1C2B", "LSG": "#A72056",
}

TEAM_LOGOS = {
    "CSK": "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/teamlogos/CSK.png",
    "MI": "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/teamlogos/MI.png",
    "RCB": "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/teamlogos/RCB.png",
    "KKR": "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/teamlogos/KKR.png",
    "DC": "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/teamlogos/DC.png",
    "SRH": "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/teamlogos/SRH.png",
    "PBKS": "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/teamlogos/PBKS.png",
    "RR": "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/teamlogos/RR.png",
    "GT": "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/teamlogos/GT.png",
    "LSG": "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/teamlogos/LSG.png",
}

CACHE = {"data": None, "time": 0}
CACHE_TTL = 120


def fetch_standings():
    now = datetime.now().timestamp()
    if CACHE["data"] and (now - CACHE["time"]) < CACHE_TTL:
        return CACHE["data"]

    url = f"{FEED_BASE}/{COMP_ID}-groupstandings.js"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.iplt20.com/",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    text = resp.text.strip()
    match = re.match(r"^ongroupstandings\((.*)\)\s*;?\s*$", text, re.DOTALL)
    if not match:
        raise ValueError("Failed to parse response")
    data = json.loads(match.group(1))
    points = data.get("points", [])
    for t in points:
        code = t.get("TeamCode", "")
        t["color"] = TEAM_COLORS.get(code, "#6B7280")
        t["logo"] = TEAM_LOGOS.get(code, "")
        try:
            nrr = float(t.get("NetRunRate", 0))
            t["nrr_display"] = f"+{t['NetRunRate']}" if nrr > 0 else t["NetRunRate"]
            t["nrr_class"] = "nrr-pos" if nrr > 0 else ("nrr-neg" if nrr < 0 else "")
        except (ValueError, TypeError):
            t["nrr_display"] = t.get("NetRunRate", "0.000")
            t["nrr_class"] = ""
        form_str = t.get("Performance", "")
        form_parts = []
        if form_str:
            for p in form_str.split(","):
                p = p.strip().upper()
                if p == "W":
                    form_parts.append({"label": "W", "cls": "form-w"})
                elif p == "L":
                    form_parts.append({"label": "L", "cls": "form-l"})
                elif p == "NR":
                    form_parts.append({"label": "NR", "cls": "form-nr"})
        t["form_parsed"] = form_parts
        t["pts_class"] = "pts-top" if int(t.get("Points", 0)) >= 4 else ("pts-mid" if int(t.get("Points", 0)) > 0 else "pts-zero")

    CACHE["data"] = points
    CACHE["time"] = now
    return points


@app.route("/")
def index():
    teams = fetch_standings()
    return render_template("index.html", teams=teams, updated=datetime.now().strftime("%d %B %Y, %H:%M:%S"))


@app.route("/api/standings")
def api_standings():
    teams = fetch_standings()
    return jsonify(teams)


@app.route("/api/refresh")
def api_refresh():
    CACHE["data"] = None
    teams = fetch_standings()
    return jsonify({"status": "ok", "teams": teams, "updated": datetime.now().strftime("%d %B %Y, %H:%M:%S")})


@app.route("/download/csv")
def download_csv():
    teams = fetch_standings()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Pos", "Team", "Code", "M", "W", "L", "NR", "NRR", "For", "Against", "Pts", "Form"])
    for t in teams:
        writer.writerow([
            t.get("OrderNo", ""), t.get("TeamName", ""), t.get("TeamCode", ""),
            t.get("Matches", "0"), t.get("Wins", "0"), t.get("Loss", "0"),
            t.get("NoResult", "0"), t.get("NetRunRate", "0"), t.get("ForTeams", ""),
            t.get("AgainstTeam", ""), t.get("Points", "0"), t.get("Performance", ""),
        ])
    output.seek(0)
    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)
    return Response(mem, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=ipl-points-table.csv"})


@app.route("/download/json")
def download_json():
    teams = fetch_standings()
    return Response(
        json.dumps(teams, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=ipl-points-table.json"},
    )


if __name__ == "__main__":
    print("\n  🏏  IPL Points Table App")
    print("  → http://localhost:5000\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
