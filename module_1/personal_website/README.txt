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
3. Create a virtual environment.
4. Activate the virtual environment.
5. Install dependencies:
   pip install -r requirements.txt
6. Start the application:
   python run.py
7. Open a browser and navigate to:
   http://127.0.0.1:8080

Disclaimer
----------
The HTML templates (home.html, contact.html, projects.html) 
and the stylesheet (style.css) were initially generated using ChatGPT. 
They were then manually reviewed, patched, and customized to satisfy the 
assignment requirements and achieve the desired style.

Project tree from root
------------------------
jhu_software_concepts/
└── module_1/
    └── personal_website/       
        ├── run.py              
        ├── requirements.txt    
        ├── README.txt         
        ├── __init__.py -> Initializes flask       
        ├── routes.py   -> page router and helper function for loading project data        
        ├── templates/          
        │   ├── base.html  -> Base template to be extended
        │   ├── home.html  -> Extension of base
        │   ├── contact.html -> Extension of base
        │   ├── projects.html  -> Extension of base, board for card snapping
        │   └── _project_card.html -> modular project container for snapping into projects.html
        ├── static/
        │   ├── css/
        │   │   └── style.css  -> File for styles in the whole project
        │   └── images/ -> directory with all images
        │      
        │           
        ├── data/  -> Project JSON files for snapping
        │   └── projects/
        │     
        └── screenshots/
            └── screenshots.pdf 

References and Images
---------------------------
https://www.freepik.com/free-vector/emotion-detection-abstract-concept-vector-illustration-speech-emotional-state-recognition-emotion-detection-from-text-sensor-technology-machine-learning-ai-reading-face-abstract-metaphor_11668839.htm?epik=dj0yJnU9bmR5aXg3NlphUFpUSENsbDNNSnFnSjZjcWxlN3VyNk8mcD0wJm49UXd0d2M0eXcwVHNRNTA5SndhTWQ5ZyZ0PUFBQUFBR2l5Qy13
https://klaxoon.com/community-content/organizing-a-hackathon-appeal-to-the-teams-competitive-spirit-and-come-up-with-innovative-solutions
https://www.sliderrevolution.com/design/one-page-website-template/
https://realpython.com/flask-project/
