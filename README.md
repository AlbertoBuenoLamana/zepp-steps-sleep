# zepp-steps-sleep

Script en Python para extraer datos de actividad, sueño y composición corporal desde los servidores de Huami/Zepp (Xiaomi, Amazfit) sin usar la app oficial.

## Qué hace

- Se autentica en los servidores de Huami usando tu cuenta de Zepp/Amazfit
- Descarga el resumen de actividad diaria de los últimos N días
- Muestra una tabla de **seguimiento físico semanal** con pasos, distancia, calorías, distancia corriendo, sueño, puntuación de sueño, frecuencia cardíaca en reposo y calidad de descanso
- Descarga el historial de **peso y composición corporal** de la báscula Xiaomi (grasa, músculo, agua, hueso, grasa visceral, score)
- También muestra entradas de peso **introducidas manualmente** en la app
- Renueva el token automáticamente si expira
- Guarda los datos crudos en un JSON local

## Requisitos

- Python 3.12+
- Cuenta Zepp/Amazfit con email y contraseña (no Google/Apple login)
- Báscula Xiaomi Mi Body Composition Scale (opcional, para composición corporal)

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

> El token expira en minutos, pero el script lo renueva automáticamente si tienes `ZEPP_EMAIL` y `ZEPP_PASSWORD` en el `.env`.

## Uso

```bash
# Últimos 7 días (por defecto)
venv/bin/python3 zepp_client.py

# Últimos 30 días
venv/bin/python3 zepp_client.py --days 30
```

### Ejemplo de salida

```
════════════════════════════════════════════════════════════════════════
 SEGUIMIENTO SEMANAL DE ACTIVIDAD FÍSICA
════════════════════════════════════════════════════════════════════════
Fecha          Pasos   Dist   Cal   Corr   Sueño  Score   FCR  Desp  Min↑
                         km           km           /100   bpm
────────────────────────────────────────────────────────────────────────
2026-03-23     8,091   6.39   292   4.85  7h 48m     94    56     —     —
2026-03-24     8,765   6.97   304   5.27   6h 6m     73    56     —     —
2026-03-25    10,513   8.40   360   6.38  6h 55m     79    54     —     —
2026-03-26     9,092   7.02   312   5.29  6h 38m     92    56     —     —
2026-03-27    12,347   9.17   360   7.05  6h 28m     87    57     1     3
2026-03-28    18,460  13.42   515  10.20       —      —     —     —     —
2026-03-29     6,936   5.15   220   3.93  8h 58m     73    57     3    62
2026-03-30     4,252   3.32   141   2.48  6h 52m     85    57     —     —
────────────────────────────────────────────────────────────────────────
MEDIA          9,807   7.48   313   5.68   7h 6m   83.3  56.1   2.0  32.5
════════════════════════════════════════════════════════════════════════

════════════════════════════════════════════════════════════════════════
 COMPOSICIÓN CORPORAL (báscula Xiaomi)
════════════════════════════════════════════════════════════════════════
Fecha        Fuente    Peso   BMI  Grasa%  Músculo%  Agua%  Hueso  Visceral  Score
────────────────────────────────────────────────────────────────────────
2026-02-26   manual    89.8  28.7       —         —      —      —         —      —
2026-02-27   manual    90.0  28.7       —         —      —      —         —      —
2026-03-01   manual    89.9  28.7       —         —      —      —         —      —
2019-12-08   báscula   73.2  23.3    20.1      55.5   54.7   2.90         8     88
════════════════════════════════════════════════════════════════════════
```

### Columnas de actividad

| Columna | Descripción |
|---------|-------------|
| Pasos | Total de pasos del día |
| Dist km | Distancia total andada/corrida |
| Cal | Calorías quemadas |
| Corr km | Distancia solo corriendo |
| Sueño | Horas dormidas (inicio → fin) |
| Score /100 | Puntuación de sueño del reloj |
| FCR bpm | Frecuencia cardíaca en reposo (baja = mejor forma) |
| Desp | Veces que te despertaste |
| Min↑ | Minutos despierto durante la noche |

### Columnas de composición corporal

| Columna | Descripción |
|---------|-------------|
| Fuente | `báscula` (Xiaomi) o `manual` (introducido en la app) |
| Peso | Peso en kg |
| BMI | Índice de masa corporal |
| Grasa% | Porcentaje de grasa corporal |
| Músculo% | Porcentaje de masa muscular |
| Agua% | Porcentaje de agua corporal |
| Hueso | Masa ósea en kg |
| Visceral | Grasa visceral |
| Score | Puntuación corporal global |

## Notas

- Endpoint europeo por defecto (`api-mifit-de2.huami.com`). Si tu cuenta es de EE.UU., cambia `DATA_URL` a `api-mifit-us.huami.com`.
- El sueño se calcula como la diferencia entre los timestamps de inicio y fin registrados por la pulsera.
- Los datos de composición corporal completa (grasa, músculo, etc.) solo están disponibles al usar la báscula Xiaomi Mi Body Composition Scale; las entradas manuales solo registran peso y BMI.
- El script muestra los últimos 10 registros de peso/composición, independientemente del rango de días de actividad.
