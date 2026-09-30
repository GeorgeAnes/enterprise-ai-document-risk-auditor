"""Clone the two public datasets into data/raw/ (git-ignored). Nothing from them is committed or redistributed."""
import subprocess
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
REPOS = {
    "cuad-atticus": "https://github.com/TheAtticusProject/cuad",  # data.zip holds CUADv1.json
    "squad-explorer": "https://github.com/rajpurkar/SQuAD-explorer",  # dataset/dev-v1.1.json
}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in REPOS.items():
        if (RAW / name).exists():
            print(f"{name}: already at {RAW / name}")
        elif subprocess.run(["git", "clone", "--depth", "1", url, str(RAW / name)]).returncode:
            sys.exit(f"git clone failed for {url}")
