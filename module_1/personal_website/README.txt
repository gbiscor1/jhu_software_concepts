JHU EP 605.256 – Module 1 Personal Website
==========================================

Requirements
------------
To run this website locally you need:
- A computer with Python 3.10+ installed
- A terminal (Command Prompt / PowerShell on Windows, or a shell on Linux/Mac)
- A text editor or IDE (Visual Studio Code recommended)
- Internet browser (Chrome, Firefox, Edge, or Safari)
- The Flask library and dependencies listed in requirements.txt

Instructions
------------
1. Clone or download this repository to your computer.
2. Open a terminal in the project root folder.
3. Create a virtual environment:
   Windows:  python -m venv venv
   Linux/Mac: python3 -m venv venv
4. Activate the virtual environment:
   Windows:  venv\Scripts\activate
   Linux/Mac: source venv/bin/activate
5. Install dependencies:
   pip install -r requirements.txt
6. Start the application:
   python run.py
7. Open a browser and navigate to:
   http://127.0.0.1:8080

Disclaimer
----------
The base HTML templates (home.html, contact.html, projects.html) 
and the stylesheet (style.css) were initially generated using ChatGPT. 
They were then manually reviewed, patched, and customized to satisfy the 
assignment requirements and achieve the desired look and behavior.

Project tree from root
------------------------
jhu_software_concepts/
└── module_1/
    └── personal_website/       
        ├── run.py              
        ├── requirements.txt    
        ├── README.txt         
        ├── __init__.py         
        ├── routes.py           
        ├── templates/          
        │   ├── base.html
        │   ├── home.html
        │   ├── contact.html
        │   ├── projects.html
        │   └── _project_card.html
        ├── static/
        │   ├── css/
        │   │   └── style.css
        │   └── images/
        │       └── projects/
        │           
        ├── data/
        │   └── projects/
        │     
        └── screenshots/
            └── screenshots.pdf 