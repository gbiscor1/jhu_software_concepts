import sys
from scrape import Scraper
from clean import Cleaner, extend_with_llm
from models.applicant import ApplicantEntry, ApplicantEntryExtended

# Global variables
PAGES = 50  # For page parsing control over command lines
DELAY = 0.8 # For costum delay override
RUN_LLM = True # For ovirriding llm function (helps debug)

def main():
    global PAGES, DELAY, RUN_LLM 

    # Allow quick override and simple checks
    if len(sys.argv) > 1:
        try:
            PAGES = int(sys.argv[1])
        except ValueError:
            print(f"Invalid page number: {sys.argv[1]} (using default {PAGES})")
    if len(sys.argv) > 2:
        try:
            DELAY = float(sys.argv[2])
        except ValueError:
            print(f"Invalid delay: {sys.argv[2]} (using default {DELAY})")
    if len(sys.argv) > 3:
        arg = sys.argv[3].lower()
        if arg == "true":
            RUN_LLM = True
        elif arg == "false":
            RUN_LLM = False

    print(f"[app.py]  Scraping {PAGES} pages with {DELAY:.2f}s delay...")
    print(f"[app.py]  LLM standardization: {'ON' if RUN_LLM else 'OFF'}")

    # Scrape agent
    scraper = Scraper("https://www.thegradcafe.com/survey/", delay=DELAY) # Set website to be scrapped
    rows = scraper.scrape(
        start_page=1,
        max_pages=PAGES,
        out_path="data/applicant_data.json"
    )
    print(f"[app.py] Collected {len(rows)} rows: applicant_data.json")

    #  Cleaner agent
    cleaner = Cleaner(validate_with_dataclass=True) # Allow validation againist model class
    cleaner.enable_dataclass_validation(ApplicantEntry, ApplicantEntryExtended) # Specify model class
    cleaner.clean_file(
        "data/applicant_data.json",
        "data/applicant_data.cleaned.json"
    )
    print("[Clean] Wrote applicant_data.cleaned.json")

    #  LLM Standardization
    if RUN_LLM:
        extend_with_llm(
            "data/applicant_data.cleaned.json",
            "data/llm_extend_applicant_data.json",
            llm_app_dir="llm_hosting",
            validate_with_dataclass=True
        )
        print("[app.py] Wrote llm_extend_applicant_data.json")

    print("[app.py] Pipeline complete.")

if __name__ == "__main__":
    main()