import argparse
from pathlib import Path

from ledgerly.generate import build, write

p = argparse.ArgumentParser()
p.add_argument("--seed", type=int, default=42)
p.add_argument("--out", type=Path, default=Path("data"))
if __name__ == "__main__":
    a = p.parse_args()
    write(build(a.seed), a.out)
    print(f"Synthetic Ledgerly data written to {a.out}; seed={a.seed}")
