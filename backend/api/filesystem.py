import os
import string
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "exemplo-dados"

HIDDEN_PREFIXES = ("$", ".")


def _entry(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "is_dir": path.is_dir(),
        "size": None if path.is_dir() else stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def _drives() -> List[dict]:
    out = []
    if os.name == "nt":
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if Path(drive).exists():
                out.append({
                    "name": f"Unidade {letter}:",
                    "path": drive,
                    "is_dir": True,
                    "size": None,
                    "modified": None,
                })
    else:
        home = Path.home()
        out.append({"name": "Home", "path": str(home), "is_dir": True, "size": None, "modified": None})
        out.append({"name": "/", "path": "/", "is_dir": True, "size": None, "modified": None})
    return out


def _shortcuts() -> List[dict]:
    shortcuts = []
    if EXAMPLES_DIR.exists():
        shortcuts.append({"name": "Dados de Exemplo", "path": str(EXAMPLES_DIR)})
    shortcuts.append({"name": "Pasta do Projeto", "path": str(PROJECT_ROOT)})
    return shortcuts


@router.get("/list")
def list_directory(path: Optional[str] = Query(None, description="Caminho do diretório a listar")):
    """Lista unidades, pastas e arquivos para o seletor de caminho."""
    if not path or not path.strip():
        return {
            "path": "",
            "parent": None,
            "entries": _drives(),
            "shortcuts": _shortcuts(),
        }

    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Caminho não encontrado: {path}")

    if p.is_file():
        p = p.parent

    try:
        children = list(p.iterdir())
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Sem permissão para acessar: {p}")

    entries = []
    for child in children:
        if child.name.startswith(HIDDEN_PREFIXES):
            continue
        try:
            entries.append(_entry(child))
        except OSError:
            continue

    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))

    parent = ""
    if p.parent != p:
        parent = str(p.parent)

    return {
        "path": str(p),
        "parent": parent,
        "entries": entries,
        "shortcuts": _shortcuts(),
    }
