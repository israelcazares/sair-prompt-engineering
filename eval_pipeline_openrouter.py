#!/usr/bin/env python3
"""
SAIR Foundation - Mathematics Distillation Challenge
Pipeline de evaluacion via OpenRouter (multi-modelo)

Requisitos:
  pip install datasets requests numpy scipy python-dotenv --break-system-packages

Configuracion:
  Edita el archivo .env en la misma carpeta:
    OPENROUTER_API_KEY=tu_api_key_aqui
  O exporta la variable de entorno:
    export OPENROUTER_API_KEY="tu_api_key_aqui"

Uso:
  python3 eval_pipeline_openrouter.py --name baseline_qwen_100 --max 100
  python3 eval_pipeline_openrouter.py --cheatsheet cs_v1.txt --name csv1_qwen_100 --max 100
  python3 eval_pipeline_openrouter.py --model meta-llama/llama-3.1-70b-instruct --name baseline_llama_100 --max 100
  python3 eval_pipeline_openrouter.py --problems hard2 --name baseline_hard2_qwen
"""

import argparse
import json
import os
import re
import time
from pathlib import Path
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()  # carga .env desde el directorio actual (o padres)

# ── CONFIGURACION OPENROUTER ─────────────────────────────────────────────────

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL      = "qwen/qwen-2.5-72b-instruct"

# ── PRICING (USD / 1M tokens) — verify at https://openrouter.ai/models ───────
# Prices last checked 2026-03 — update if OpenRouter changes their rates.
# Note: OpenRouter uses hyphenated slugs (qwen-2.5-*), not qwen2.5-*
MODEL_PRICING = {
    "qwen/qwen-2.5-32b-instruct":             {"input": 0.07,  "output": 0.16},
    "qwen/qwen-2.5-72b-instruct":             {"input": 0.13,  "output": 0.40},
    "mistralai/mixtral-8x7b-instruct":        {"input": 0.24,  "output": 0.24},
    "mistralai/mistral-large":                {"input": 2.00,  "output": 6.00},
    "meta-llama/llama-3.1-70b-instruct":      {"input": 0.35,  "output": 0.40},
    "meta-llama/llama-3.1-405b-instruct":     {"input": 2.70,  "output": 2.70},
    "meta-llama/llama-3.3-70b-instruct":      {"input": 0.12,  "output": 0.30},
    "openai/gpt-4o-mini":                     {"input": 0.15,  "output": 0.60},
    "openai/gpt-4o":                          {"input": 2.50,  "output": 10.00},
    "openai/gpt-oss-120b":                    {"input": 1.60,  "output": 1.60},
    "google/gemini-flash-1.5":                {"input": 0.075, "output": 0.30},
    "anthropic/claude-3.5-sonnet":            {"input": 3.00,  "output": 15.00},
}
DEFAULT_PRICE_INPUT  = 0.50   # fallback input  price per 1M tokens
DEFAULT_PRICE_OUTPUT = 1.50   # fallback output price per 1M tokens
DEFAULT_BUDGET_USD   = 10.0   # default hard stop (USD)


# ── 1. CARGA DE PROBLEMAS ────────────────────────────────────────────────────

def load_problems(split="normal"):
    try:
        from datasets import load_dataset
        ds = load_dataset(
            "SAIRfoundation/equational-theories-selected-problems",
            name=split,
            split="train"
        )
        problems = []
        for row in ds:
            problems.append({
                "id":    row.get("id", ""),
                "eq1":   row["equation1"],
                "eq2":   row["equation2"],
                "label": "TRUE" if row["answer"] else "FALSE",
            })
        print(f"[OK] Cargados {len(problems)} problemas ({split})")
        return problems
    except Exception as e:
        print(f"[WARN] HuggingFace no disponible: {e}")
        print("[INFO] Usando 10 problemas de ejemplo...")
        return _sample_problems()


def _sample_problems():
    return [
        {"id": "s0", "eq1": "x * y = y * x",
         "eq2": "x * (y * z) = y * (x * z)",    "label": "TRUE"},
        {"id": "s1", "eq1": "x * (y * z) = (x * y) * z",
         "eq2": "x * y = y * x",                 "label": "FALSE"},
        {"id": "s2", "eq1": "x * x = x",
         "eq2": "x * (x * y) = x",               "label": "TRUE"},
        {"id": "s3", "eq1": "x * y = x",
         "eq2": "x * (y * z) = x",               "label": "TRUE"},
        {"id": "s4", "eq1": "x * y = y",
         "eq2": "x * y = x",                     "label": "FALSE"},
        {"id": "s5", "eq1": "x * (y * z) = (x * y) * z",
         "eq2": "x * x = x",                     "label": "FALSE"},
        {"id": "s6", "eq1": "x * y = y * x",
         "eq2": "x * x = x",                     "label": "FALSE"},
        {"id": "s7", "eq1": "x * (x * y) = x",
         "eq2": "x * x = x",                     "label": "TRUE"},
        {"id": "s8", "eq1": "x * y = x",
         "eq2": "x * y = y * x",                 "label": "FALSE"},
        {"id": "s9", "eq1": "(x * y) * z = x * (y * z)",
         "eq2": "x * (y * z) = y * (x * z)",     "label": "FALSE"},
    ]


# ── 2. PROMPT OFICIAL JINJA2 ─────────────────────────────────────────────────

def build_prompt(eq1, eq2, cheatsheet=""):
    cs_block = ("\n" + cheatsheet.strip() + "\n") if cheatsheet.strip() else ""
    return (
        "You are a mathematician specializing in equational theories of magmas.\n"
        f"Your task is to determine whether Equation 1 ({eq1}) "
        f"implies Equation 2 ({eq2}) over all magmas."
        f"{cs_block}\n"
        "Output format (use exact headers without any additional text or formatting):\n"
        "VERDICT: must be exactly TRUE or FALSE (in the same line).\n"
        "REASONING: must be non-empty.\n"
        "PROOF: required if VERDICT is TRUE, empty otherwise.\n"
        "COUNTEREXAMPLE: required if VERDICT is FALSE, empty otherwise."
    )


# ── 3. LLAMADA A OPENROUTER ──────────────────────────────────────────────────

def call_model(prompt, model=DEFAULT_MODEL, timeout=180, retries=5):
    """
    Llama a OpenRouter via OpenAI-compatible API.

    Endpoint: https://openrouter.ai/api/v1/chat/completions
    (OpenRouter uses this standard path — a 404 response means the MODEL was
    not found or is unavailable, not the endpoint itself.  The error detail is
    always in the JSON body, so we parse it before raising.)

    Retry strategy:
      - 429 / 5xx  → exponential backoff (5 → 10 → 20 → 40 → 60 s max)
      - 404        → fatal (wrong/unavailable model) — no retry
      - 401 / 403  → fatal (bad API key) — no retry
      - timeout    → retry with backoff
      - empty body → retry with backoff
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "local-eval",
        "X-Title":       "sair-eval",
    }
    payload = {
        "model":       model,
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens":  1024,
    }

    for attempt in range(retries):
        try:
            r = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )

            # ── Parse body first (OpenRouter puts error detail in JSON, even on 4xx) ──
            try:
                data = r.json()
            except ValueError:
                data = {}

            # ── Surface any embedded error object before checking HTTP status ─────
            # OpenRouter wraps errors as: {"error": {"code": 404, "message": "..."}}
            if "error" in data:
                err      = data["error"]
                err_code = err.get("code") if isinstance(err, dict) else None
                err_msg  = err.get("message", str(err)) if isinstance(err, dict) else str(err)

                # 404 = model not found / no endpoints — fatal, no retry
                if err_code == 404 or r.status_code == 404:
                    print(f"  [404] Modelo no encontrado en OpenRouter: {err_msg}")
                    print(f"  Verifica que '{model}' existe en https://openrouter.ai/models")
                    return {"text": f"ERROR 404: {err_msg}", "usage": {}}

                # 401 / 403 = bad key — fatal
                if r.status_code in (401, 403):
                    print(f"  [AUTH ERROR {r.status_code}] {err_msg}")
                    return {"text": f"ERROR {r.status_code}: {err_msg}", "usage": {}}

                # 429 = rate limit — retry
                if r.status_code == 429 or err_code == 429:
                    retry_after = r.headers.get("Retry-After")
                    wait = int(retry_after) if retry_after else min(5 * (2 ** attempt), 60)
                    print(f"  [RATE LIMIT] esperando {wait}s... (intento {attempt+1}/{retries})")
                    time.sleep(wait)
                    continue

                # Other embedded errors — treat as fatal
                print(f"  [API ERROR {r.status_code}] {err_msg}")
                return {"text": f"ERROR: {err_msg}", "usage": {}}

            # ── Now raise for any remaining HTTP errors (no JSON error body) ──────
            if not r.ok:
                print(f"  [HTTP {r.status_code}] {r.text[:200]}")
                if r.status_code in (500, 502, 503, 504) and attempt < retries - 1:
                    wait = min(5 * (2 ** attempt), 60)
                    print(f"  [SERVER ERROR] reintentando en {wait}s...")
                    time.sleep(wait)
                    continue
                return {"text": f"ERROR HTTP {r.status_code}", "usage": {}}

            # ── Safe extraction of content ────────────────────────────────────────
            choices  = data.get("choices") or []
            message  = (choices[0].get("message") or {}) if choices else {}
            content  = message.get("content") or ""

            if not content.strip():
                if attempt < retries - 1:
                    wait = min(5 * (2 ** attempt), 60)
                    print(f"  [EMPTY] respuesta vacia, reintentando en {wait}s...")
                    time.sleep(wait)
                    continue
                return {"text": "ERROR: empty response", "usage": {}}

            usage = data.get("usage") or {}
            return {"text": content, "usage": usage}

        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                wait = min(5 * (2 ** attempt), 60)
                print(f"  [TIMEOUT] intento {attempt+1}/{retries}, reintentando en {wait}s...")
                time.sleep(wait)
            else:
                return {"text": "TIMEOUT", "usage": {}}

        except Exception as e:
            return {"text": f"ERROR: {e}", "usage": {}}

    return {"text": "TIMEOUT", "usage": {}}


# ── 4. PARSER ────────────────────────────────────────────────────────────────

def parse_response(text):
    """
    Parser estructurado para respuestas de instruccion.
    Compatible con todos los modelos disponibles en OpenRouter.
    """
    result = {
        "verdict":        None,
        "reasoning":      "",
        "proof":          "",
        "counterexample": "",
        "had_thinking":   False,
        "raw":            text,
    }

    if not text or text.startswith("TIMEOUT") or text.startswith("ERROR"):
        return result

    # 1) VERDICT estructurado
    m = re.search(r"VERDICT:\s*(TRUE|FALSE)", text, re.IGNORECASE)
    if m:
        result["verdict"] = m.group(1).upper()

    # 2) TRUE/FALSE suelto en ultimas 5 lineas
    if not result["verdict"]:
        for line in reversed(text.strip().split("\n")[-5:]):
            if re.search(r"\bTRUE\b", line, re.IGNORECASE):
                result["verdict"] = "TRUE"
                break
            elif re.search(r"\bFALSE\b", line, re.IGNORECASE):
                result["verdict"] = "FALSE"
                break

    # 3) Lenguaje natural fallback
    if not result["verdict"]:
        t = text.lower()
        true_patterns = [
            r"verdict\s*:?\s*true",    r"implication\s+holds",
            r"implies\s+equation\s+2", r"equation\s+2\s+holds",
            r"indeed\s+implies",       r"thus\s+true",
        ]
        false_patterns = [
            r"verdict\s*:?\s*false",   r"counterexample\s*:.*\S",
            r"does\s+not\s+imply",     r"equation\s+2\s+fails",
            r"implication\s+fails",    r"thus\s+false",
        ]
        for pat in true_patterns:
            if re.search(pat, t):
                result["verdict"] = "TRUE"
                break
        if not result["verdict"]:
            for pat in false_patterns:
                if re.search(pat, t):
                    result["verdict"] = "FALSE"
                    break

    # Extraer secciones
    m = re.search(r"REASONING:\s*(.*?)(?=PROOF:|COUNTEREXAMPLE:|$)",
                  text, re.DOTALL | re.IGNORECASE)
    if m:
        result["reasoning"] = m.group(1).strip()[:300]

    m = re.search(r"PROOF:\s*(.*?)(?=COUNTEREXAMPLE:|$)",
                  text, re.DOTALL | re.IGNORECASE)
    if m:
        result["proof"] = m.group(1).strip()[:300]

    m = re.search(r"COUNTEREXAMPLE:\s*(.*?)$",
                  text, re.DOTALL | re.IGNORECASE)
    if m:
        result["counterexample"] = m.group(1).strip()[:300]

    return result


# ── 4.5. SEGUIMIENTO DE COSTOS ───────────────────────────────────────────────

def _get_pricing(model):
    """Retorna dict con 'input' y 'output' (USD por 1M tokens) para el modelo."""
    return MODEL_PRICING.get(
        model, {"input": DEFAULT_PRICE_INPUT, "output": DEFAULT_PRICE_OUTPUT}
    )


def tokens_to_cost(in_tokens, out_tokens, model):
    """Convierte conteo de tokens a USD."""
    p = _get_pricing(model)
    return (in_tokens * p["input"] + out_tokens * p["output"]) / 1_000_000


def estimate_tokens(prompt_text, response_text=""):
    """Estima tokens cuando la API no los reporta (~4 chars = 1 token)."""
    return round(len(prompt_text) / 4), round(len(response_text) / 4)


def estimate_run_cost(problems, cheatsheet, model=DEFAULT_MODEL):
    """
    Estima el costo total ANTES de iniciar la evaluacion.
    Usa el primer problema como muestra para el largo del prompt.
    """
    p             = _get_pricing(model)
    sample_prompt = build_prompt(problems[0]["eq1"], problems[0]["eq2"], cheatsheet)
    avg_in        = len(sample_prompt) / 4.0   # ~4 chars per token
    avg_out       = 400.0                       # estimacion conservadora
    total_in      = avg_in  * len(problems)
    total_out     = avg_out * len(problems)
    cost_usd      = (total_in * p["input"] + total_out * p["output"]) / 1_000_000
    return {
        "estimated_cost_usd":  round(cost_usd, 4),
        "avg_input_tokens":    round(avg_in),
        "avg_output_tokens":   round(avg_out),
        "total_input_tokens":  round(total_in),
        "total_output_tokens": round(total_out),
        "n_problems":          len(problems),
        "model":               model,
    }


# ── 5. EVALUACION ────────────────────────────────────────────────────────────

def evaluate_cheatsheet(cheatsheet, problems, model=DEFAULT_MODEL,
                        max_problems=None, delay=0.5,
                        budget_usd=DEFAULT_BUDGET_USD):
    if max_problems:
        problems = problems[:max_problems]

    correct = true_correct = false_correct = 0
    true_total = false_total = 0
    results = []

    total_input_tokens  = 0
    total_output_tokens = 0
    total_cost_usd      = 0.0
    budget_exceeded     = False
    tokens_estimated    = 0   # count of calls where usage was estimated

    size_bytes = len(cheatsheet.encode("utf-8"))
    feasible   = size_bytes <= 10240

    print(f"\n[EVAL] {len(problems)} problemas | modelo: {model}")
    print(f"[EVAL] Cheat sheet: {size_bytes} bytes | "
          f"{'FACTIBLE' if feasible else 'INFACTIBLE >10KB'}")
    print(f"[EVAL] API: OpenRouter | Presupuesto: ${budget_usd:.2f} USD")

    start_time = time.time()

    for i, prob in enumerate(problems):
        prompt    = build_prompt(prob["eq1"], prob["eq2"], cheatsheet)
        resp      = call_model(prompt, model)
        raw       = resp["text"]
        usage     = resp["usage"]

        # Use reported usage if available; fall back to character estimation
        if usage.get("prompt_tokens") or usage.get("completion_tokens"):
            in_tok  = usage.get("prompt_tokens", 0)
            out_tok = usage.get("completion_tokens", 0)
        else:
            in_tok, out_tok = estimate_tokens(prompt, raw)
            tokens_estimated += 1

        call_cost            = tokens_to_cost(in_tok, out_tok, model)
        total_input_tokens  += in_tok
        total_output_tokens += out_tok
        total_cost_usd      += call_cost

        parsed    = parse_response(raw)
        predicted = parsed["verdict"]
        actual    = prob["label"].upper()
        is_correct = (predicted == actual)

        if is_correct:
            correct += 1
        if actual == "TRUE":
            true_total += 1
            if is_correct:
                true_correct += 1
        else:
            false_total += 1
            if is_correct:
                false_correct += 1

        results.append({
            "id":             prob["id"],
            "eq1":            prob["eq1"],
            "eq2":            prob["eq2"],
            "label":          actual,
            "predicted":      predicted,
            "correct":        is_correct,
            "had_thinking":   parsed["had_thinking"],
            "reasoning":      parsed["reasoning"],
            "proof":          parsed["proof"],
            "counterexample": parsed["counterexample"],
            "tokens_in":      in_tok,
            "tokens_out":     out_tok,
            "cost_usd":       round(call_cost, 6),
        })

        elapsed   = time.time() - start_time
        avg_sec   = elapsed / (i + 1)
        remaining = avg_sec * (len(problems) - i - 1)
        hrs       = int(remaining // 3600)
        mins      = int((remaining % 3600) // 60)
        acc_now   = correct / (i + 1)
        est_flag  = "~" if tokens_estimated > 0 else ""   # ~ = some tokens estimated

        status = "OK  " if is_correct else "FAIL"
        print(f"  [{i+1:>4}/{len(problems)}] {status} | "
              f"label={actual} pred={str(predicted):<5} | "
              f"acc={acc_now:.2f} | "
              f"{avg_sec:.1f}s/prob | ETA {hrs}h{mins:02d}m | "
              f"{est_flag}${total_cost_usd:.4f} | "
              f"{prob['eq1'][:25]}")

        time.sleep(delay)

        if total_cost_usd >= budget_usd:
            print(f"\n[BUDGET] Limite de ${budget_usd:.2f} USD alcanzado tras "
                  f"{i+1} problemas — deteniendo evaluacion.")
            budget_exceeded = True
            break

    n        = len(results)   # may be < len(problems) when budget is exceeded
    f1       = correct       / n           if n           > 0 else 0.0
    f2_true  = true_correct  / true_total  if true_total  > 0 else 0.0
    f2_false = false_correct / false_total if false_total > 0 else 0.0
    f2       = (f2_true + f2_false) / 2.0

    total_mins = (time.time() - start_time) / 60
    est_note   = f" (~{tokens_estimated} llamadas estimadas)" if tokens_estimated else ""
    print(f"\n[TIME] Completado en {total_mins:.1f} minutos")
    print(f"[COST] Total: ${total_cost_usd:.4f} USD  "
          f"({total_input_tokens:,} tokens in / {total_output_tokens:,} out){est_note}")

    metrics = {
        "f1_accuracy":          f1,
        "f2_coverage":          f2,
        "f2_true_acc":          f2_true,
        "f2_false_acc":         f2_false,
        "f3_neg_size":          -size_bytes,
        "size_bytes":           size_bytes,
        "feasible":             feasible,
        "n_correct":            correct,
        "n_total":              n,
        "n_true_correct":       true_correct,
        "n_true_total":         true_total,
        "n_false_correct":      false_correct,
        "n_false_total":        false_total,
        "model":                model,
        "provider":             "openrouter",
        "timestamp":            datetime.now().isoformat(),
        "total_minutes":        round(total_mins, 1),
        "total_input_tokens":   total_input_tokens,
        "total_output_tokens":  total_output_tokens,
        "total_cost_usd":       round(total_cost_usd, 6),
        "budget_usd":           budget_usd,
        "budget_exceeded":      budget_exceeded,
        "tokens_estimated_calls": tokens_estimated,
    }
    return {"metrics": metrics, "results": results}


# ── 6. GUARDAR Y MOSTRAR ─────────────────────────────────────────────────────

def save_results(eval_result, name, output_dir="results"):
    Path(output_dir).mkdir(exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{output_dir}/{name}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(eval_result, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] {path}")
    return path


def print_metrics(name, m):
    est_note = (f" (~{m.get('tokens_estimated_calls', 0)} estimadas)"
                if m.get("tokens_estimated_calls") else "")
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"  Modelo:      {m['model']} via {m.get('provider','?')}")
    print(f"  Problemas:   {m['n_total']}")
    print(f"  Tiempo:      {m.get('total_minutes','?')} minutos")
    print(f"  f1 accuracy: {m['f1_accuracy']:.4f}  "
          f"({m['n_correct']}/{m['n_total']})")
    print(f"  TRUE  acc:   {m['f2_true_acc']:.4f}  "
          f"({m['n_true_correct']}/{m['n_true_total']})")
    print(f"  FALSE acc:   {m['f2_false_acc']:.4f}  "
          f"({m['n_false_correct']}/{m['n_false_total']})")
    print(f"  Size:        {m['size_bytes']} bytes  "
          f"({'OK' if m['feasible'] else 'INFACTIBLE'})")
    print(f"  Costo total: ${m.get('total_cost_usd', 0):.4f} USD  "
          f"({m.get('total_input_tokens', 0):,} tokens in / "
          f"{m.get('total_output_tokens', 0):,} out){est_note}")
    if m.get("budget_exceeded"):
        print(f"  [WARN] Presupuesto de ${m.get('budget_usd', '?')} USD alcanzado "
              f"— evaluacion incompleta ({m['n_total']} problemas evaluados)")
    print(f"{'='*60}")


# ── 7. VERIFICACION DE API ───────────────────────────────────────────────────

def test_api(model=DEFAULT_MODEL):
    """Verifica que la API key de OpenRouter funciona antes de lanzar evaluacion."""
    print(f"[TEST] Verificando conexion a OpenRouter con modelo: {model}")
    resp     = call_model("Respond with TRUE.", model=model, timeout=90, retries=3)
    response = resp["text"]
    if "TIMEOUT" in response or "ERROR" in response:
        print(f"[ERROR] API no responde: {response}")
        print("  Verifica OPENROUTER_API_KEY y conexion a internet")
        return False
    if "TRUE" in response.upper():
        print(f"[OK] API funcionando — respuesta: {response[:50]}")
        return True
    print(f"[WARN] API responde pero formato inesperado: {response[:100]}")
    return True


# ── 8. MAIN ──────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="SAIR Challenge Evaluator — OpenRouter"
    )
    p.add_argument("--cheatsheet", default="",
                   help="Path al .txt del cheat sheet (vacio = baseline)")
    p.add_argument("--problems",   default="normal",
                   choices=["normal", "hard", "hard1", "hard2"])
    p.add_argument("--model",      default=DEFAULT_MODEL,
                   help=f"Modelo OpenRouter (default: {DEFAULT_MODEL}). "
                        f"Ejemplos: mistralai/mixtral-8x7b-instruct, "
                        f"meta-llama/llama-3.1-70b-instruct, openai/gpt-4o-mini")
    p.add_argument("--max",        type=int, default=None,
                   help="Limitar numero de problemas")
    p.add_argument("--name",       default=None,
                   help="Nombre del experimento")
    p.add_argument("--delay",      type=float, default=0.5,
                   help="Segundos entre llamadas API (default: 0.5)")
    p.add_argument("--skip-test",  action="store_true",
                   help="Saltar verificacion de API")
    p.add_argument("--budget",     type=float, default=DEFAULT_BUDGET_USD,
                   help=f"Presupuesto maximo en USD — detiene la evaluacion si se supera "
                        f"(default: {DEFAULT_BUDGET_USD})")
    p.add_argument("--provider",   default="openrouter",
                   help="Proveedor de API (default: openrouter, para extensibilidad futura)")
    args = p.parse_args()

    # Verificar API key
    if not OPENROUTER_API_KEY:
        print("[ERROR] Falta OPENROUTER_API_KEY.")
        print("  Agrega la siguiente linea a tu archivo .env:")
        print("    OPENROUTER_API_KEY=tu_key_aqui")
        return

    # Test de conexion
    if not args.skip_test:
        if not test_api(args.model):
            return

    # Cargar cheat sheet
    cheatsheet = ""
    if args.cheatsheet:
        with open(args.cheatsheet, "r", encoding="utf-8") as f:
            cheatsheet = f.read()
        size = len(cheatsheet.encode("utf-8"))
        print(f"[CS] '{args.cheatsheet}' — {size} bytes")
        if size > 10240:
            print("[WARN] Supera 10KB — INFACTIBLE por regla de Coello")
    else:
        print("[CS] Baseline — sin cheat sheet")

    # Cargar problemas
    problems = load_problems(args.problems)
    name     = args.name or (
        Path(args.cheatsheet).stem if args.cheatsheet else "baseline"
    )
    # Use last segment of model name for readable experiment naming
    model_slug = args.model.split("/")[-1]
    name += f"_{model_slug}"

    # Estimacion de costo pre-ejecucion
    n_to_eval = min(args.max, len(problems)) if args.max else len(problems)
    est = estimate_run_cost(problems[:n_to_eval], cheatsheet, args.model)
    print(f"\n[COST] Estimacion para {est['n_problems']} problemas con {args.model}:")
    print(f"  ~{est['avg_input_tokens']} tokens in / ~{est['avg_output_tokens']} out por llamada")
    print(f"  Costo estimado:  ~${est['estimated_cost_usd']:.4f} USD")
    print(f"  Presupuesto max: ${args.budget:.2f} USD")
    if est["estimated_cost_usd"] > args.budget:
        print(f"  [WARN] La estimacion supera el presupuesto — "
              f"considera reducir --max o aumentar --budget")

    # Evaluar
    result = evaluate_cheatsheet(
        cheatsheet=cheatsheet,
        problems=problems,
        model=args.model,
        max_problems=args.max,
        delay=args.delay,
        budget_usd=args.budget,
    )

    print_metrics(name, result["metrics"])
    result["name"] = name
    save_results(result, name)


if __name__ == "__main__":
    main()
