# Report: T00458 local — modo de AN38 + preparación de la corrida

Fecha: 2026-10-31. Pasos 0–5 ejecutados; la corrida completa queda para el usuario (COMANDOS.md).

## Paso 0 — Commit local

`215db3b scripts: fail fast with clear message when API key is missing; add .env.example` — exactamente 4 archivos (.gitignore, .env.example, ambos scripts). Sin push. `git log -3`: 215db3b → bcf2862 → 698e3b2.

## Paso 1 — Modo de la corrida AN38 n=400

**Conclusión: AN38 n=400 corrió en modo default (wrapper), no --raw-prompt.**

Evidencia:
- `cheatsheets/cheat_sheet_variant_AN38.txt` **no contiene** `{{ equation1 }}`/`{{ equation2 }}` (verificado por lectura del archivo completo, 34 líneas). En modo raw (`eval_pipeline_together.py:430-431`) el `replace` sería no-op y el modelo recibiría **cero ecuaciones** — imposible con 71.8% de accuracy y razonamientos que citan las ecuaciones concretas.
- Muestreo seed 42 (20 problemas por JSON): AN38 = 9/20 mencionan eq1 literal en reasoning/proof/counterexample; AN45c = 7/20 (no discriminatorio por sí solo, pero confirma que las ecuaciones sí estaban en el prompt de AN38).
- `tokens_in` (mediana): AN38 = 756. Estimación de caracteres del prompt: wrapped ≈ 2,223 chars vs raw ≈ 1,758 chars. El observado es compatible con wrapped (chars/≈3) e incompatible con raw. AN45c: mediana 766, raw ≈ 2,252 chars (consistente) vs wrapped ≈ 2,694 chars.
- Filename: `AN45c_rawprompt_…` lleva la marca; `AN38_gptoss_hard3_full_…` no.
- Paper: `paper-sair-v16.tex:530-532` reserva "(corrected pipeline `--raw-prompt`)" para el resultado primario (AN45c); L431 "AN45c uses a self-contained template".

**Implicación (solo hallazgo, sin interpretación):** la comparación local n=400 AN38-vs-AN45c se hizo con dos construcciones de prompt distintas: AN38 = wrapper del pipeline (rol + ecuaciones inline + cuerpo + formato del wrapper) y AN45c = cheatsheet autocontenido con placeholders sustituidos.

## Paso 2 — Cheatsheet T00458 reconstruido

`fase1/t00458-local/T00458_cheatsheet.txt` = líneas 1–15 de `cheat_sheet_variant_AN45c.txt` (header de plantilla, incl. `Equation 1: {{ equation1 }}` / `Equation 2: {{ equation2 }}` y el bloque VERDICT/REASONING/PROOF/COUNTEREXAMPLE, más la línea en blanco que sigue) + `cheat_sheet_variant_AN38.txt` completo, sin newline final.

- `wc -c` = **2,242 bytes exactos** ✓
- Normalizado (colapso de espacios, sin línea vacía inicial ni newline final): **idéntico** a `fase1/submission-check/submitted_cheatsheet.txt` (la copia de la pestaña Cheatsheet del leaderboard).

## Paso 3 — Invocación reconstruida (sin ejecutar)

De `metrics` de `results/AN45c_rawprompt_gptoss_hard3_gpt-oss-120b_20260414_000546.json` y del argparse:
`--cheatsheet <file> --problems hard3 --model openai/gpt-oss-120b --raw-prompt` (provider Together; temperature 0, top_p 1, seed 42 fijos en payload `eval_pipeline_together.py:200-206`; `--delay` default 0.5; `--name` original `AN45c_rawprompt_gptoss_hard3`).

Verificación por lectura de código: con `--raw-prompt`, `evaluate_problem` (L430-431) hace `cheatsheet.replace("{{ equation1 }}", eq1).replace("{{ equation2 }}", eq2)` y lo envía como prompt completo. El archivo T00458 contiene `Equation 1: {{ equation1 }}` / `Equation 2: {{ equation2 }}` en su header → las ecuaciones sí se sustituyen.

Prompt de ejemplo construido con el mismo código (E1=`x = y * (x * z)`, E2=`x * y = y * x`): impreso en sesión — header con ecuaciones sustituidas, seguido del cuerpo AN38 (CE search → singleton → decision). `placeholders remaining: 0`.

**Discrepancia encontrada:** el script commiteado fija `max_tokens=8192` para no-Gemma (`eval_pipeline_together.py:199`), pero `paper-sair-v16.tex:397` dice "`max_tokens` is set to 4,096 for gpt-oss-120b". La corrida real de abril pudo usar 4,096 — NO VERIFICADO (los JSON no guardan max_tokens). Los COMANDOS usan el script tal cual (8,192).

Otra nota: `save_results` (`eval_pipeline_together.py:593-596`) escribe siempre en `results/`; los COMANDOS mueven el JSON producido a `fase1/t00458-local/` después.

## Paso 4 — COMANDOS.md

Ver `fase1/t00458-local/COMANDOS.md` (impreso abajo): chequeo de llave sin valor, smoke 5 problemas, corrida n=400 con `--budget 5` (tope), y comando de análisis. Costo estimado ~$2 (referencia: AN45c n=400 costó $2.13, `metrics.total_cost_usd`).

## Paso 5 — analyze.py + control

`fase1/t00458-local/analyze.py` (stdlib): accuracy, T/F recall, F1(TRUE), parse rate, Wilson 95%, chequeo de IDs idénticos, McNemar pareado con corrección de continuidad (mismo método que `scripts/mcnemar_an45c_an38.py:197-206`: χ²=(|b−c|−1)²/(b+c), p=erfc(√(χ²/2)); binomial exacta si b+c<25).

Control ejecutado con los JSON existentes:

```
ID sets AN38 vs AN45c identical: True

AN45c vs AN38 (n=400 paired problems)
  2x2: both correct=256  only AN45c=61  only AN38=31  both wrong=52
  b=61  c=31  chi2=9.1413  p=0.00249903  [chi-square(1 df), continuity-corrected]
```

Reproduce exactamente b=61, c=31, χ²=9.14, p=0.0025 (paper, `paper-sair-v16.tex:175-176`).

## Tabla resumen (pre-corrida)

| variante | construcción de prompt | accuracy | Wilson 95% | T recall | F recall |
|---|---|---|---|---|---|
| baseline | wrapper sin cheatsheet | 59.75% (239/400) | [54.9, 64.4] | 82.6% | 38.0% |
| AN38 | wrapper + cuerpo AN38, ecuaciones inline | 71.75% (287/400) | [67.2, 75.9] | 78.5% | 65.4% |
| AN45c | raw-prompt autocontenido | 79.25% (317/400) | [75.0, 82.9] | 95.9% | 63.4% |
| T00458 | raw-prompt (header AN45c + cuerpo AN38) | pendiente corrida | — | — | — |

## NO VERIFICADO

1. **max_tokens real de la corrida AN45c/AN38 de abril**: script commiteado = 8,192; paper dice 4,096 para gpt-oss (L397). Los JSON no registran el valor.
2. **Versión exacta del script el día de cada corrida** (anterior al primer commit 2026-04-15): el código commiteado es idéntico desde entonces, pero la corrida AN38 (04-04) es previa al commit.
3. **Que T00458_cheatsheet.txt sea byte-exacto al enviado a la plataforma**: normalizado idéntico a la copia web; la web pudo alterar espacios. El raw de la plataforma no está disponible.
4. **Disponibilidad del dataset HF** (`SAIRfoundation/equational-theories-selected-problems`, config hard3): si falla, el script usa 10 problemas de ejemplo (L84-86) — el usuario debe verificar el log `[OK] Cargados 400 problemas (hard3)`.
5. **Si el modelo `openai/gpt-oss-120b` en Together sigue disponible con ese nombre** (puede haber rotación de catálogo).

---

## Apéndice (pre-corrida): tope de tokens de abril + fallback del dataset

### 1. Distribución de `tokens_out` por problema (corridas n=400 existentes)

| corrida | max | p99 | p95 | ==4096 | ==8192 | >4096 |
|---|---|---|---|---|---|---|
| AN38 n=400 | 4,096 | 4,096 | 4,096 | **268/400** | 0 | 0 |
| AN45c rawprompt n=400 | 8,192 | 8,192 | 8,192 | 0 | **25/400** | **226/400** |
| baseline n=400 | 8,192 | 8,192 | 7,403 | 0 | **12/400** | **168/400** |

- `finish_reason` no se guarda en los JSON (todas las respuestas tienen `predicted` TRUE/FALSE; 0 no parseadas en las tres corridas). Las respuestas en el tope (268/25/12) no se pueden confirmar como truncadas — no hay campo de finish reason.
- **Conclusión: el tope de abril NO fue único.** AN38 corrió con max_tokens=4,096 (coincide con `paper-sair-v16.tex:397`: "max_tokens is set to 4,096 for gpt-oss-120b"), mientras AN45c-rawprompt y baseline corrieron con 8,192. Para T00458 con "la misma configuración que la corrida AN45c", el valor correcto es **8,192** — que es exactamente lo que envía hoy el script (`eval_pipeline_together.py:199`: `mt = 2048 if "gemma" in model.lower() else 8192`).
- ¿Argumento para max_tokens?: **no existe** en el argparse (L654-676: cheatsheet, problems, model, max, skip, name, delay, skip-test, budget, raw-prompt). Tampoco hay parámetro de reasoning — el script solo *lee* `message.reasoning` de la respuesta (L164-165), no envía nada de reasoning effort.

### 2. Fallback del dataset (lectura de código)

- Éxito: `print(f"[OK] Cargados {len(problems)} problemas ({split})")` → en el log esperado: `[OK] Cargados 400 problemas (hard3)` (`eval_pipeline_together.py:82`).
- Fallo HF: `print(f"[WARN] HuggingFace no disponible: {e}")` seguido de `print("[INFO] Usando 10 problemas de ejemplo...")` (L84-86) → evaluaría solo 10 problemas sintéticos. Los greps de COMANDOS.md chequean la línea de éxito y `n_total` en el JSON.

### 3. Cambios aplicados a COMANDOS.md y analyze.py

- COMANDOS.md: nota al inicio sobre max_tokens (8192 ya coincide con la corrida AN45c; sin flag disponible), bloque nuevo "Control de drift: AN45c re-run n=400" (misma invocación de abril, `--name AN45c_rerun_gptoss_hard3`, log `rerun_an45c.log`, mv a `AN45c_rerun_gptoss_hard3_full.json`), y grep de verificación del dataset + `n_total` al final de cada bloque.
- analyze.py: si existe `fase1/t00458-local/AN45c_rerun_gptoss_hard3_full.json`, añade accuracy+Wilson del re-run, McNemar AN45c-abril vs AN45c-rerun (control de drift) y McNemar T00458 vs AN45c-rerun.

---

# Corrida local (2026-11-01): T00458 n=400 + re-run AN45c n=400

Ejecutado en una VM de Devin, rama `work/t00458-local`, intérprete `/usr/bin/python3` (Python 3.10.12) para todo. Los comandos son los de COMANDOS.md, sustituyendo `/usr/local/bin/python3` por `/usr/bin/python3`. Diferencias de invocación: en el bloque 2 la salida se redirigió con `> run.log 2>&1` en lugar de `2>&1 | tee run.log`, y en el bloque 3 se usó `2>&1 | tee rerun_an45c.log > /dev/null`. En ambos casos el log tiene el mismo contenido; solo no se imprimió en pantalla.

## Paso A — Preparación

- `git log --oneline -3`: `0c4580b` → `215db3b` → `bcf2862`.
- Dependencias instaladas: requests, python-dotenv, datasets.
- Llave: la comprobación imprimió "definida, longitud 50". La llave original (longitud 64) devolvía 401 "Invalid API key provided"; el usuario la revocó, cargó una nueva y confirmó que longitud 50 es correcto.
- `T00458_cheatsheet.txt`: `wc -c` = 2242 bytes; contiene `{{ equation1 }}` (1 vez) y `{{ equation2 }}` (1 vez).

## Paso B — Smoke test (5 problemas)

- `smoke.log`: contiene `[OK] Cargados 400 problemas (hard3)` (1 vez); `[INFO] Usando 10 problemas de ejemplo` aparece 0 veces.
- `smoke_5.json`: n_total = 5. Las 5 respuestas tienen predicted TRUE o FALSE (4/5 correctas; los 5 problemas tienen label TRUE). Costo: $0.024624.
- Prompt reconstruido para hard3_0001 con el mismo código del script (`cheatsheet.replace("{{ equation1 }}", eq1).replace("{{ equation2 }}", eq2)`): `Equation 1: x = y * x` y `Equation 2: x = x * (x * ((y * z) * x))`, coincidentes con eq1 y eq2 del JSON. Placeholders restantes: 0.

## Pasos C y D — Corridas completas

| corrida | log | `[OK] Cargados 400 problemas` | JSON | n_total |
|---|---|---|---|---|
| T00458 | run.log | sí (1) | T00458_rawprompt_gptoss_hard3_full.json | 400 |
| AN45c re-run | rerun_an45c.log | sí (1) | AN45c_rerun_gptoss_hard3_full.json | 400 |

Ninguna corrida se lanzó dos veces. `budget_exceeded` = False en las dos.

## Paso E — Artefactos (las 5 corridas n=400)

| corrida | n_total | provider | model | size_bytes | parseadas | no parseadas | costo (script, USD) | minutos |
|---|---|---|---|---|---|---|---|---|
| baseline abril | 400 | together | openai/gpt-oss-120b | 0 | 400 | 0 | 1.666349 | 359.9 |
| AN38 abril | 400 | together | openai/gpt-oss-120b | 1776 | 400 | 0 | 1.750772 | 258.6 |
| AN45c abril | 400 | together | openai/gpt-oss-120b | 2252 | 400 | 0 | 2.129656 | 314.7 |
| AN45c re-run | 400 | together | openai/gpt-oss-120b | 2252 | 400 | 0 | 2.200161 | 243.1 |
| T00458 | 400 | together | openai/gpt-oss-120b | 2242 | 400 | 0 | 2.407314 | 240.6 |

Los conjuntos de IDs de problema son idénticos en las 5 corridas (True).

## Paso F — Tokens de salida (`tokens_out`)

| corrida | max | p99 | p95 | ==4096 | ==8192 |
|---|---|---|---|---|---|
| baseline abril | 8,192 | 8,192 | 7,358 | 0 | 12 |
| AN38 abril | 4,096 | 4,096 | 4,096 | 268 | 0 |
| AN45c abril | 8,192 | 8,192 | 8,192 | 0 | 25 |
| AN45c re-run | 8,192 | 8,192 | 8,192 | 0 | 29 |
| T00458 | 8,192 | 8,192 | 8,192 | 0 | 42 |

Percentiles por rango más cercano (`supplement.py`). El p95 de baseline aquí es 7,358 y en el apéndice pre-corrida es 7,403; la diferencia se atribuye al método de percentil (NO VERIFICADO).

## Paso G — Análisis

Comandos: `analyze.py --t00458 fase1/t00458-local/T00458_rawprompt_gptoss_hard3_full.json` y `supplement.py`. Este último es un script auxiliar nuevo, solo stdlib, que reutiliza `wilson`/`mcnemar`/`load` de analyze.py y cubre las 5 corridas y los 5 pares de McNemar. Las cifras de T00458 y de AN45c re-run coinciden entre los dos scripts.

### a) Métricas

| corrida | accuracy | Wilson 95% | TRUE recall | FALSE recall | F1(TRUE) | parse rate |
|---|---|---|---|---|---|---|
| baseline abril | 59.75% (239/400) | [54.87, 64.44] | 82.56% (161/195) | 38.05% (78/205) | 0.6667 | 400/400 |
| AN38 abril | 71.75% (287/400) | [67.15, 75.94] | 78.46% (153/195) | 65.37% (134/205) | 0.7303 | 400/400 |
| AN45c abril | 79.25% (317/400) | [75.01, 82.94] | 95.90% (187/195) | 63.41% (130/205) | 0.8184 | 400/400 |
| AN45c re-run | 79.50% (318/400) | [75.27, 83.17] | 98.46% (192/195) | 61.46% (126/205) | 0.8240 | 400/400 |
| T00458 | 82.50% (330/400) | [78.47, 85.91] | 95.90% (187/195) | 69.76% (143/205) | 0.8423 | 400/400 |

### b) McNemar pareado con corrección de continuidad (χ² con 1 gl; b+c ≥ 25 en todos los pares)

b = solo A correcto, c = solo B correcto.

| # | A vs B | ambos ✓ | b | c | ambos ✗ | χ² | p |
|---|---|---|---|---|---|---|---|
| 1 | AN45c abril vs AN38 abril (control) | 256 | 61 | 31 | 52 | 9.1413 | 0.00249903 |
| 2 | AN45c abril vs AN45c re-run | 298 | 19 | 20 | 63 | 0.0000 | 1 |
| 3 | T00458 vs AN45c re-run | 302 | 28 | 16 | 54 | 2.7500 | 0.0972544 |
| 4 | T00458 vs AN45c abril | 298 | 32 | 19 | 51 | 2.8235 | 0.0928919 |
| 5 | T00458 vs AN38 abril | 263 | 67 | 24 | 46 | 19.3846 | 1.06864e-05 |

El control (1) reproduce b=61, c=31, p=0.0025.

### c) Costo y duración

| corrida | costo (script, USD) | duración (min) | tokens in / out | reintentos por respuesta vacía (`[EMPTY]`) |
|---|---|---|---|---|
| smoke T00458 (n=5) | 0.024624 | 2.9 | 3,783 / 20,841 | 1 |
| T00458 (n=400) | 2.407314 | 240.6 | 305,180 / 2,102,134 | 37 |
| AN45c re-run (n=400) | 2.200161 | 243.1 | 306,780 / 1,893,381 | 33 |
| **total sesión** | **4.632099** | 486.6 | | 71 |

## Tabla resumen

| variante | construcción de prompt | max_tokens | fecha | accuracy | Wilson 95% | T recall | F recall |
|---|---|---|---|---|---|---|---|
| baseline | wrapper sin cheatsheet | 8,192 (inferido de tokens_out) | 2026-04-14 | 59.75% (239/400) | [54.9, 64.4] | 82.6% | 38.0% |
| AN38 abril | wrapper + cuerpo AN38, ecuaciones inline | 4,096 (inferido de tokens_out) | 2026-04-04 | 71.75% (287/400) | [67.2, 75.9] | 78.5% | 65.4% |
| AN45c abril | raw autocontenido | 8,192 (inferido de tokens_out) | 2026-04-14 | 79.25% (317/400) | [75.0, 82.9] | 95.9% | 63.4% |
| AN45c re-run | raw autocontenido | 8,192 (script L199) | 2026-11-01 | 79.50% (318/400) | [75.3, 83.2] | 98.5% | 61.5% |
| T00458 | raw (plantilla + cuerpo AN38) | 8,192 (script L199) | 2026-11-01 | 82.50% (330/400) | [78.5, 85.9] | 95.9% | 69.8% |

Fechas de abril tomadas del timestamp en el nombre de cada JSON; fechas de noviembre tomadas de `metrics.timestamp`.

## NO VERIFICADO (corrida local)

1. **Costo realmente facturado.** `openai/gpt-oss-120b` no está en `MODEL_PRICING`, así que el script usa el default de $1.00/M tokens tanto de entrada como de salida (L61-62). Además, cuando hay un reintento por `[EMPTY]` (contenido vacío con `finish_reason: length` en el intento descartado, según el `[DEBUG]` del log), el costo del intento descartado no se suma. Con la misma tarifa default, los 71 reintentos añadirían como mucho unos $0.64 (≤ 71 × ~8,950 tokens), para un acumulado de ≤ ~$5.27, por debajo del tope de $6.
2. **Truncamiento** de las respuestas con exactamente 8,192 tokens: los JSON no guardan `finish_reason`.
3. **max_tokens de las corridas de abril:** inferido del máximo de `tokens_out`; los JSON no lo registran.
4. **Determinismo del proveedor:** temperature 0 y seed 42 se envían, pero no se verificó que Together garantice salidas idénticas.
5. **Llamadas no pedidas por el prompt:** se hicieron 2 llamadas GET `/v1/models` (sin costo) para diagnosticar la llave original, que devolvió 401, y validar la nueva, que devolvió 200.
