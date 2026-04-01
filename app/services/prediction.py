"""Symbol prediction service — MVP stub.

Implements a simple frequency + bigram model for next-symbol prediction.
Will be enhanced with ML models (BERTimbau) and Claude API via Bedrock.
"""

from collections import defaultdict


class PredictionService:
    """Predicts next symbols based on usage frequency and bigram co-occurrence."""

    def __init__(self) -> None:
        # symbol_id -> total selection count
        self._frequency: dict[str, int] = defaultdict(int)
        # (prev_symbol_id, next_symbol_id) -> co-occurrence count
        self._bigrams: dict[tuple[str, str], int] = defaultdict(int)

    def record_selection(self, symbol_id: str, prev_symbol_id: str | None = None) -> None:
        """Record a symbol selection to update frequency and bigram models."""
        self._frequency[symbol_id] += 1
        if prev_symbol_id:
            self._bigrams[(prev_symbol_id, symbol_id)] += 1

    def predict(
        self,
        prev_symbol_id: str | None = None,
        limit: int = 8,
    ) -> list[str]:
        """Return top predicted symbol IDs.

        If prev_symbol_id is given, blends bigram scores (70%) with frequency (30%).
        Otherwise falls back to pure frequency ranking.
        """
        if not self._frequency:
            return []

        if prev_symbol_id:
            bigram_scores: dict[str, float] = {}
            for (prev, nxt), count in self._bigrams.items():
                if prev == prev_symbol_id:
                    bigram_scores[nxt] = count

            max_bigram = max(bigram_scores.values()) if bigram_scores else 1
            max_freq = max(self._frequency.values()) if self._frequency else 1

            combined: dict[str, float] = {}
            all_symbols = set(self._frequency.keys()) | set(bigram_scores.keys())
            for sym in all_symbols:
                b_score = bigram_scores.get(sym, 0) / max_bigram
                f_score = self._frequency.get(sym, 0) / max_freq
                combined[sym] = 0.7 * b_score + 0.3 * f_score

            ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)
            return [sym for sym, _ in ranked[:limit]]

        # Pure frequency fallback
        ranked = sorted(self._frequency.items(), key=lambda x: x[1], reverse=True)
        return [sym for sym, _ in ranked[:limit]]
