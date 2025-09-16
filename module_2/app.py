import os
import sys
import time
import subprocess
from contextlib import contextmanager
from pathlib import Path

import requests  # pip install requests

from scrape import Scraper
from clean import Cleaner, extend_with_llm
from models.applicant import ApplicantEntry, ApplicantEntryExtended

# Global variables
PAGES = 50   # For page parsing control over command lines
DELAY = 0.8  # For custom delay override
RUN_LLM = True  # For overriding llm function

# ---------- Auto-start or reuse LLM host (HTTP) ----------
def start_llm_host_if_needed(port: int = 8000):
    import os, sys, time, subprocess, requests
    from pathlib import Path

    base = f"http://127.0.0.1:{port}"

    # Reuse an already running host
    try:
        r = requests.get(base + "/", timeout=0.8)
        if r.ok:
            os.environ["LLM_HOSTING_URL"] = base
            print(f"[LLM] using existing host at {base}")
            return None  # we didn't spawn a new process
    except requests.RequestException:
        pass

    # Otherwise start the professor's host (unchanged file in llm_hosting/)
    llm_dir = Path(__file__).parent / "llm_hosting"
    env = os.environ.copy()
    env["PORT"] = env["LLM_PORT"] = str(port)

    proc = subprocess.Popen(
        [sys.executable, "app.py", "--serve"],
        cwd=str(llm_dir),
        env=env,
        stdout=subprocess.DEVNULL,   # keep logs quiet
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Wait until health endpoint responds
    deadline = time.time() + 20.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"[LLM] host exited (code {proc.returncode}).")
        try:
            if requests.get(base + "/", timeout=1.0).ok:
                os.environ["LLM_HOSTING_URL"] = base
                print(f"[LLM] ready at {base}")
                return proc
        except requests.RequestException:
            time.sleep(0.3)

    proc.terminate()
    raise RuntimeError("[LLM] host not ready.")

def main():
    global PAGES, DELAY, RUN_LLM

    # --- argv parsing ---
    if len(sys.argv) > 1:
        try:
            PAGES = int(sys.argv[1])
        except ValueError:
            print(f"Invalid page number: {sys.argv[1]} (using default {PAGES})")
    if len(sys.argv) > 2:
        try:
            DELAY = float(sys.argv[2])
        except ValueError:
            print(f"Invalid delay: {DELAY} (keeping default)")
    if len(sys.argv) > 3:
        RUN_LLM = (sys.argv[3].lower() == "true")

    print(f"[app.py]  Scraping {PAGES} pages with {DELAY:.2f}s delay…")
    print(f"[app.py]  LLM standardization: {'ON' if RUN_LLM else 'OFF'}")

    # --- scrape ---
    scraper = Scraper("https://www.thegradcafe.com/survey/", delay=DELAY)
    rows = scraper.scrape(start_page=1, max_pages=PAGES, out_path="data/applicant_data.json")
    print(f"[app.py] Collected {len(rows)} rows: applicant_data.json")

    # --- clean ---
    cleaner = Cleaner(validate_with_dataclass=True)
    cleaner.enable_dataclass_validation(ApplicantEntry, ApplicantEntryExtended)
    cleaner.clean_file("data/applicant_data.json", "data/applicant_data.cleaned.json")
    print("[Clean] Wrote applicant_data.cleaned.json")

    # --- LLM ---
    if RUN_LLM:
        print("[app.py] Starting LLM Host…")
        proc = start_llm_host_if_needed(port=8000)
        try:
            extend_with_llm(
                "data/applicant_data.cleaned.json",
                "data/llm_extend_applicant_data.json",
                timeout_s=600,                 # give the host time per batch
                validate_with_dataclass=True
            )
            print("[app.py] Wrote llm_extend_applicant_data.json")
        finally:
            # Only terminate if we actually started it here
            if proc is not None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    pass

    print("[app.py] Pipeline complete.")

if __name__ == "__main__":
    main()
