import json
from pathlib import Path

_POLICIES_DIR = Path(__file__).parent


def render_policy(template_name: str, **kwargs) -> dict:
    """Load a JSON policy template and substitute {placeholder} variables.

    Args:
        template_name: Filename (e.g. "replication_role.json") inside policies/.
        **kwargs: Placeholder values to substitute.

    Returns:
        Parsed dict with all placeholders replaced.
    """
    text = (_POLICIES_DIR / template_name).read_text()
    for key, value in kwargs.items():
        text = text.replace(f"{{{key}}}", value)
    return json.loads(text)
