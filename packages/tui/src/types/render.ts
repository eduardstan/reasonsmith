/**
 * The one place any rendering words an evidence basis.
 *
 * The wording is `basis_sentence` in `src/reasonsmith/render.py`, quoted, and the rule it exists to
 * keep is `docs/semantics.md` §10's: **a basis is a kind and never a rank**. It keeps that rule by
 * saying, wherever a basis is shown, which rungs the duty cannot reach and that the reason is the
 * duty's rather than the system's — a bare word beside a rung word would be read as a fifth rung.
 *
 * What a reader must not break:
 *
 *   - **The basis sentence is rendered in exactly one place.** A second wording here would be the
 *     second-source-of-truth problem this module exists to prevent.
 *   - **The three sentences are the Python's, character for character.** They were a paraphrase
 *     once, under a comment claiming they were verbatim, which is the worse of the two failures: a
 *     reader who checked the citation would have found a file that said something else. If the
 *     Python's wording changes, this file changes with it — it is not a place to improve a sentence.
 *   - **The behavioural basis has no sentence, and that is the Python's answer, not a gap.** It
 *     reaches every rung, so there is no ceiling to explain, and a sentence on every result is the
 *     noise that makes the other three unreadable. `null` here means *say nothing*; a caller that
 *     substituted a default would put the noise back.
 */

import type { EvidenceBasis } from "./verdict.ts"

/**
 * `_BASIS_SENTENCES` from `src/reasonsmith/render.py`, verbatim. Behavioural is absent there and
 * absent here — `basis_sentence` returns `None` for it.
 */
const BASIS_SENTENCES: Partial<Record<EvidenceBasis, string>> = {
  relational:
    "relational — this duty is a property of a pair of executions, and a decision record holds " +
    "one. No length of decision log observes it, so the rungs it can reach are probed and " +
    "proved; a system exposing only a log cannot discharge it, and that is a fact about the " +
    "kind of property and not about how much the system exposed",
  artifact:
    "artifact — this duty is measured against the inference artefact behind a decision rather " +
    "than against what the system decided. No trace holds that artefact and the enumeration is " +
    "exact only on the one artefact it ran over, so the rungs above unattainable are recounted " +
    "and probed, and neither observed nor proved is reachable however much the system exposes. " +
    "Which of the two a verdict reaches is a fact about the artefact and not about the search: " +
    "probed measures a reason set enumerated from a model encoding, recounted measures one the " +
    "system recounted about its own inference",
  assessment:
    "assessment — this duty rests on how an open-textured predicate applies, which a named " +
    "authority settles and no engine here does. No rung of the strength lattice ranks it, " +
    "because the lattice ranks ways of interrogating a system and no system was interrogated",
}

/** The basis sentence, or `null` where the Python renders none. */
export function basisSentence(basis: EvidenceBasis): string | null {
  return BASIS_SENTENCES[basis] ?? null
}
