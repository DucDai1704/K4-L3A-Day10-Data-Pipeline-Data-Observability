import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.config import load_settings
from core.utils import read_json
from observability.dashboard import generate_dashboard_html


def main() -> None:
    settings = load_settings()
    baseline = read_json(settings.paths.baseline_metrics)
    corrupted = read_json(settings.paths.corrupted_metrics)
    repaired = read_json(settings.paths.repaired_metrics)
    quality = read_json(settings.paths.baseline_quality_report)
    freshness = read_json(settings.paths.freshness_report)

    output_path = settings.paths.project_dir / "data" / "reports" / "dashboard.html"
    generate_dashboard_html(
        output_path=output_path,
        baseline_metrics=baseline,
        corrupted_metrics=corrupted,
        repaired_metrics=repaired,
        quality_report=quality,
        freshness_report=freshness,
    )
    print(f"✅ Dashboard generated successfully: {output_path}")


if __name__ == "__main__":
    main()
