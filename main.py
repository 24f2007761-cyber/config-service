
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def normalize_key(key):
    key = str(key).strip().lower()

    if key.startswith("app_"):
        key = key[4:]

    if key == "num_workers":
        key = "workers"

    return key


def normalize_config(data):
    result = {}

    for key, value in data.items():
        if value is not None:
            result[normalize_key(key)] = value

    return result


def convert_type(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value

        return str(value).strip().lower() in (
            "true", "1", "yes", "on"
        )

    return str(value)


@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    # 1. Defaults
    config = DEFAULTS.copy()

    # 2. Environment-specific YAML
    env_name = os.getenv("APP_ENV", "development")
    yaml_file = Path(f"config.{env_name}.yaml")

    if yaml_file.exists():
        with yaml_file.open("r", encoding="utf-8") as file:
            yaml_data = yaml.safe_load(file) or {}

        config.update(normalize_config(yaml_data))

    # 3. .env file
    env_file = Path(".env")

    if env_file.exists():
        dotenv_data = dotenv_values(env_file)
        config.update(normalize_config(dotenv_data))

    # 4. OS environment variables
    os_config = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("APP_")
    }

    config.update(normalize_config(os_config))

    # 5. CLI overrides
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        config[normalize_key(key)] = value

    # Type conversion
    result = {
        key: convert_type(key, value)
        for key, value in config.items()
    }

    # Hide the API key
    result["api_key"] = "****"

    return result