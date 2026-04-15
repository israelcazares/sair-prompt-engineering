#!/usr/bin/env python3
"""
SAIR Foundation - Mathematics Distillation Challenge
Pipeline de evaluacion via Together AI (multi-modelo)

Requisitos:
  pip install datasets requests numpy scipy python-dotenv

Configuracion:
  Edita el archivo .env en la misma carpeta:
    TOGETHER_API_KEY=tu_api_key_aqui
  O exporta la variable de entorno:
    export TOGETHER_API_KEY="tu_api_key_aqui"

Uso:
  python3 eval_pipeline_together.py --name baseline_llama_100 --max 100
  python3 eval_pipeline_together.py --cheatsheet cs_v2a.txt --name csv2a_llama_100 --max 100
  python3 eval_pipeline_together.py --model meta-llama/Llama-3.3-70B-Instruct-Turbo --max 50
  python3 eval_pipeline_together.py --problems hard2 --name baseline_hard2
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

load_dotenv()

# ── CONFIGURACION TOGETHER AI ────────────────────────────────────────────────

TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")
TOGETHER_URL     = "https://api.together.xyz/v1/chat/completions"
DEFAULT_MODEL    = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

# ── PRICING (USD / 1M tokens) — verify at https://www.together.ai/pricing ────
# Only serverless (pay-per-token) models listed here.
# Dedicated-endpoint models require a running endpoint and are NOT supported here.
MODEL_PRICING = {
    # Llama 3.x serverless
    "meta-llama/Llama-3.3-70B-Instruct-Turbo":        {"input": 0.88, "output": 0.88},
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo":    {"input": 0.18, "output": 0.18},
    "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo":  {"input": 3.50, "output": 3.50},
    # Qwen serverless
    "Qwen/Qwen2.5-72B-Instruct-Turbo":                {"input": 1.20, "output": 1.20},
    "Qwen/Qwen2.5-7B-Instruct-Turbo":                 {"input": 0.30, "output": 0.30},
    # Mistral serverless
    "mistralai/Mixtral-8x7B-Instruct-v0.1":           {"input": 0.60, "output": 0.60},
    "mistralai/Mistral-7B-Instruct-v0.3":             {"input": 0.20, "output": 0.20},
    # DeepSeek serverless
    "deepseek-ai/DeepSeek-R1-Distill-Llama-70B":      {"input": 0.88, "output": 0.88},
    "deepseek-ai/DeepSeek-R1":                        {"input": 7.00, "output": 7.00},
    # Google serverless
    "google/gemma-4-31B-it":                           {"input": 0.20, "output": 0.50},
    "google/gemma-2-9b-it":                            {"input": 0.30, "output": 0.30},
}
DEFAULT_PRICE_INPUT  = 1.00
DEFAULT_PRICE_OUTPUT = 1.00
DEFAULT_BUDGET_USD   = 10.0


# ── 1. CARGA DE PROBLEMAS ────────────────────────────────────────────────────

def load_problems(split="normal"):
    try:
        from datasets import load_dataset
        ds = load_dataset(
            "SAIRfoundation/equational-theories-selected-problems",
            name=split,
            split="train",
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


# ── 2. PROMPT ────────────────────────────────────────────────────────────────

def build_prompt(eq1, eq2, cheatsheet=""):
    cs_block = ("\n" + cheatsheet.strip() + "\n") if cheatsheet.strip() else ""
    return (
        "You are a mathematician specializing in equational theories of magmas.\n"
        f"Your task is to determine whether Equation 1 ({eq1}) "
        f"implies Equation 2 ({eq2}) over all magmas."
        f"{cs_block}\n"
        "Your response MUST begin with EXACTLY this line (no preamble):\n"
        "VERDICT: TRUE   or   VERDICT: FALSE\n\n"
        "Then use these sections:\n"
        "REASONING: (required, non-empty)\n"
        "PROOF: (required if TRUE, empty otherwise)\n"
        "COUNTEREXAMPLE: (required if FALSE, empty otherwise)"
    )


# ── 3. LLAMADA A TOGETHER AI ─────────────────────────────────────────────────

def extract_text(resp_json):
    """
    Robustly extract model output from Together AI / OpenAI-compatible responses.

    Priority order:
      1. choices[0].message.content   — standard chat format
      2. choices[0].message.reasoning — some models (e.g. gpt-oss-120b) return
                                        their answer here when content is empty
      3. choices[0].text              — completion format
      4. output_text / output         — Together-specific legacy formats

    Returns None if no usable text is found, which triggers a retry.
    """
    if not resp_json:
        return None

    if "choices" in resp_json:
        choices = resp_json["choices"]
        if choices and isinstance(choices[0], dict):
            choice = choices[0]
            msg = choice.get("message")
            if isinstance(msg, dict):
                # 1. Standard content field
                content = msg.get("content")
                if content and content.strip():
                    return content
                # 2. Reasoning field fallback (gpt-oss-120b and similar)
                reasoning = msg.get("reasoning")
                if reasoning and reasoning.strip():
                    return reasoning
            # 3. Completion-style text field
            text = choice.get("text")
            if text and text.strip():
                return text

    # 4. Together-specific legacy formats
    if resp_json.get("output_text", "").strip():
        return resp_json["output_text"]
    if resp_json.get("output", "").strip():
        return resp_json["output"]

    return None


def call_model(prompt, model=DEFAULT_MODEL, timeout=120, retries=5):
    """
    Calls Together AI chat/completions endpoint.

    Together uses the standard OpenAI-compatible path.
    Determinism: temperature=0, top_p=1, seed=42.

    Retry strategy:
      - 429 / 5xx  → exponential backoff (1 → 2 → 4 → 8 → 16 s, cap 60)
      - 401 / 403  → fatal (bad key) — no retry
      - timeout    → retry with backoff
      - empty body → retry with backoff
    """
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type":  "application/json",
    }
    # Gemma 4 on Together is very slow with high max_tokens; cap it
    mt = 2048 if "gemma" in model.lower() else 8192
    payload = {
        "model":       model,
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": 0,
        "top_p":       1,
        "seed":        42,
        "max_tokens":  mt,
    }

    for attempt in range(retries):
        wait = min(2 ** attempt, 60)
        try:
            r = requests.post(
                TOGETHER_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )

            try:
                data = r.json()
            except ValueError:
                data = {}

            # ── Embedded error object ─────────────────────────────────────────
            if "error" in data:
                err     = data["error"]
                err_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)

                if r.status_code in (401, 403):
                    print(f"  [AUTH ERROR {r.status_code}] {err_msg}")
                    return {"text": f"ERROR {r.status_code}: {err_msg}", "usage": {}}

                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After")
                    w = int(retry_after) if retry_after else wait
                    print(f"  [RATE LIMIT] esperando {w}s (intento {attempt+1}/{retries})")
                    time.sleep(w)
                    continue

                if r.status_code in (500, 502, 503, 504) and attempt < retries - 1:
                    print(f"  [SERVER {r.status_code}] {err_msg} — reintentando en {wait}s")
                    time.sleep(wait)
                    continue

                print(f"  [API ERROR {r.status_code}] {err_msg}")
                return {"text": f"ERROR: {err_msg}", "usage": {}}

            # ── Non-JSON HTTP errors ──────────────────────────────────────────
            if not r.ok:
                if r.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                    print(f"  [HTTP {r.status_code}] reintentando en {wait}s...")
                    time.sleep(wait)
                    continue
                return {"text": f"ERROR HTTP {r.status_code}", "usage": {}}

            # ── Extract content (handles all Together/OpenAI response formats) ──
            content = extract_text(data)

            if not content or not content.strip():
                if attempt < retries - 1:
                    print(f"  [EMPTY] respuesta vacia, reintentando en {wait}s...")
                    print(f"  [DEBUG] raw response: {data}")
                    time.sleep(wait)
                    continue
                print(f"  [DEBUG] raw response (final attempt): {data}")
                return {"text": "ERROR: empty response", "usage": {}}

            usage = data.get("usage") or {}
            result = {"text": content, "usage": usage}

            # Log system_fingerprint if present
            fp = data.get("system_fingerprint")
            if fp:
                result["system_fingerprint"] = fp

            return result

        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                print(f"  [TIMEOUT] intento {attempt+1}/{retries}, reintentando en {wait}s...")
                time.sleep(wait)
            else:
                return {"text": "TIMEOUT", "usage": {}}

        except Exception as e:
            return {"text": f"ERROR: {e}", "usage": {}}

    return {"text": "TIMEOUT", "usage": {}}


# ── 4. PARSER ────────────────────────────────────────────────────────────────

def parse_response(text):
    result = {
        "verdict":        None,
        "reasoning":      "",
        "proof":          "",
        "counterexample": "",
        "raw":            text,
    }

    if not text or text.startswith("TIMEOUT") or text.startswith("ERROR"):
        result["verdict"] = "FALSE"
        return result

    # ── Extract sections first (needed for structural signals below) ─────────
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

    # ── 1. Explicit VERDICT header — highest priority ─────────────────────────
    m = re.search(r"VERDICT\s*:\s*(TRUE|FALSE)", text, re.IGNORECASE)
    if m:
        result["verdict"] = m.group(1).upper()
        return result

    # ── 2. Structural signals from sections ──────────────────────────────────
    # Non-empty COUNTEREXAMPLE section → FALSE
    if result["counterexample"]:
        result["verdict"] = "FALSE"
        return result
    # Non-empty PROOF section → TRUE
    if result["proof"]:
        result["verdict"] = "TRUE"
        return result

    # ── 3. Natural-language patterns (sentence-level) ─────────────────────────
    true_pats = [
        r"\bverdict\b.*\btrue\b",
        r"\bimplication\s+holds\b",
        r"\bdoes\s+imply\b",
        r"\bindeed\s+implies\b",
        r"(?:thus|therefore|so|hence|conclusion[:\s])\s*,?\s*(?:the\s+answer\s+is\s+)?true\b",
        r"\bequation\s+2\s+(?:holds|follows|is\s+implied)\b",
        r"\bthe\s+implication\s+(?:is|holds)\s+true\b",
        r"\bthis\s+implies\b",
    ]
    false_pats = [
        r"\bverdict\b.*\bfalse\b",
        r"\bdoes\s+not\s+imply\b",
        r"\bfails\s+to\s+imply\b",
        r"\bimplication\s+(?:fails|does\s+not\s+hold)\b",
        r"(?:thus|therefore|so|hence|conclusion[:\s])\s*,?\s*(?:the\s+answer\s+is\s+)?false\b",
        r"\bequation\s+2\s+(?:does\s+not\s+hold|fails|is\s+not\s+implied)\b",
        r"\bcounterexample\b.*\bshows\b",
        r"\b(?:serves?\s+as|is)\s+a\s+counterexample\b",
    ]
    t = text.lower()
    for pat in true_pats:
        if re.search(pat, t):
            result["verdict"] = "TRUE"
            return result
    for pat in false_pats:
        if re.search(pat, t):
            result["verdict"] = "FALSE"
            return result

    # ── 4. Bare TRUE / FALSE anywhere in text — use last occurrence ───────────
    # Collect all matches with positions to resolve conflicts.
    all_hits = []
    for m in re.finditer(r"\b(TRUE|FALSE)\b", text, re.IGNORECASE):
        all_hits.append((m.start(), m.group(1).upper()))

    if all_hits:
        # If only one value appears, use it.
        values = {v for _, v in all_hits}
        if len(values) == 1:
            result["verdict"] = values.pop()
        else:
            # Conflict: TRUE and FALSE both present → use last occurrence.
            result["verdict"] = all_hits[-1][1]
        return result

    # ── 5. Final safety fallback — verdict is NEVER None ─────────────────────
    result["verdict"] = "FALSE"
    return result


# ── 5. COST TRACKING ─────────────────────────────────────────────────────────

def _get_pricing(model):
    return MODEL_PRICING.get(
        model, {"input": DEFAULT_PRICE_INPUT, "output": DEFAULT_PRICE_OUTPUT}
    )


def tokens_to_cost(in_tokens, out_tokens, model):
    p = _get_pricing(model)
    return (in_tokens * p["input"] + out_tokens * p["output"]) / 1_000_000


def estimate_tokens(text):
    return round(len(text) / 4)


def estimate_run_cost(problems, cheatsheet, model=DEFAULT_MODEL):
    p             = _get_pricing(model)
    sample_prompt = build_prompt(problems[0]["eq1"], problems[0]["eq2"], cheatsheet)
    avg_in        = len(sample_prompt) / 4.0
    avg_out       = 400.0
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


# ── 6. EVALUATE SINGLE PROBLEM ───────────────────────────────────────────────

def evaluate_problem(prob, cheatsheet, model, raw_prompt=False):
    """Evaluate one problem. Returns a result dict."""
    if raw_prompt and cheatsheet:
        prompt = cheatsheet.replace("{{ equation1 }}", prob["eq1"]).replace("{{ equation2 }}", prob["eq2"])
    else:
        prompt = build_prompt(prob["eq1"], prob["eq2"], cheatsheet)
    resp   = call_model(prompt, model)
    raw    = resp["text"]
    usage  = resp["usage"]

    if usage.get("prompt_tokens") or usage.get("completion_tokens"):
        in_tok  = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        estimated = False
    else:
        in_tok  = estimate_tokens(prompt)
        out_tok = estimate_tokens(raw)
        estimated = True

    call_cost = tokens_to_cost(in_tok, out_tok, model)
    parsed    = parse_response(raw)
    predicted = parsed["verdict"]
    actual    = prob["label"].upper()

    return {
        "id":             prob["id"],
        "eq1":            prob["eq1"],
        "eq2":            prob["eq2"],
        "label":          actual,
        "predicted":      predicted,
        "correct":        predicted == actual,
        "reasoning":      parsed["reasoning"],
        "proof":          parsed["proof"],
        "counterexample": parsed["counterexample"],
        "tokens_in":      in_tok,
        "tokens_out":     out_tok,
        "cost_usd":       round(call_cost, 6),
        "estimated":      estimated,
        "system_fingerprint": resp.get("system_fingerprint"),
    }


# ── 7. RUN PIPELINE ──────────────────────────────────────────────────────────

def run_pipeline(cheatsheet, problems, model=DEFAULT_MODEL,
                 max_problems=None, delay=0.5,
                 budget_usd=DEFAULT_BUDGET_USD, raw_prompt=False):
    if max_problems:
        problems = problems[:max_problems]

    results             = []
    correct             = 0
    true_correct        = 0
    false_correct       = 0
    true_total          = 0
    false_total         = 0
    total_input_tokens  = 0
    total_output_tokens = 0
    total_cost_usd      = 0.0
    budget_exceeded     = False
    tokens_estimated    = 0

    size_bytes = len(cheatsheet.encode("utf-8"))
    feasible   = size_bytes <= 10240

    print(f"\n[EVAL] {len(problems)} problemas | modelo: {model}")
    print(f"[EVAL] Cheat sheet: {size_bytes} bytes | "
          f"{'FACTIBLE' if feasible else 'INFACTIBLE >10KB'}")
    print(f"[EVAL] API: Together AI | Presupuesto: ${budget_usd:.2f} USD")

    start_time = time.time()

    for i, prob in enumerate(problems):
        r = evaluate_problem(prob, cheatsheet, model, raw_prompt=raw_prompt)
        results.append(r)

        total_input_tokens  += r["tokens_in"]
        total_output_tokens += r["tokens_out"]
        total_cost_usd      += r["cost_usd"]
        if r["estimated"]:
            tokens_estimated += 1

        if r["correct"]:
            correct += 1
        if r["label"] == "TRUE":
            true_total += 1
            if r["correct"]:
                true_correct += 1
        else:
            false_total += 1
            if r["correct"]:
                false_correct += 1

        elapsed   = time.time() - start_time
        avg_sec   = elapsed / (i + 1)
        remaining = avg_sec * (len(problems) - i - 1)
        hrs       = int(remaining // 3600)
        mins      = int((remaining % 3600) // 60)
        acc_now   = correct / (i + 1)
        est_flag  = "~" if tokens_estimated > 0 else ""

        status = "OK  " if r["correct"] else "FAIL"
        print(f"  [{i+1:>4}/{len(problems)}] {status} | "
              f"label={r['label']} pred={str(r['predicted']):<5} | "
              f"acc={acc_now:.2f} | "
              f"{avg_sec:.1f}s/prob | ETA {hrs}h{mins:02d}m | "
              f"{est_flag}${total_cost_usd:.4f} | "
              f"{prob['eq1'][:25]}")

        # Budget warning at 80%
        if total_cost_usd >= budget_usd * 0.8 and total_cost_usd < budget_usd:
            print(f"  [WARN] {total_cost_usd/budget_usd*100:.0f}% del presupuesto usado")

        if total_cost_usd >= budget_usd:
            print(f"\n[BUDGET] Limite de ${budget_usd:.2f} USD alcanzado tras "
                  f"{i+1} problemas — deteniendo evaluacion.")
            budget_exceeded = True
            break

        if i < len(problems) - 1:
            time.sleep(delay)

    n        = len(results)
    f1       = correct       / n           if n           > 0 else 0.0
    f2_true  = true_correct  / true_total  if true_total  > 0 else 0.0
    f2_false = false_correct / false_total if false_total > 0 else 0.0
    f2       = (f2_true + f2_false) / 2.0
    total_mins = (time.time() - start_time) / 60

    est_note = f" (~{tokens_estimated} estimadas)" if tokens_estimated else ""
    print(f"\n[TIME] Completado en {total_mins:.1f} minutos")
    print(f"[COST] Total: ${total_cost_usd:.4f} USD  "
          f"({total_input_tokens:,} in / {total_output_tokens:,} out){est_note}")

    metrics = {
        "f1_accuracy":            f1,
        "f2_coverage":            f2,
        "f2_true_acc":            f2_true,
        "f2_false_acc":           f2_false,
        "f3_neg_size":            -size_bytes,
        "size_bytes":             size_bytes,
        "feasible":               feasible,
        "n_correct":              correct,
        "n_total":                n,
        "n_true_correct":         true_correct,
        "n_true_total":           true_total,
        "n_false_correct":        false_correct,
        "n_false_total":          false_total,
        "model":                  model,
        "provider":               "together",
        "timestamp":              datetime.now().isoformat(),
        "total_minutes":          round(total_mins, 1),
        "total_input_tokens":     total_input_tokens,
        "total_output_tokens":    total_output_tokens,
        "total_cost_usd":         round(total_cost_usd, 6),
        "budget_usd":             budget_usd,
        "budget_exceeded":        budget_exceeded,
        "tokens_estimated_calls": tokens_estimated,
        "determinism":            {"temperature": 0, "top_p": 1, "seed": 42},
    }
    return {"metrics": metrics, "results": results}


# ── 8. SAVE & DISPLAY ────────────────────────────────────────────────────────

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
    print(f"  Determinism: temp={m['determinism']['temperature']} "
          f"top_p={m['determinism']['top_p']} "
          f"seed={m['determinism']['seed']}")
    print(f"  f1 accuracy: {m['f1_accuracy']:.4f}  "
          f"({m['n_correct']}/{m['n_total']})")
    print(f"  TRUE  acc:   {m['f2_true_acc']:.4f}  "
          f"({m['n_true_correct']}/{m['n_true_total']})")
    print(f"  FALSE acc:   {m['f2_false_acc']:.4f}  "
          f"({m['n_false_correct']}/{m['n_false_total']})")
    print(f"  Size:        {m['size_bytes']} bytes  "
          f"({'OK' if m['feasible'] else 'INFACTIBLE'})")
    print(f"  Costo total: ${m.get('total_cost_usd', 0):.4f} USD  "
          f"({m.get('total_input_tokens', 0):,} in / "
          f"{m.get('total_output_tokens', 0):,} out){est_note}")
    if m.get("budget_exceeded"):
        print(f"  [WARN] Presupuesto de ${m.get('budget_usd', '?')} USD alcanzado "
              f"— evaluacion incompleta ({m['n_total']} problemas evaluados)")
    print(f"{'='*60}")


# ── 9. API TEST ──────────────────────────────────────────────────────────────

def test_api(model=DEFAULT_MODEL):
    print(f"[TEST] Verificando conexion a Together AI con modelo: {model}")
    resp     = call_model("Respond with exactly: TRUE", model=model, timeout=60, retries=3)
    response = resp["text"]
    if "TIMEOUT" in response or "ERROR" in response:
        print(f"[ERROR] API no responde: {response}")
        print("  Verifica TOGETHER_API_KEY y conexion a internet")
        return False
    if "TRUE" in response.upper():
        print(f"[OK] API funcionando — respuesta: {response[:50]}")
        return True
    print(f"[WARN] API responde pero formato inesperado: {response[:100]}")
    return True


# ── 10. MAIN ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="SAIR Challenge Evaluator — Together AI"
    )
    p.add_argument("--cheatsheet", default="",
                   help="Path al .txt del cheat sheet (vacio = baseline)")
    p.add_argument("--problems",   default="normal",
                   choices=["normal", "hard", "hard1", "hard2", "hard3"])
    p.add_argument("--model",      default=DEFAULT_MODEL,
                   help=f"Modelo Together AI (default: {DEFAULT_MODEL})")
    p.add_argument("--max",        type=int, default=None,
                   help="Limitar numero de problemas")
    p.add_argument("--skip",       type=int, default=0,
                   help="Saltar los primeros N problemas (default: 0)")
    p.add_argument("--name",       default=None,
                   help="Nombre del experimento")
    p.add_argument("--delay",      type=float, default=0.5,
                   help="Segundos entre llamadas API (default: 0.5)")
    p.add_argument("--skip-test",  action="store_true",
                   help="Saltar verificacion de API")
    p.add_argument("--budget",     type=float, default=DEFAULT_BUDGET_USD,
                   help=f"Presupuesto maximo en USD (default: {DEFAULT_BUDGET_USD})")
    p.add_argument("--raw-prompt", action="store_true",
                   help="Use cheatsheet as complete prompt (substitute {{equation1}}/{{equation2}} directly)")
    args = p.parse_args()

    if not TOGETHER_API_KEY:
        print("[ERROR] Falta TOGETHER_API_KEY.")
        print("  Agrega a tu archivo .env:")
        print("    TOGETHER_API_KEY=tu_key_aqui")
        return

    if not args.skip_test:
        if not test_api(args.model):
            return

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

    problems   = load_problems(args.problems)
    if args.skip > 0:
        print(f"[SKIP] Saltando los primeros {args.skip} problemas")
        problems = problems[args.skip:]
    model_slug = args.model.split("/")[-1]
    name       = args.name or (
        Path(args.cheatsheet).stem if args.cheatsheet else "baseline"
    )
    name += f"_{model_slug}"

    n_to_eval = min(args.max, len(problems)) if args.max else len(problems)
    est = estimate_run_cost(problems[:n_to_eval], cheatsheet, args.model)
    print(f"\n[COST] Estimacion para {est['n_problems']} problemas con {args.model}:")
    print(f"  ~{est['avg_input_tokens']} tokens in / ~{est['avg_output_tokens']} out por llamada")
    print(f"  Costo estimado:  ~${est['estimated_cost_usd']:.4f} USD")
    print(f"  Presupuesto max: ${args.budget:.2f} USD")
    if est["estimated_cost_usd"] > args.budget:
        print(f"  [WARN] La estimacion supera el presupuesto — "
              f"considera reducir --max o aumentar --budget")

    result = run_pipeline(
        cheatsheet=cheatsheet,
        problems=problems,
        model=args.model,
        max_problems=args.max,
        delay=args.delay,
        budget_usd=args.budget,
        raw_prompt=args.raw_prompt,
    )

    print_metrics(name, result["metrics"])
    result["name"] = name
    save_results(result, name)


if __name__ == "__main__":
    main()
