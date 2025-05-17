import os
from pathlib import Path 
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

files = [
    "src/__init__.py"
    "src/main.py",              
    "src/utils/helpers.py",   
    "src/utils/prompt.py"    
    "data/raw/",
    "data/processed/",            
    "models/",                     
    "logs/app.log",               
    "configs/config.yaml",         
    "README.md",
    "research/med_trial1.ipynb",
    "setup.py",
    "app.py",
    "tests/test_main.py",                                   
]

def create_project_structure():
    """Create files and directories as per the template."""
    for file in files:
        file_path = Path(file)
        
        if file_path.suffix:  
            file_path.parent.mkdir(parents=True, exist_ok=True) 
            if not file_path.exists():
                file_path.touch()
                logging.info(f"Created file: {file_path}")
            else:
                logging.info(f"File already exists: {file_path}")
        else:  
            file_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created directory: {file_path}")

if __name__ == "__main__":
    create_project_structure()
    logging.info("Project structure setup complete.")