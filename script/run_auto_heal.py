import sys
from pathlib import Path
import pandas as pd

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.config import load_settings
from pipelines.auto_heal import run_self_healing_pipeline


def main() -> None:
    settings = load_settings()
    # Test auto-healing with corrupted data if available, otherwise clean data
    if settings.paths.corrupted_clean_json.exists():
        test_df = pd.read_json(settings.paths.corrupted_clean_json)
        source = "corrupted_incoming_batch"
    else:
        test_df = pd.read_json(settings.paths.clean_json)
        source = "clean_incoming_batch"

    result = run_self_healing_pipeline(test_df, source_label=source)
    print(f"Self-healing executed successfully: action={result['action_taken']}")


if __name__ == "__main__":
    main()
