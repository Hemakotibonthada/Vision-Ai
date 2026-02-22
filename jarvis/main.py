"""
Jarvis AI - Main Entry Point
===============================
Starts the Jarvis AI system with all services.

Usage:
    python -m jarvis.main
    OR
    uvicorn jarvis.api:app --host 0.0.0.0 --port 8100
"""
import asyncio
import sys
import os
import signal

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from loguru import logger

from jarvis.config import settings


def configure_logging():
    """Configure loguru logging."""
    log_dir = os.path.join(settings.DATA_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger.add(
        os.path.join(log_dir, "jarvis_{time}.log"),
        rotation="10 MB",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} - {message}",
    )


def print_banner():
    """Print Jarvis startup banner."""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║         ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗         ║
    ║         ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝         ║
    ║         ██║███████║██████╔╝██║   ██║██║███████╗         ║
    ║    ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║         ║
    ║    ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║         ║
    ║     ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝         ║
    ║                                                          ║
    ║           AI Home Assistant v1.0.0                       ║
    ║           Face Recognition • Voice Control               ║
    ║           Security • Smart Home • Learning               ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)
    print(f"  API Server:    http://localhost:{settings.JARVIS_PORT}")
    print(f"  WebSocket:     ws://localhost:{settings.JARVIS_WS_PORT}/ws")
    print(f"  Vision AI:     {settings.VISION_API_URL}")
    print(f"  ESP32 Server:  {settings.ESP32_SERVER_URL}")
    print(f"  Owner:         {settings.OWNER_NAME}")
    print(f"  Data Dir:      {settings.DATA_DIR}")
    print()


def main():
    """Main entry point."""
    configure_logging()
    print_banner()

    logger.info("Starting Jarvis AI System...")

    uvicorn.run(
        "jarvis.api:app",
        host="0.0.0.0",
        port=settings.JARVIS_PORT,
        reload=False,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
