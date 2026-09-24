"""Lossless q-gram candidate generation for difflib.SequenceMatcher.

Python 3.10+; standard library only. Input titles MUST already be normalized
exactly as in the existing application, and kept in the baseline pair order.
No records, identifiers, or groups are modified.

The callback exclude_pair(i, j) MUST implement the application's EXISTING
identifier/group exclusion rule on a stable snapshot. i < j always.

For s=len(a)+len(b), let h be the smallest matching-character count accepted by
Python's floating-point expression 2.0*h/s >= threshold. A true match must have
multiset q-gram overlap >= max(0, h-(q-1)*(s-2*h+1)).

Candidate generation uses: exact length feasibility, a lossless rare-token
prefix probe against FULL postings, and exact multiset-overlap counts computed
using Python integer bitsets. Final acceptance is the original difflib ratio,
with autojunk=True and the original argument direction. This is not LSH.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from math import isfinite
from time import perf_counter
from typing import Callable, Iterator, NamedTuple, Sequence


@dataclass
class JoinStats:
    items: int = 0
    total_pairs: int = 0
    length_pairs: int = 0
    prefix_pairs: int = 0
    qgram_pairs: int = 0
    zero_bound_pairs: int = 0
    excluded_pairs: int = 0  # Excluded among qgram survivors, not all library pairs.
    character_rejected: int = 0
    ratio_calls: int = 0
    matches: int = 0
    token_types: int = 0
    token_occurrences: int = 0
    prefix_token_lookups: int = 0
    bitset_additions: int = 0
    build_seconds: float = 0.0
    scan_seconds: float = 0.0


class ReviewPair(NamedTuple):
    i: int
    j: int
    ratio: float


def qgram_counts(text: str, q: int) -> Counter[str]:
    """Unpadded, contiguous Python-str code-point q-grams, with multiplicity."""
    if not isinstance(q, int) or isinstance(q, bool) or q < 1:
        raise ValueError("q must be a positive integer")
    return Counter(text[p:p + q] for p in range(max(0, len(text) - q + 1)))


def minimum_matches(total: int, threshold: float = 0.9) -> int:
    """Exact integer cutoff for the same float comparison as difflib.ratio.

    Returns total//2+1 if no integer matching count can pass. Empty vs empty
    has ratio 1.0 and requires zero matches. No floating-point ceil is used.
    """
    if total < 0:
        raise ValueError("total must be nonnegative")
    if not isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be finite and in [0, 1]")
    if total == 0:
        return 0
    lo, hi = 0, total // 2 + 1
    while lo < hi:
        mid = (lo + hi) // 2
        if 2.0 * mid / total >= threshold:
            hi = mid
        else:
            lo = mid + 1
    return lo


def overlap_bound(m: int, n: int, q: int = 3,
                  threshold: float = 0.9) -> int:
    """Necessary MULTISET overlap; call length feasibility separately."""
    if m < 0 or n < 0 or q < 1:
        raise ValueError("lengths must be nonnegative and q must be positive")
    h = minimum_matches(m + n, threshold)
    return max(0, h - (q - 1) * (m + n - 2 * h + 1))


def _at_least(planes: list[int], threshold: int, mask: int) -> int:
    """Bit j of planes[k] is bit k of record j's overlap count."""
    if not mask or threshold >= (1 << len(planes)):
        return 0
    if threshold <= 0:
        return mask
    # Scan low to high. At each new high bit, > decides the comparison;
    # equality delegates to the previously computed lower-bit comparison.
    result = mask
    for k, plane in enumerate(planes):
        if (threshold >> k) & 1:
            result &= plane
        else:
            result |= plane
    return result & mask


class LosslessQGramIndex:
    """Read-only snapshot index. No normalization and no database writes."""

    def __init__(self, titles: Sequence[str], *, q: int = 3,
                 threshold: float = 0.9) -> None:
        started = perf_counter()
        if isinstance(titles, (str, bytes)):
            raise TypeError("titles must be a sequence of normalized strings")
        if not isinstance(q, int) or isinstance(q, bool) or q < 1:
            raise ValueError("q must be a positive integer")
        if not isfinite(threshold) or not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be finite and in [0, 1]")
        self.titles = tuple(titles)
        if any(not isinstance(s, str) for s in self.titles):
            raise TypeError("every normalized title must be a str")
        self.q, self.threshold = q, threshold
        self.lengths = tuple(map(len, self.titles))
        self.character_counts = tuple(Counter(s) for s in self.titles)
        self._h_cache: dict[int, int] = {}
        self._all = (1 << len(self.titles)) - 1

        # Canonical occurrence tokens (gram, 1), ..., (gram, count).
        # Their ordinary set intersection equals multiset gram intersection.
        postings: dict[tuple[str, int], int] = {}
        raw_tokens: list[list[tuple[str, int]]] = []
        length_masks: dict[int, int] = defaultdict(int)
        for i, text in enumerate(self.titles):
            bit = 1 << i
            length_masks[len(text)] |= bit
            tokens = []
            for gram, count in qgram_counts(text, q).items():
                for r in range(1, count + 1):
                    token = (gram, r)
                    tokens.append(token)
                    postings[token] = postings.get(token, 0) | bit
            raw_tokens.append(tokens)

        # Global, deterministic rare-first ordering. No stop-gram removal.
        vocabulary = sorted(postings,
                            key=lambda t: (postings[t].bit_count(), t))
        rank = {token: k for k, token in enumerate(vocabulary)}
        self._postings = tuple(postings[token] for token in vocabulary)
        self._tokens = tuple(tuple(sorted(rank[t] for t in tokens))
                             for tokens in raw_tokens)

        # Build length plans once. Complexity O(K^2), K=distinct lengths;
        # typically small for titles. Thresholds are NOT assumed monotonic.
        self._plans: dict[int, tuple[tuple[int, int], ...]] = {}
        for n in length_masks:
            masks_by_bound: dict[int, int] = defaultdict(int)
            for m, mask in length_masks.items():
                total = m + n
                h = self._minimum(total)
                if h > min(m, n):
                    continue
                bound = max(0, h - (q - 1) * (total - 2 * h + 1))
                masks_by_bound[bound] |= mask
            self._plans[n] = tuple(sorted(masks_by_bound.items()))
        self.build_seconds = perf_counter() - started

    def _minimum(self, total: int) -> int:
        value = self._h_cache.get(total)
        if value is None:
            value = minimum_matches(total, self.threshold)
            self._h_cache[total] = value
        return value

    def iter_candidates(self, *, stats: JoinStats | None = None
                        ) -> Iterator[tuple[int, int]]:
        """Yield all q-gram-feasible i<j in original pair order, no exclusions.

        stats is an accumulator: pass a fresh JoinStats for each complete scan.
        Bound-zero buckets are explicitly enumerated, never silently dropped.
        """
        if stats is None:
            stats = JoinStats()
        size = len(self.titles)
        stats.items = size
        stats.total_pairs = size * (size - 1) // 2
        stats.build_seconds = self.build_seconds
        stats.token_types = len(self._postings)
        stats.token_occurrences = sum(map(len, self._tokens))
        for i, tokens in enumerate(self._tokens):
            later = self._all & ~((1 << (i + 1)) - 1)
            positive_groups = []
            positive_mask = fallback = 0
            for bound, mask in self._plans[self.lengths[i]]:
                mask &= later
                if not mask:
                    continue
                if bound == 0:
                    fallback |= mask
                else:
                    positive_groups.append((bound, mask))
                    positive_mask |= mask
            stats.length_pairs += (positive_mask | fallback).bit_count()
            stats.zero_bound_pairs += fallback.bit_count()
            candidates = fallback

            if positive_mask:
                # Plans are sorted, so this is min bound among actual partners.
                smallest_bound = positive_groups[0][0]
                prefix_size = len(tokens) - smallest_bound + 1
                active = 0
                if prefix_size > 0:
                    for token in tokens[:prefix_size]:
                        active |= self._postings[token]
                    stats.prefix_token_lookups += min(prefix_size, len(tokens))
                active &= positive_mask
                stats.prefix_pairs += active.bit_count()
                if active:
                    # Add all occurrence-token postings as bit-sliced integers.
                    # This obtains the EXACT multiset overlap for all active
                    # records simultaneously; no Python loop over their pairs.
                    planes: list[int] = []
                    for token in tokens:
                        carry = self._postings[token] & active
                        if not carry:
                            continue
                        stats.bitset_additions += 1
                        k = 0
                        while carry:
                            if k == len(planes):
                                planes.append(carry)
                                break
                            old = planes[k]
                            planes[k] = old ^ carry
                            carry &= old
                            k += 1
                    for bound, mask in positive_groups:
                        candidates |= _at_least(planes, bound, mask & active)
            stats.prefix_pairs += fallback.bit_count()
            stats.qgram_pairs += candidates.bit_count()
            while candidates:
                lowbit = candidates & -candidates
                yield i, lowbit.bit_length() - 1
                candidates ^= lowbit

    def iter_matches(self, *, exclude_pair: Callable[[int, int], bool],
                     stats: JoinStats | None = None) -> Iterator[ReviewPair]:
        """Final difflib adjudication; mandatory existing exclusion callback.

        Always score SequenceMatcher(None, titles[i], titles[j]) for i<j.
        Reuse only the second-sequence cache; do not reverse arguments.
        stats.scan_seconds includes the consumer's work between yielded items.
        """
        if not callable(exclude_pair):
            raise TypeError("exclude_pair must be the existing exclusion rule")
        if stats is None:
            stats = JoinStats()
        started = perf_counter()
        matchers: dict[int, SequenceMatcher] = {}
        try:
            for i, j in self.iter_candidates(stats=stats):
                if exclude_pair(i, j):
                    stats.excluded_pairs += 1
                    continue
                ca, cb = self.character_counts[i], self.character_counts[j]
                if len(ca) > len(cb):
                    ca, cb = cb, ca
                overlap = sum(min(count, cb.get(char, 0))
                              for char, count in ca.items())
                if overlap < self._minimum(self.lengths[i] + self.lengths[j]):
                    stats.character_rejected += 1
                    continue
                matcher = matchers.get(j)
                if matcher is None:
                    matcher = SequenceMatcher(None, "", self.titles[j],
                                              autojunk=True)
                    matchers[j] = matcher
                matcher.set_seq1(self.titles[i])
                stats.ratio_calls += 1
                score = matcher.ratio()
                if score >= self.threshold:
                    stats.matches += 1
                    yield ReviewPair(i, j, score)
        finally:
            stats.scan_seconds += perf_counter() - started


def review_pairs(titles: Sequence[str], *,
                 exclude_pair: Callable[[int, int], bool], q: int = 3,
                 threshold: float = 0.9,
                 stats: JoinStats | None = None) -> list[ReviewPair]:
    """Convenience wrapper returning the human-review list only."""
    index = LosslessQGramIndex(titles, q=q, threshold=threshold)
    return list(index.iter_matches(exclude_pair=exclude_pair, stats=stats))
