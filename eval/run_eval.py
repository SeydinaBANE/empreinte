"""Execute l'evaluation d'extraction sur le jeu de donnees labellise.

En mode demo (provider deterministe), valide le harnais de bout en bout sans GPU :
    python eval/run_eval.py
En production, pointer EMPREINTE_LLM_API_BASE vers le vLLM pour mesurer le vrai modele.
Sort en erreur si le F1 passe sous le seuil (gate qualite, informatif en CI).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from empreinte.evaluation import EvalReport, score_extraction  # noqa: E402
from empreinte.logging import configure_logging, get_logger  # noqa: E402
from empreinte.schemas import ExtractedIndicatorDraft  # noqa: E402
from empreinte.services import build_pipeline  # noqa: E402

logger = get_logger(__name__)

_DATASET_DIR = Path(__file__).parent / "dataset"
_F1_THRESHOLD = 0.8


def _load_gold(path: Path) -> tuple[str, list[ExtractedIndicatorDraft]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    gold = [ExtractedIndicatorDraft.model_validate(item) for item in data["indicators"]]
    return data["doc_id"], gold


async def _evaluate_case(path: Path) -> EvalReport:
    doc_id, gold = _load_gold(path)
    pipeline = build_pipeline()
    document = await pipeline.documents.get(doc_id)
    if document is None:
        raise SystemExit(f"document de demo introuvable: {doc_id}")
    extraction = await pipeline.extractor.extract(document)
    return score_extraction(extraction.indicators, gold)


def main() -> None:
    configure_logging()
    worst_f1 = 1.0
    for path in sorted(_DATASET_DIR.glob("*.json")):
        report = asyncio.run(_evaluate_case(path))
        worst_f1 = min(worst_f1, report.f1)
        logger.info(
            "eval_case",
            case=path.stem,
            precision=report.precision,
            recall=report.recall,
            f1=report.f1,
            value_accuracy=report.value_accuracy,
        )
    if worst_f1 < _F1_THRESHOLD:
        logger.error("eval_below_threshold", f1=worst_f1, threshold=_F1_THRESHOLD)
        sys.exit(1)


if __name__ == "__main__":
    main()
