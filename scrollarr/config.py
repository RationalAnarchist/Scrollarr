import json
import os
import shutil
import logging
import uuid
import secrets

logger = logging.getLogger(__name__)

class ConfigManager:
    _instance = None
    CONFIG_FILE = "config/config.json"
    EXAMPLE_CONFIG_FILE = "config/config.json.example"
    DEFAULT_CONFIG = {
        "download_path": "saved_stories",
        "min_delay": 2.0,
        "max_delay": 5.0,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "update_interval_hours": 1,
        "worker_sleep_min": 30.0,
        "worker_sleep_max": 60.0,
        "database_url": "sqlite:///library.db",
        "log_level": "INFO",
        "library_path": "library",
        "story_folder_format": "{Title} ({Id})",
        "chapter_file_format": "{Index} - {Title}",
        "volume_folder_format": "Volume {Volume}",
        "compiled_filename_pattern": "{Title} - {Volume}",
        "single_chapter_name_format": "{Title} - {Index} - {Chapter}",
        "chapter_group_name_format": "{Title} - {StartChapter} to {EndChapter}",
        "volume_name_format": "{Title} - {Volume} - {VolName}",
        "full_story_name_format": "{Title} - Full story to {EndChapter}",

        # Security defaults
        "auth_method": "NotDecided",
        "auth_username": "",
        "auth_password": "",
        "api_key": "",
        "session_secret": "",
        "local_auth_disabled": False,
        "setup_complete": False
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.config = cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """Loads configuration from file or creates default if missing."""
        config = self.DEFAULT_CONFIG.copy()
        config_exists = os.path.exists(self.CONFIG_FILE)
        file_config = {}
        save_needed = False

        if not config_exists:
            if os.path.exists(self.EXAMPLE_CONFIG_FILE):
                logger.info(f"Config file not found. Creating from example at {self.EXAMPLE_CONFIG_FILE}")
                try:
                    shutil.copy(self.EXAMPLE_CONFIG_FILE, self.CONFIG_FILE)
                    # Reload as if it existed
                    with open(self.CONFIG_FILE, 'r') as f:
                        file_config = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to copy example config: {e}")
            else:
                logger.info(f"Config file not found. Creating default at {self.CONFIG_FILE}")
                save_needed = True
        else:
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    file_config = json.load(f)
            except Exception as e:
                 logger.error(f"Failed to load config file: {e}. Using defaults.")

        # Merge file config into defaults
        if file_config:
            config.update(file_config)

            # Check for missing keys from example config (if available) to soft-update
            if os.path.exists(self.EXAMPLE_CONFIG_FILE):
                try:
                    with open(self.EXAMPLE_CONFIG_FILE, 'r') as f:
                        example_config = json.load(f)
                        for k, v in example_config.items():
                            if k not in config:
                                config[k] = v
                                logger.info(f"Added missing config key '{k}' from example.")
                                save_needed = True
                except Exception as e:
                    logger.warning(f"Failed to read example config for updates: {e}")

        # Migration logic
        # 1. Filename pattern migration
        if 'filename_pattern' in file_config and 'compiled_filename_pattern' not in file_config:
             config['compiled_filename_pattern'] = file_config['filename_pattern']
             save_needed = True

        # 2. Fix legacy double "Vol" pattern
        if config.get('compiled_filename_pattern') == "{Title} - Vol {Volume}":
            config['compiled_filename_pattern'] = "{Title} - {Volume}"
            save_needed = True

        # 3. Setup Complete for existing users (Migration)
        # If config existed but setup_complete was missing, assume it's an upgrade and mark as complete
        if config_exists and 'setup_complete' not in file_config:
            config['setup_complete'] = True
            save_needed = True

        # 4. Generate API Key if missing
        if not config.get('api_key'):
            config['api_key'] = str(uuid.uuid4())
            save_needed = True

        # 5. Generate Session Secret if missing
        if not config.get('session_secret'):
            config['session_secret'] = secrets.token_hex(32)
            save_needed = True

        # Override with Environment Variables
        for key, default_value in self.DEFAULT_CONFIG.items():
            env_key = f"SCROLLARR_{key.upper()}"
            env_val = os.getenv(env_key)
            if env_val is not None:
                # Type conversion
                if isinstance(default_value, bool):
                     config[key] = env_val.lower() in ('true', '1', 'yes')
                elif isinstance(default_value, int):
                    try:
                        config[key] = int(env_val)
                    except ValueError:
                        pass
                elif isinstance(default_value, float):
                    try:
                        config[key] = float(env_val)
                    except ValueError:
                        pass
                else:
                    config[key] = env_val

        # Save if we made structural changes or generated keys
        if save_needed:
            self.save_config(config)

        return config

    def save_config(self, config=None):
        """Saves configuration to file."""
        if config is None:
            config = self.config

        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            self.config = config
            logger.info("Configuration saved.")
        except Exception as e:
            logger.error(f"Failed to save config file: {e}")

    def get(self, key, default=None):
        """Gets a configuration value."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Sets a configuration value and saves to file."""
        self.config[key] = value
        self.save_config()

# Global instance
config_manager = ConfigManager()
