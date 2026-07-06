"""Conservative Verse workspace helpers for UEFN projects."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VERSE_SUFFIX = ".verse"
PROJECT_MARKERS = (".uefnproject", ".uproject")
TEMPLATE_NAMES = ("basic_device", "npc_behavior")


BASIC_DEVICE_TEMPLATE = """using {{ /Fortnite.com/Devices }}
using {{ /Verse.org/Simulation }}

{class_name} := class(creative_device):

    OnBegin<override>()<suspends>:void =
        Print("{display_name} ready")
"""


NPC_BEHAVIOR_TEMPLATE = """using {{ /Fortnite.com/AI }}
using {{ /Verse.org/Simulation }}

{class_name} := class(npc_behavior):

    OnBegin<override>()<suspends>:void =
        Print("{display_name} NPC behavior ready")
"""


class WorkspaceError(ValueError):
    """Raised when a workspace operation is outside the project boundary."""


@dataclass(frozen=True)
class VerseWorkspace:
    root: Path

    @classmethod
    def discover(cls, start: str | Path | None = None) -> "VerseWorkspace":
        env_root = os.environ.get("UEFN_PROJECT_ROOT")
        if env_root:
            return cls(Path(env_root).resolve())

        current = Path(start or os.getcwd()).resolve()
        candidates = [current, *current.parents]
        for candidate in candidates:
            if any(candidate.glob(f"*{marker}") for marker in PROJECT_MARKERS):
                return cls(candidate)
            if (candidate / "Verse").is_dir() or (candidate / "Plugins").is_dir():
                return cls(candidate)
        return cls(current)

    def resolve_safe(self, path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError(f"Path is outside UEFN project root: {resolved}") from exc
        return resolved

    def verse_roots(self) -> list[Path]:
        roots: list[Path] = []
        for relative in ("Verse", "Plugins"):
            path = self.root / relative
            if path.is_dir():
                roots.append(path)
        if not roots:
            roots.append(self.root)
        return roots

    def list_verse_files(self) -> list[dict[str, str]]:
        files: list[Path] = []
        for root in self.verse_roots():
            files.extend(root.rglob(f"*{VERSE_SUFFIX}"))
        unique = sorted({path.resolve() for path in files if path.is_file()})
        return [{"path": str(path), "relative_path": str(path.relative_to(self.root))} for path in unique]

    def read_verse_file(self, path: str) -> dict[str, str]:
        resolved = self.resolve_safe(path)
        if resolved.suffix != VERSE_SUFFIX:
            raise WorkspaceError(f"Not a Verse file: {resolved}")
        return {"path": str(resolved), "relative_path": str(resolved.relative_to(self.root)), "content": resolved.read_text(encoding="utf-8")}

    def write_verse_file(self, path: str, content: str, overwrite: bool = True) -> dict[str, Any]:
        resolved = self.resolve_safe(path)
        if resolved.suffix != VERSE_SUFFIX:
            raise WorkspaceError(f"Verse files must end with {VERSE_SUFFIX}: {resolved}")
        if resolved.exists() and not overwrite:
            raise WorkspaceError(f"Verse file already exists: {resolved}")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8", newline="\n")
        return {
            "path": str(resolved),
            "relative_path": str(resolved.relative_to(self.root)),
            "bytes": len(content.encode("utf-8")),
        }

    def create_device(self, name: str, template: str = "basic_device", directory: str = "Verse", overwrite: bool = False) -> dict[str, Any]:
        content = render_template(template, name)
        class_name = to_verse_identifier(name)
        path = Path(directory) / f"{class_name}.verse"
        return self.write_verse_file(str(path), content, overwrite=overwrite)

    def context(self) -> dict[str, Any]:
        return {
            "project_root": str(self.root),
            "verse_roots": [str(path) for path in self.verse_roots()],
            "verse_file_count": len(self.list_verse_files()),
            "templates": list(TEMPLATE_NAMES),
        }


def to_verse_identifier(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "generated_device"
    if cleaned[0].isdigit():
        cleaned = f"device_{cleaned}"
    return cleaned.lower()


def render_template(template: str, name: str) -> str:
    class_name = to_verse_identifier(name)
    display_name = name.strip() or class_name
    if template == "basic_device":
        return BASIC_DEVICE_TEMPLATE.format(class_name=class_name, display_name=display_name)
    if template == "npc_behavior":
        return NPC_BEHAVIOR_TEMPLATE.format(class_name=class_name, display_name=display_name)
    raise WorkspaceError(f"Unknown Verse template '{template}'. Available: {', '.join(TEMPLATE_NAMES)}")


def get_templates() -> dict[str, str]:
    return {
        "basic_device": BASIC_DEVICE_TEMPLATE.format(class_name="example_device", display_name="Example Device"),
        "npc_behavior": NPC_BEHAVIOR_TEMPLATE.format(class_name="example_npc_behavior", display_name="Example NPC Behavior"),
    }
