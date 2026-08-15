from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "evaluation" / "model-robustness-matrix.json"
MODELITO_PIN = "15b616ca02de50436a026865ee04500e3561b932"


def _run(command: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=check)


def _modelito_available() -> bool:
    return shutil.which("modelito-doctor") is not None and shutil.which("modelito-benchmark-local") is not None


def ensure_modelito(*, allow_install: bool = True) -> dict[str, Any]:
    if _modelito_available():
        return {"status": "present", "doctor": shutil.which("modelito-doctor"), "benchmark": shutil.which("modelito-benchmark-local")}
    if not allow_install:
        raise RuntimeError("Modelito CLI is missing and installation was disabled")

    sibling = ROOT.parent / "modelito"
    if (sibling / "pyproject.toml").exists():
        target = f"{sibling}[ollama]"
        source = str(sibling)
    else:
        target = f"modelito[ollama] @ git+https://github.com/krahd/modelito.git@{MODELITO_PIN}"
        source = f"krahd/modelito@{MODELITO_PIN}"

    result = _run([sys.executable, "-m", "pip", "install", target])
    if result.returncode != 0 or not _modelito_available():
        raise RuntimeError(f"Could not install Modelito from {source}: {result.stderr.strip()}")
    return {
        "status": "installed",
        "source": source,
        "stdout": result.stdout.strip(),
        "doctor": shutil.which("modelito-doctor"),
        "benchmark": shutil.which("modelito-benchmark-local"),
    }


def _ollama_models() -> set[str]:
    if shutil.which("ollama") is None:
        raise RuntimeError("Ollama CLI is not installed or is not on PATH")
    result = _run(["ollama", "list"])
    if result.returncode != 0:
        raise RuntimeError(f"ollama list failed: {result.stderr.strip()}")
    models: set[str] = set()
    for line in result.stdout.splitlines()[1:]:
        fields = line.split()
        if fields:
            models.add(fields[0])
    return models


def ensure_ollama_model(model: str, *, allow_pull: bool = True) -> dict[str, Any]:
    present = _ollama_models()
    if model in present:
        return {"model": model, "status": "present"}
    if not allow_pull:
        raise RuntimeError(f"Required Ollama model is missing: {model}")
    result = subprocess.run(["ollama", "pull", model], text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ollama pull failed for {model}")
    after = _ollama_models()
    if model not in after:
        raise RuntimeError(f"Ollama pull returned success but {model} is still absent")
    return {"model": model, "status": "pulled"}


def doctor(model: str) -> dict[str, Any]:
    # Modelito <=1.4.6 exposes modelito-doctor as an entry point to a parser that
    # still expects the `doctor` subcommand. Newer Modelito accepts both forms.
    # Use the backwards-compatible form so an already-installed 1.4.6 does not
    # make the experiment fail before it can update or run.
    result = _run(["modelito-doctor", "doctor", "--provider", "ollama", "--model", model])
    return {
        "model": model,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _known_modelito_listing_false_negative(model: str, doctor_state: dict[str, Any]) -> bool:
    """Return True only for the known Ollama-list formatting false negative.

    Some installed Modelito versions compare the requested model against raw
    `ollama list` rows instead of bare model names. In that case the diagnostic
    says `requested model not found` while visibly listing the exact requested
    tag. Exact presence has already been independently verified by
    `ensure_ollama_model`, so this specific doctor failure is safe to retain as
    a warning rather than aborting the experiment.
    """
    diagnostic = "\n".join(
        [doctor_state.get("stdout", ""), doctor_state.get("stderr", "")]
    )
    return (
        doctor_state.get("returncode") != 0
        and "requested model not found" in diagnostic.lower()
        and model in diagnostic
        and model in _ollama_models()
    )


def prepare(matrix_path: Path, *, install_modelito: bool = True, pull_models: bool = True) -> dict[str, Any]:
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    modelito = ensure_modelito(allow_install=install_modelito)
    models = []
    for spec in matrix["models"]:
        tag = spec["ollama_model"]
        state = ensure_ollama_model(tag, allow_pull=pull_models)
        state["doctor"] = doctor(tag)
        if state["doctor"]["returncode"] != 0:
            if _known_modelito_listing_false_negative(tag, state["doctor"]):
                state["doctor_warning"] = (
                    "Known Modelito Ollama-list formatting false negative: the exact "
                    "tag is independently verified by `ollama list`; continuing while "
                    "retaining the failed doctor diagnostic in the manifest."
                )
            else:
                diagnostic = state["doctor"]["stderr"] or state["doctor"]["stdout"]
                raise RuntimeError(f"Modelito doctor failed for {tag}: {diagnostic}")
        models.append(state)
    return {"modelito": modelito, "models": models}


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure Modelito and the frozen Ollama RTCA model matrix are available.")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--no-install-modelito", action="store_true")
    parser.add_argument("--no-pull", action="store_true")
    args = parser.parse_args()
    payload = prepare(
        args.matrix,
        install_modelito=not args.no_install_modelito,
        pull_models=not args.no_pull,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
