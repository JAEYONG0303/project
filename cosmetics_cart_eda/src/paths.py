"""공통 경로. 원본 zip 위치는 환경변수 COSMETICS_ZIP 으로 바꿀 수 있다."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ZIP = Path(os.environ.get("COSMETICS_ZIP", ROOT / "raw" / "archive.zip"))
SAMPLE_DIR = ROOT / "sample"; SAMPLE = SAMPLE_DIR / "events_sample_2pct.csv"
WORK = ROOT / "work"          # 중간 산출물(pickle, json). git 제외
TABLEAU = ROOT / "tableau"
for d in (SAMPLE_DIR, WORK, TABLEAU): d.mkdir(parents=True, exist_ok=True)
