#!/usr/bin/env python3
"""
Regenera el array SESSIONS de index.html a partir del export de Apple Salud.

Uso:
  python3 actualizar_sesiones.py [ruta/al/export.zip] [ruta/a/index.html]

Por defecto busca ~/Downloads/exportar.zip (o export.zip) y el index.html al lado de este script.
Antes de escribir guarda una copia index.html.bak.
"""
import os, re, sys, shutil, zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, date

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
DESDE          = date(2026, 3, 9)     # primera sesión del log
CREATINA_DESDE = date(2026, 3, 13)    # D1
FUENTE         = "Apple Watch"        # ignora duplicados de otras apps (Gentler Streak, etc.)
MIN_DURACION   = 5                    # descarta entrenamientos de menos de N min (arranques por error)
CAMINATA_MIN   = 30                   # caminatas: solo las de N min o más

TIPOS = {
    "FunctionalStrengthTraining":  "funcional",
    "HighIntensityIntervalTraining": "intervalos",
    "TraditionalStrengthTraining": "maquinas",
    "Walking":                     "caminata",
    "Yoga":                        "yoga",
}

# Puntaje de esfuerzo del Watch (1-10) -> etiqueta del log
def esfuerzo(v):
    if v is None: return "—"
    v = round(v)
    if v <= 3: return "Bajo"
    if v <= 5: return "Moderado"
    return {6: "Desafiante", 7: "Duro", 8: "Muy duro", 9: "Extremo"}.get(v, "Máx. esf.")

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# ------------------------------------------------------------
def abrir_xml(zip_path):
    z = zipfile.ZipFile(zip_path)
    for n in z.namelist():
        if re.search(r"apple_health_export/(export|exportar)\.xml$", n):
            return z.open(n)
    sys.exit("No encontré export.xml dentro del zip")

def leer_workouts(fh):
    buf, dentro = [], False
    for raw in fh:
        line = raw.decode("utf-8")
        s = line.lstrip()
        if not dentro:
            if not s.startswith("<Workout "): continue
            buf = [line]
            if line.rstrip().endswith("/>"):
                yield ET.fromstring(line); continue
            dentro = True; continue
        buf.append(line)
        if s.startswith("</Workout>"):
            dentro = False
            yield ET.fromstring("".join(buf))

def parse(w):
    d = {"tipo": w.get("workoutActivityType").replace("HKWorkoutActivityType", ""),
         "inicio": datetime.strptime(w.get("startDate")[:19], "%Y-%m-%d %H:%M:%S"),
         "min": float(w.get("duration") or 0),
         "fuente": w.get("sourceName") or ""}
    for s in w.iter("WorkoutStatistics"):
        t = s.get("type")
        if t.endswith("ActiveEnergyBurned"): d["cal"] = float(s.get("sum"))
        elif t.endswith("IdentifierHeartRate"):
            d["fcP"], d["fcM"] = float(s.get("average")), float(s.get("maximum"))
    for g in w.iter("WorkoutZoneGroup"):
        zonas = list(g.iter("WorkoutZone"))
        if zonas: d["z5"] = float(zonas[-1].get("duration"))   # última zona = Zona 5
    for r in w.iter("Record"):
        if r.get("type") == "HKQuantityTypeIdentifierWorkoutEffortScore":
            d["esf"] = float(r.get("value"))
    return d

def sesiones(zip_path):
    out = []
    for w in leer_workouts(abrir_xml(zip_path)):
        d = parse(w)
        t = TIPOS.get(d["tipo"])
        if not t or FUENTE not in d["fuente"].replace("\xa0", " "): continue
        if d["inicio"].date() < DESDE or d["min"] < MIN_DURACION: continue
        if t == "caminata" and d["min"] < CAMINATA_MIN: continue
        out.append((d, t))
    out.sort(key=lambda x: x[0]["inicio"])
    return out

def a_js(lista):
    filas = []
    for i, (d, t) in enumerate(lista, 1):
        f = d["inicio"].date()
        m = round(d["min"])
        dias = (f - CREATINA_DESDE).days + 1
        z5 = "null" if d.get("z5") is None else str(round(d["z5"]))
        filas.append(
            f'  {{n:{i},f:"{f:%d/%m}",d:"{DIAS[f.weekday()]}",t:"{t}",'
            f'dur:"{m//60}:{m%60:02d}",cal:{round(d.get("cal", 0))},'
            f'fcP:{round(d.get("fcP", 0))},fcM:{round(d.get("fcM", 0))},z5:{z5},'
            f'esf:"{esfuerzo(d.get("esf"))}",cr:"{"Pre" if dias < 1 else f"D{dias}"}"}},')
    return "\n".join(filas)

def main():
    dl = os.path.expanduser("~/Downloads")
    zip_path = sys.argv[1] if len(sys.argv) > 1 else next(
        (os.path.join(dl, n) for n in ("exportar.zip", "export.zip") if os.path.exists(os.path.join(dl, n))), None)
    jsx = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if not zip_path: sys.exit("No encontré el export de Salud en Descargas")

    lista = sesiones(zip_path)
    if not lista: sys.exit("No encontré sesiones; no toco el archivo")
    src = open(jsx, encoding="utf-8").read()
    nuevo, n = re.subn(r"(const SESSIONS = \[\n).*?(\n\];)", lambda m: m.group(1) + a_js(lista) + m.group(2),
                       src, count=1, flags=re.S)
    if not n: sys.exit("No encontré 'const SESSIONS = [' en el archivo")
    shutil.copy(jsx, jsx + ".bak")
    open(jsx, "w", encoding="utf-8").write(nuevo)
    print(f"{len(lista)} sesiones escritas en {jsx} (backup en .bak)")

if __name__ == "__main__":
    main()
