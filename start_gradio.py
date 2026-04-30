#!/usr/bin/env python3
from pathlib import Path
import sys

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.src.gradio_app.app import main

if __name__ == "__main__":
    main()
