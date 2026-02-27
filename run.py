import uvicorn
import uvicorn.config
import os
import sys
import copy

# Ensure current directory is in sys.path so scrollarr package is found
sys.path.append(os.getcwd())

if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    # Configure Uvicorn logging
    log_config = copy.deepcopy(uvicorn.config.LOGGING_CONFIG)

    log_config["handlers"]["file"] = {
        "class": "logging.FileHandler",
        "filename": "logs/uvicorn.log",
        "formatter": "default",
        "mode": "a",
        "encoding": "utf-8",
    }

    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        if logger_name in log_config["loggers"]:
             # Ensure handlers list exists
             if "handlers" not in log_config["loggers"][logger_name]:
                 log_config["loggers"][logger_name]["handlers"] = []
             log_config["loggers"][logger_name]["handlers"].append("file")

    # Exclude configuration files from reloader to prevent restart loops during setup/settings save
    # Also exclude database files and logs
    reload_excludes = [
        "config/*.json",
        "config/*.tmp",
        "*.db",
        "*.db-journal",
        "*.db-wal",
        "*.db-shm",
        "logs/*",
        "*.log"
    ]

    uvicorn.run(
        "scrollarr.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=log_config,
        reload_excludes=reload_excludes
    )
