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
