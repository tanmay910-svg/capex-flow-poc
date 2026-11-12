
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

COLUMN_MAPPING_FILE = CONFIG_DIR / "column_mapping.json"
VALIDATION_RULES_FILE = CONFIG_DIR / "validation_rules.json"


def load_json_config(file_path):
    """Load and validate a JSON configuration file."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {file_path}"
        )

    try:
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in {file_path.name}: {error}"
        ) from error


def load_column_mapping():
    return load_json_config(COLUMN_MAPPING_FILE)


def load_validation_rules():
    return load_json_config(VALIDATION_RULES_FILE)


def load_all_configs():
    return {
        "column_mapping": load_column_mapping(),
        "validation_rules": load_validation_rules()
    }


if __name__ == "__main__":
    configs = load_all_configs()

    print("Configuration files loaded successfully!")

    print(
        "Available mapping sections:",
        list(configs["column_mapping"].keys())
    )

    print(
        "Available validation sections:",
        list(configs["validation_rules"].keys())
    )
