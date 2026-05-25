from pathlib import Path

settings_path = Path("config/settings.py")
text = settings_path.read_text(encoding="utf-8")

append_block = 