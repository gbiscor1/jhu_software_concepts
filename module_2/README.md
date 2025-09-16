JHU EP 605.256 – Module 2: GradCafe Scraper
Student: Gabriel Bisco Reinato

Overview
--------
This project scrapes recent results from TheGradCafe, cleans/normalizes each row
to a defined schema, and standardizes the Program and University
fields using a tiny local LLM provided in llm_hosting.

Requirements
------------
- Python 3.10+
- A terminal (PowerShell/Command Prompt, etc)
- A text editor or IDE (VS Code recommended)
- Internet connection (for scraping and first-time model download by llm_hosting)
- The Python packages listed in requirements.txt

What it does
------------
1) Scrape: fetch N pages of public result listings (polite delays between pages).
2) Clean: normalize fields (dates, status, degree, GRE ranges, GPA bounds, etc.).
3) LLM Standardize (optional): call llm_hosting/app.py in CLI mode to produce
   program_canon and university_canon and, when non-empty, overwrite program/university.
4) Save: write JSON files to module_2/data/.

Quickstart (Windows PowerShell)
-------------------------------
cd module_2
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run full pipeline: <pages> <delay_seconds> <use_llm>
python app.py 60 0.5 true

Arguments
---------
<pages>         Integer. How many GradCafe result pages to scrape.
                Roughly ~1500 for 30,000 rows.

<delay_seconds> Float (seconds). Delay between HTTP requests during scraping.

<use_llm>       Boolean. If true, runs the local LLM standardization step
                via `llm_hosting/app.py` after cleaning. First LLM run downloads a small
                model and may take longer.

Outputs (module_2/data/)
------------------------
- applicant_data.json                raw scraped rows
- applicant_data.cleaned.json        schema-cleaned rows
- llm_extend_applicant_data.json     cleaned rows with LLM

Schema (models/applicant.py)
---------------------
Required:
- program 
- university 
- date_added 
- url 
- status 

Optional:
- comments, accept_date, reject_date
- start_term 
- citizenship
- gre_total 
- degree 
- gpa 

Project Tree (from root)
-----------------------------
jhu_software_concepts/
└─ module_2/
   ├─ app.py                   orchestrates: scrape, clean, LLM
   ├─ scrape.py                requests and parsing of result pages (scrapper agent)
   ├─ clean.py                 normalization, dataclass validation, LLM client, JSON saves (cleaner agent / LLM agent)
   ├─ models/
   │  └─ applicant.py          dataclasses
   ├─ llm_hosting/             tiny local llm package
   ├─ data/                    output JSON files
   │  ├─ applicant_data.json
   │  ├─ applicant_data.cleaned.json
   │  └─ llm_extend_applicant_data.json
   ├─ screenshots
   |   └─ manual robot check
   ├─ requirements.txt
   └─ README.md


Known Bugs:
----------
- None up to 5,000 rows. Depending on the time to process 30K rows with llm may need to increase timeout.
- May need to create optimization for llm cleanup

Disclaimer
----------
Some components were drafted with assistance from ChatGPT and then reviewed or customized:
- Regex/BeautifulSoup extraction helpers (started by coding them myself then used chatGPT to help me figure out how to scrape missed fields)
- Validation model (first sketched with GPT then modified for assignment)
- Suggestions for atomic/robust JSON writes
- File-based integration between the cleaner’s LLM step and llm_hosting (Helped me figure out how to call llm_hosting to write on file)
- ALL TEST FILES (not part of the assignment)
- Most print statements for debugging

References
----------
- https://www.thegradcafe.com
- https://realpython.com/python-web-scraping-practical-introduction
- https://realpython.com/beautiful-soup-web-scraper-python
