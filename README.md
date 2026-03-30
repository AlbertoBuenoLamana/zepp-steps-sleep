# zepp-steps-sleep

Script en Python para extraer datos de pasos y sueño desde los servidores de Huami/Zepp (Xiaomi, Amazfit) sin usar la app oficial.

## Qué hace

- Se autentica en los servidores de Huami usando tu cuenta de Zepp/Amazfit
- Descarga el resumen de actividad diaria de los últimos N días
- Muestra una tabla con **pasos** y **tiempo dormido** por día
- Renueva el token automáticamente si expira
- Guarda los datos crudos en un JSON local

## Requisitos

- Python 3.12+
- Cuenta Zepp/Amazfit con email y contraseña (no Google/Apple login)

## Instalación

```bash
git clone https://github.com/AlbertoBuenoLamana/zepp-steps-sleep.git
cd zepp-steps-sleep
python3 -m venv venv
venv/bin/pip install huami-token requests
```

## Configuración

Copia `.env.example` a `.env` y rellena tus credenciales:

```bash
cp .env.example .env
```

Obtén tu `app_token` y `user_id` con:

```bash
venv/bin/huami-token --method amazfit --email tu@email.com --password tupassword --no_logout
```

Copia `app_token` y el `user_id` que aparecen en el output al `.env`.

> El token expira en minutos, pero el script lo renueva solo si tienes `ZEPP_EMAIL` y `ZEPP_PASSWORD` en el `.env`.

## Uso

```bash
# Últimos 7 días (por defecto)
venv/bin/python3 zepp_client.py

# Últimos 30 días
venv/bin/python3 zepp_client.py --days 30
```

### Ejemplo de salida

```
══════════════════════════════════════
Fecha             Pasos      Sueño
──────────────────────────────────────
2026-03-23        8,091     7h 48m
2026-03-24        8,765      6h 6m
2026-03-25       10,513     6h 55m
2026-03-26        9,092     6h 38m
2026-03-27       12,347     6h 28m
2026-03-28       18,460          —
2026-03-29        6,936     8h 58m
2026-03-30        4,252     6h 52m
══════════════════════════════════════
```

Los datos crudos se guardan en `zepp_activity_FECHA_FECHA.json` para procesado posterior.

## Notas

- Endpoint europeo por defecto (`api-mifit-de2.huami.com`). Si tu cuenta es de EE.UU., cambia `DATA_URL` a `api-mifit-us.huami.com`.
- El sueño se calcula como la diferencia entre el timestamp de inicio y fin del sueño registrado por la pulsera.
- El campo `—` en sueño indica que la pulsera no registró datos de sueño ese día.
