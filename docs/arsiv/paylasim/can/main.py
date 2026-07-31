"""Orkestratoru komut satirindan denemek icin kucuk giris noktasi.

Kullanim:
    python main.py "domates icin ne zaman sulamaliyim"
"""
from __future__ import annotations

import sys

from agents.orchestrator import build_graph


def main() -> None:
    query = " ".join(sys.argv[1:]) or "bu tarlaya hangi urunu ekmeliyim"
    app = build_graph()
    state = app.invoke({"query": query})
    result = state.get("result", {})
    print(f"Niyet   : {state.get('intent')}")
    print(f"Agent   : {result.get('agent')}")
    print(f"Cevap   : {result.get('message')}")


if __name__ == "__main__":
    main()
