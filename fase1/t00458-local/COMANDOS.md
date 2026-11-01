# Comandos para correr T00458 localmente (Together, hard3 n=400)

Ejecutar desde la raíz del repo (`/Users/manuelcazares/Downloads/sair-prompt-engineering`),
con `/usr/local/bin/python3`. `TOGETHER_API_KEY` debe estar exportada en la sesión.
El script escribe el JSON de salida siempre en `results/` (ruta hardcodeada en
`save_results`, `scripts/eval_pipeline_together.py:593-596`); por eso cada bloque
termina moviendo el archivo a `fase1/t00458-local/`.

**Verificación del dataset en el log:** buscar la línea
`[OK] Cargados 400 problemas (hard3)`. Si aparece
`[WARN] HuggingFace no disponible:` o `[INFO] Usando 10 problemas de ejemplo...`,
detener — estarías evaluando el fallback de 10 problemas.

**Nota max_tokens:** la corrida AN45c de abril usó 8,192 (medido por `tokens_out`
en su JSON; el script actual ya envía 8,192 para no-Gemma, `eval_pipeline_together.py:199`).
La corrida AN38 de abril usó 4,096. El script **no** tiene argumento para fijar
max_tokens ni parámetro de reasoning; como 8,192 coincide con la corrida AN45c,
no hace falta tocar nada.

## 0) Comprobación de la llave (sin mostrar su valor)

```bash
/usr/local/bin/python3 -c "import os;print('definida, longitud', len(os.environ['TOGETHER_API_KEY'])) if 'TOGETHER_API_KEY' in os.environ else print('no definida')"
```

Esperado: `definida, longitud 64`. Si imprime `no definida`, exportar primero y no continuar.

## 1) Smoke test — 5 problemas

```bash
/usr/local/bin/python3 scripts/eval_pipeline_together.py \
  --cheatsheet fase1/t00458-local/T00458_cheatsheet.txt \
  --problems hard3 \
  --model openai/gpt-oss-120b \
  --raw-prompt \
  --max 5 \
  --budget 5 \
  --name T00458_smoke \
  2>&1 | tee fase1/t00458-local/smoke.log
mv results/T00458_smoke_gpt-oss-120b_*.json fase1/t00458-local/smoke_5.json
grep -c "OK] Cargados 400 problemas" fase1/t00458-local/smoke.log
/usr/local/bin/python3 -c "import json,glob; d=json.load(open(glob.glob('fase1/t00458-local/smoke_5.json')[0])); print('n_total:', d['metrics']['n_total'])"
```

## 2) Corrida completa — n=400

```bash
/usr/local/bin/python3 scripts/eval_pipeline_together.py \
  --cheatsheet fase1/t00458-local/T00458_cheatsheet.txt \
  --problems hard3 \
  --model openai/gpt-oss-120b \
  --raw-prompt \
  --budget 5 \
  --name T00458_rawprompt_gptoss_hard3 \
  2>&1 | tee fase1/t00458-local/run.log
mv results/T00458_rawprompt_gptoss_hard3_gpt-oss-120b_*.json \
   fase1/t00458-local/T00458_rawprompt_gptoss_hard3_full.json
grep -c "OK] Cargados 400 problemas" fase1/t00458-local/run.log
/usr/local/bin/python3 -c "import json; d=json.load(open('fase1/t00458-local/T00458_rawprompt_gptoss_hard3_full.json')); print('n_total:', d['metrics']['n_total'])"
```

## 3) Control de drift: AN45c re-run n=400

Misma invocación que la corrida AN45c de abril (mismo cheatsheet, --raw-prompt,
hard3, max_tokens 8192 implícito):

```bash
/usr/local/bin/python3 scripts/eval_pipeline_together.py \
  --cheatsheet cheatsheets/cheat_sheet_variant_AN45c.txt \
  --problems hard3 \
  --model openai/gpt-oss-120b \
  --raw-prompt \
  --budget 5 \
  --name AN45c_rerun_gptoss_hard3 \
  2>&1 | tee fase1/t00458-local/rerun_an45c.log
mv results/AN45c_rerun_gptoss_hard3_gpt-oss-120b_*.json \
   fase1/t00458-local/AN45c_rerun_gptoss_hard3_full.json
grep -c "OK] Cargados 400 problemas" fase1/t00458-local/rerun_an45c.log
/usr/local/bin/python3 -c "import json; d=json.load(open('fase1/t00458-local/AN45c_rerun_gptoss_hard3_full.json')); print('n_total:', d['metrics']['n_total'])"
```

## 4) Análisis (después de las corridas)

```bash
/usr/local/bin/python3 fase1/t00458-local/analyze.py \
  --t00458 fase1/t00458-local/T00458_rawprompt_gptoss_hard3_full.json
```

## Notas de invocación (reconstrucción)

- `--problems hard3`: dataset HF `SAIRfoundation/equational-theories-selected-problems`,
  config `hard3`, split `train` (`eval_pipeline_together.py:68-82`); requiere
  paquete `datasets` y acceso a HuggingFace. Requiere `/usr/local/bin/python3`
  (el de homebrew no tiene `requests`/`dotenv`).
- `--model openai/gpt-oss-120b`: coincide con `metrics.model` de la corrida AN45c.
- `--raw-prompt`: filename original `AN45c_rawprompt_…`; sustituye
  `{{ equation1 }}`/`{{ equation2 }}` dentro del cheatsheet (L430-431).
- temperature 0, top_p 1, seed 42: fijos en el payload (L200-206).
- `--delay` default 0.5 s; `--budget 5` para el tope de 5 USD (default del script es 10).
- Estimación: la corrida AN45c costó $2.13; cada corrida aquí debería estar en el
  mismo orden (~$2). Dos corridas completas ≈ $4-5 total. Si la estimación que
  imprime el script supera $5, detener.
