import logging
from pathlib import Path

def setup_logging():
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "neurodeamon.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.getLogger('sqlite3').setLevel(logging.WARNING) # Reduzir logs do sqlite
