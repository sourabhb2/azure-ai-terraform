import os
import subprocess
import requests
import json
import re
from string import Template
from datetime import datetime

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "phi3:mini"

# Avoid proxy issues for localhost
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

REPO_PATH = os.getcwd()
ENV_PATH = os.path.join(REPO_PATH, "env")
TF_FILE = os.path.join(ENV_PATH, "main.tf")

TEMPLATES = {
    "create_vm": os.path.join(REPO_PATH, "templates", "vm.tf.tpl"),
    "create_storage": os.path.join(REPO_PATH, "templates", "storage.tf.tpl"),
}

session = requests.Session()
session.trust_env = False


def log(msg):
    print(msg, flush=True)


def run(args, cwd):
    subprocess.check_call(args, cwd=cwd)


def sanitize_storage_name(name: str) -> str:
    # Azure rules: lowercase letters+numbers only, 3-24 chars
    name = (name or "").lower()
    name = re.sub(r"[^a-z0-9]", "", name)
    if len(name) < 3:
        name = "stg" + datetime.now().strftime("%H%M%S")
    if len(name) > 24:
        name = name[:24]
    return name


def ollama_generate(prompt: str, system_prompt: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": system_prompt + "\n\nUSER REQUEST:\n" + prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 220},
    }
    r = session.post(OLLAMA_URL, json=payload, timeout=300)
    r.raise_for_status()
    return r.json().get("response", "").strip()


def extract_json(text: str) -> str:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0).strip() if m else ""


def repair_json(js: str) -> str:
    js = js.strip()
    js = js.replace("'", '"')
    js = re.sub(r",\s*}", "}", js)
    js = re.sub(r",\s*]", "]", js)
    js = re.sub(r'(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1 "\2":', js)
    return js


def call_llm_json(prompt: str, retries: int = 3) -> dict:
    system = """Return ONLY valid JSON. No markdown. No explanation.

Supported actions:
- create_vm
- create_storage

Schema:
{
  "action": "create_vm|create_storage",
  "rg_name": "ai-rg",
  "location": "Central India",
  "vm_name": "ai-vm",
  "vm_size": "Standard_B1s",
  "storage_account_name": "aistorage1234"
}

Rules:
- Always output JSON ONLY
- Never return empty rg_name or location; use defaults
- Use double quotes only
- No trailing commas
"""

    raw = ollama_generate(prompt, system)

    for attempt in range(retries):
        js = extract_json(raw)
        if not js:
            raw = ollama_generate("Return JSON only: " + prompt, system)
            continue

        fixed = repair_json(js)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            raw = ollama_generate("Fix JSON strictly, output only JSON:\n" + fixed, system)

    raise ValueError("LLM JSON parse failed.")


def render_from_template(template_path: str, variables: dict) -> str:
    with open(template_path, "r", encoding="utf-8") as f:
        tpl = Template(f.read())
    return tpl.safe_substitute(variables)


def write_tf(code: str):
    os.makedirs(ENV_PATH, exist_ok=True)
    with open(TF_FILE, "w", encoding="utf-8") as f:
        f.write(code)
    log(f"✅ Terraform written: {TF_FILE}")


def terraform_validate():
    log("🔍 Running terraform fmt/init/validate...")
    run(["terraform", "fmt"], ENV_PATH)
    run(["terraform", "init", "-upgrade"], ENV_PATH)
    run(["terraform", "validate"], ENV_PATH)
    log("✅ Terraform validation successful")


def git_push(commit_message: str):
    # Commit only the important files
    run(["git", "add", ".gitignore"], REPO_PATH)
    run(["git", "add", "env/main.tf"], REPO_PATH)
    run(["git", "add", "templates"], REPO_PATH)

    try:
        run(["git", "commit", "-m", commit_message], REPO_PATH)
    except subprocess.CalledProcessError:
        log("⚠️ Nothing to commit.")
        return

    run(["git", "push", "origin", "main"], REPO_PATH)
    log("✅ Code pushed to GitHub (GitHub Actions will deploy)")


def main():
    prompt = input("💻 Enter command: ").strip()
    if not prompt:
        log("❌ Empty prompt.")
        return

    log("🤖 Understanding prompt using Local LLM...")
    data = call_llm_json(prompt)
    log(f"✅ JSON: {data}")

    action = (data.get("action") or "").strip()
    if action not in TEMPLATES:
        log(f"❌ Unsupported action: {action}")
        log(f"Supported: {list(TEMPLATES.keys())}")
        return

    # Defaults
    if not data.get("rg_name"):
        data["rg_name"] = "ai-rg"
    if not data.get("location"):
        data["location"] = "Central India"

    if action == "create_vm":
        if not data.get("vm_name"):
            data["vm_name"] = "ai-vm"
        if not data.get("vm_size"):
            data["vm_size"] = "Standard_B1s"

    if action == "create_storage":
        if not data.get("storage_account_name"):
            data["storage_account_name"] = "aistorage" + datetime.now().strftime("%H%M%S")
        data["storage_account_name"] = sanitize_storage_name(data["storage_account_name"])

    tf_code = render_from_template(TEMPLATES[action], data)
    write_tf(tf_code)
    terraform_validate()
    git_push(f"AI: {action}")


if __name__ == "__main__":
    main()
