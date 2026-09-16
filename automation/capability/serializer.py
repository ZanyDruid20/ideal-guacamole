from pathlib import Path
from .schema import Capability

# Read a saved JSON artifact and validate it as a Capability before returning it.
def load_capability(path: Path) -> Capability:
    return Capability.model_validate_json(path.read_text())

# Create the destination folder and save the capability as readable JSON.
def save_capability(capability: Capability, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(capability.model_dump_json(indent=2))

