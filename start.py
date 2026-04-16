#!/usr/bin/env python3
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.src.main import app
from backend.src.config import settings
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "start:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True
    )
