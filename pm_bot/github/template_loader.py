"""Load GitHub issue-form templates (YAML) from the vendored snapshot.

v0 intentionally vendors templates into this repo so Codex tasks have reliable access,
without needing multi-repo checkout.

Later (v1+), add a sync script that fetches from phys-sims/.github at a pinned ref.
"""

from pathlib import Path
import yaml

DEFAULT_TEMPLATE_DIR = (
    Path(__file__).resolve().parents[2] / "vendor" / "dotgithub" / "ISSUE_TEMPLATE"
)


def load_template(name: str, template_dir: Path = DEFAULT_TEMPLATE_DIR) -> dict:
    path = template_dir / f"{name}.yml"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return yaml.safe_load(path.read_text())


def list_templates(template_dir: Path = DEFAULT_TEMPLATE_DIR) -> list[str]:
    return sorted([p.stem for p in template_dir.glob("*.yml")])
