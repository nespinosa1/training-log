# Training Log

Registro de entrenamientos generado a partir del export de Apple Salud.

- `index.html`: el log. Abrilo directo en el navegador (React + Recharts por CDN, sin build).
- `actualizar_sesiones.py`: regenera el array `SESSIONS` de `index.html` desde el export.

## Actualizar

1. iPhone → Salud → foto de perfil → **Exportar todos los datos de salud**.
2. Dejá el `.zip` en `~/Downloads`.
3. `python3 actualizar_sesiones.py`
