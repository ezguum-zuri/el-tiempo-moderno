"""Descarga los avisos de AEMET (vía MeteoAlarm) y guarda solo los vigentes en avisos.json.

Lo ejecuta GitHub Actions cada 20 minutos. La página lee avisos.json desde el propio
repositorio, porque el navegador no puede pedir los avisos directamente a MeteoAlarm.
"""
import json, sys, urllib.request
from datetime import datetime, timezone

URL = "https://feeds.meteoalarm.org/api/v1/warnings/feeds-spain"

def parse(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None

def main(out="avisos.json"):
    req = urllib.request.Request(URL, headers={"User-Agent": "isla-del-tiempo (GitHub Actions)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    now = datetime.now(timezone.utc)
    seen, res = set(), []
    for w in data.get("warnings", []):
        a = w.get("alert") or {}
        if a.get("msgType") == "Cancel":
            continue
        infos = a.get("info") or []
        info = next((i for i in infos if str(i.get("language", "")).lower().startswith("es")), infos[0] if infos else None)
        if not info:
            continue
        lv = 0
        for p in info.get("parameter") or []:
            if p.get("valueName") == "awareness_level":
                try: lv = int(str(p.get("value")).split(";")[0])
                except Exception: lv = 0
        if lv < 2:
            continue
        ex = parse(info.get("expires"))
        if not ex or ex < now:
            continue
        title = str(info.get("headline") or info.get("event") or "Aviso").split(". ")[0]
        onset = info.get("onset") or info.get("effective")
        for ar in info.get("area") or []:
            zone = ar.get("areaDesc") or ""
            key = (zone, title, onset)
            if key in seen:
                continue
            seen.add(key)
            res.append({"level": lv, "title": title, "zone": zone, "desc": info.get("description") or "",
                        "onset": onset, "expires": info.get("expires")})
    res.sort(key=lambda x: (-x["level"], x["onset"] or ""))
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"source": "AEMET vía MeteoAlarm", "updated": now.isoformat(timespec="seconds"), "warnings": res},
                  f, ensure_ascii=False, indent=0)
    print(f"{len(res)} avisos vigentes")

if __name__ == "__main__":
    main(*sys.argv[1:])
