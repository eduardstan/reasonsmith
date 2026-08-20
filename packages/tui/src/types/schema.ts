/**
 * The JSON contract `reasonsmith check --json` emits.
 *
 * `docs/semantics.md` §7 names this output *the complete machine record, deliberately unprojected* —
 * it was built so that another program could render it. The TUI is that other program: it never
 * recomputes a verdict, never reads a trace, and never asks the Python anything except *one*
 * subprocess call whose stdout it parses.
 *
 * The contract's shape is the Python's `ConformanceReport.toDict()`, and every field here names a
 * key the JSON actually carries. A field the Python does not emit is not declared here; a JSON
 * field the TUI does not need is allowed to be untyped at the parser boundary and discarded.
 *
 * What a reader must not break:
 *   - **The schema version is the JSON shape's, not the package's.** It increments only when a key
 *     is removed, renamed, or changes type or meaning. `parseReport` accepts the version the
 *     TUI was written against and refuses others, with the rejected version in the error.
 *   - **The details bag is intentionally untyped.** It is the place every engine stores whatever
 *     that engine alone produces, and a typed details bag here would force the TUI to track engines
 *     it does not own. The keys the TUI *does* read are listed in `./detail-keys.ts`.
 *   - **No sentence of the report is rebuilt here.** `undeclared_domain_notice` arrives as prose the
 *     Python wrote and is rendered as prose; the TUI does not recompute it from the results it was
 *     derived from. A notice two programs have to keep in step is a notice that drifts, and this one
 *     had already drifted before the key existed.
 *   - **A vocabulary the Python closed is refused at this boundary.** Verdicts, strengths, bases,
 *     finding kinds and the audience flags are all checked here, so an unrecognised value fails at
 *     the parse with the value in the error, rather than reaching a renderer that has no wording for
 *     it and silently shows nothing.
 */

import { checkAudienceBlock, type AudienceBlock } from "./audiences.ts"
import {
  isBasis,
  isOperationalOutcome,
  isStrength,
  isVerdict,
  type EvidenceBasis,
  type OperationalOutcome,
  type StrengthOrNull,
  type Verdict,
} from "./verdict.ts"

/**
 * `JSON_SCHEMA_VERSION` from `src/reasonsmith/report.py`. Bump on the Python side, then here.
 *
 * It is deliberately *not* bumped when a key is added, which is the convention
 * `tests/test_json_schema_version.py` records — so this number cannot tell a record carrying
 * `undeclared_domain_notice` from one emitted before that key existed. The parser therefore names
 * a missing additive key in its own error rather than inferring a version from its absence: a
 * reader is told which key is missing and which Python to run, not handed a renderer that quietly
 * shows less than the run measured.
 */
export const REPORT_SCHEMA_VERSION = 2

/**
 * The conformance report, as Python's `--json` output. Plain data — the TUI never constructs one
 * itself, it parses what the subprocess emits.
 */
export interface ConformanceReport {
  readonly schema_version: number
  readonly pack_id: string
  readonly system_name: string
  readonly system_scope: string | null
  readonly system_domains: readonly string[]
  readonly time_domain: string
  readonly headline: string
  readonly counts: ReportCounts
  readonly results: readonly RequirementResult[]
  readonly limits: string
  /**
   * The one sentence a run owes a reader when domain-limited duties went unchecked, or `null` when
   * none did. **The wording is the Python's and is read, never re-derived here.** The TUI used to
   * rebuild this sentence from `details["skipped_for_undeclared_domain"]`, which made a compliance
   * notice a thing two programs had to keep in step; it drifted in the obvious way, losing the
   * final clause that names where the vocabulary is written down. `null` is a value and not an
   * absence: the declared case is defined rather than missing.
   */
  readonly undeclared_domain_notice: string | null
  /**
   * The projection this record was *asked* for, declared rather than applied — `--json` is the
   * complete machine record and no audience filters it. It is what lets a consumer tell `absent
   * because this audience is not shown it` from `absent because the run never established it`.
   */
  readonly audience: AudienceBlock
}

/**
 * The two rows of counts: binding and interpretive. Each row carries every category the result model
 * can produce, with `0` when the category is empty. A field whose count is `0` is still present —
 * the JSON does not drop empty counts, and the TUI's status bar skips them rather than widening
 * what it expects.
 */
export interface ReportCounts {
  readonly total: number
  readonly binding_total: number
  readonly proved: number
  readonly probed: number
  readonly recounted: number
  readonly observed: number
  readonly violated: number
  readonly inconclusive: number
  readonly not_evaluated: number
  readonly on_an_assessment: number
  readonly unattainable: number
  readonly not_applicable: number
  readonly interpretive_total: number
  readonly interpretive_proved: number
  readonly interpretive_probed: number
  readonly interpretive_recounted: number
  readonly interpretive_observed: number
  readonly interpretive_violated: number
  readonly interpretive_inconclusive: number
  readonly interpretive_not_evaluated: number
  readonly interpretive_on_an_assessment: number
  readonly interpretive_unattainable: number
  readonly interpretive_not_applicable: number
}

/**
 * A finding reported *beside* a result rather than through its verdict.
 *
 * The only kind today is `certificate`, and the thing to understand before rendering one is that
 * **a `FAIL` here may sit beside a `satisfied` duty, and that pairing is the finding rather than a
 * contradiction to reconcile**. The duty was cleared on what its engine could check; the
 * certificate measurement over the same decision failed. A viewer that showed one and suppressed
 * the other would be picking which half of a measured disagreement its reader is allowed to see.
 */
export interface CertificateFinding {
  readonly type: "certificate"
  readonly verdict: "FAIL"
  /** Index of the decision the failed certificate was measured over, or `null` if unrecorded. */
  readonly decision_index: number | null
}

export type Finding = CertificateFinding

/**
 * One requirement's result. The fields here are exactly the keys every result carries — no field is
 * optional, every field is what the Python reports. `details` is the bag every engine writes into;
 * the TUI reads only the keys it has a name for.
 */
export interface RequirementResult {
  readonly requirement_id: string
  readonly source_clause: string
  /**
   * The statutory quotation the duty restates, carried through from the pack unchanged — never
   * reflowed, truncated or whitespace-normalised. The pack's copy is the authority and this is a
   * passthrough, which is the whole reason a detail pane may print it: quoting is not this tool
   * speaking about a statute in its own voice. Empty on a result no run stamped.
   */
  readonly verbatim_text: string
  readonly verdict: Verdict
  /** Operational reader-facing outcome; additive to the compatibility verdict/rung pair. */
  readonly outcome: OperationalOutcome
  readonly strength: StrengthOrNull
  readonly signals_required: readonly string[]
  readonly signals_missing: readonly string[]
  readonly evidence_summary: string
  readonly details: Readonly<Record<string, unknown>>
  /** Findings reported beside the verdict; empty when there is nothing to say. */
  readonly findings: readonly Finding[]
  readonly binding: boolean
  readonly scope: string
  readonly domains: readonly string[]
  readonly basis: EvidenceBasis
}

/** `evaluated` and `unevaluated` are the two predicates the lay projection's branches turn on. */
export function isEvaluated(result: RequirementResult): boolean {
  return result.verdict !== "not_applicable"
}

/**
 * Refuse a JSON object that is not shaped like a `ConformanceReport`. The error names the first
 * thing it found wrong so a stale or misconfigured Python install is not reported as a runtime
 * crash inside the renderer.
 */
export function parseReport(value: unknown): ConformanceReport {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("the JSON record is not an object")
  }
  const obj = value as Record<string, unknown>
  if (obj["schema_version"] !== REPORT_SCHEMA_VERSION) {
    throw new Error(
      `unsupported schema_version ${JSON.stringify(obj["schema_version"])}; this build of ` +
        `reasonsmith-tui reads schema_version ${REPORT_SCHEMA_VERSION}. Regenerate the JSON by ` +
        "running `reasonsmith check --json` against the matching Python reasonsmith version.",
    )
  }
  for (const key of [
    "pack_id",
    "system_name",
    "system_scope",
    "system_domains",
    "time_domain",
    "headline",
    "counts",
    "results",
    "limits",
    "undeclared_domain_notice",
    "audience",
  ] as const) {
    if (!(key in obj)) {
      throw new Error(
        `the JSON record is missing ${JSON.stringify(key)}. The key is additive, so ` +
          `\`schema_version\` is still ${REPORT_SCHEMA_VERSION} without it; run \`reasonsmith ` +
          "check --json` against a Python reasonsmith that emits it.",
      )
    }
  }
  if (!Array.isArray(obj["results"])) {
    throw new Error("`results` must be an array")
  }
  const rawNotice = obj["undeclared_domain_notice"]
  if (rawNotice !== null && typeof rawNotice !== "string") {
    throw new Error(
      "`undeclared_domain_notice` must be a string or null; got " + JSON.stringify(rawNotice),
    )
  }
  // Narrowed by the throw above; TypeScript cannot carry that narrowing out of `unknown` itself.
  const notice = rawNotice as string | null
  return {
    schema_version: REPORT_SCHEMA_VERSION,
    pack_id: String(obj["pack_id"]),
    system_name: String(obj["system_name"]),
    system_scope: obj["system_scope"] === null ? null : String(obj["system_scope"]),
    system_domains: asStringArray(obj["system_domains"], "system_domains"),
    time_domain: String(obj["time_domain"]),
    headline: String(obj["headline"]),
    counts: parseCounts(obj["counts"]),
    results: (obj["results"] as readonly unknown[]).map((r, i) =>
      parseResult(r, `results[${i}]`),
    ),
    limits: String(obj["limits"]),
    undeclared_domain_notice: notice,
    audience: checkAudienceBlock(obj["audience"]),
  }
}

function parseCounts(value: unknown): ReportCounts {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("`counts` must be an object")
  }
  const c = value as Record<string, unknown>
  const keys: (keyof ReportCounts)[] = [
    "total",
    "binding_total",
    "proved",
    "probed",
    "recounted",
    "observed",
    "violated",
    "inconclusive",
    "not_evaluated",
    "on_an_assessment",
    "unattainable",
    "not_applicable",
    "interpretive_total",
    "interpretive_proved",
    "interpretive_probed",
    "interpretive_recounted",
    "interpretive_observed",
    "interpretive_violated",
    "interpretive_inconclusive",
    "interpretive_not_evaluated",
    "interpretive_on_an_assessment",
    "interpretive_unattainable",
    "interpretive_not_applicable",
  ]
  const out: Record<string, number> = {}
  for (const key of keys) {
    const v = c[key]
    if (typeof v !== "number" || !Number.isFinite(v)) {
      throw new Error(`counts.${key} must be a number; got ${JSON.stringify(v)}`)
    }
    out[key] = v
  }
  return out as unknown as ReportCounts
}

function parseResult(value: unknown, path: string): RequirementResult {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${path} must be an object`)
  }
  const obj = value as Record<string, unknown>
  for (const key of [
    "requirement_id",
    "source_clause",
    "verbatim_text",
    "verdict",
    "outcome",
    "strength",
    "signals_required",
    "signals_missing",
    "evidence_summary",
    "details",
    "findings",
    "binding",
    "scope",
    "domains",
    "basis",
  ] as const) {
    if (!(key in obj)) {
      throw new Error(`${path} is missing ${JSON.stringify(key)}`)
    }
  }
  const verdictRaw = obj["verdict"]
  const outcomeRaw = obj["outcome"]
  const strengthRaw = obj["strength"]
  const basisRaw = obj["basis"]
  if (typeof verdictRaw !== "string" || !isVerdict(verdictRaw)) {
    throw new Error(`${path}.verdict is not a recognised verdict: ${JSON.stringify(verdictRaw)}`)
  }
  if (typeof outcomeRaw !== "string" || !isOperationalOutcome(outcomeRaw)) {
    throw new Error(`${path}.outcome is not a recognised operational outcome: ${JSON.stringify(outcomeRaw)}`)
  }
  if (strengthRaw !== null && (typeof strengthRaw !== "string" || !isStrength(strengthRaw))) {
    throw new Error(
      `${path}.strength is not a recognised strength (or null): ${JSON.stringify(strengthRaw)}`,
    )
  }
  if (typeof basisRaw !== "string" || !isBasis(basisRaw)) {
    throw new Error(`${path}.basis is not a recognised basis: ${JSON.stringify(basisRaw)}`)
  }
  // Narrowed to the vocabularies by the checks above; the type cast is required because TypeScript
  // cannot narrow `unknown` to `Strength | null` through an `if (!isStrength()) throw` alone.
  const verdict = verdictRaw
  const outcome = outcomeRaw
  const strength = strengthRaw as StrengthOrNull
  const basis = basisRaw
  if (
    obj["details"] === null ||
    typeof obj["details"] !== "object" ||
    Array.isArray(obj["details"])
  ) {
    throw new Error(`${path}.details must be an object`)
  }
  return {
    requirement_id: String(obj["requirement_id"]),
    source_clause: String(obj["source_clause"]),
    verbatim_text: String(obj["verbatim_text"]),
    verdict,
    outcome,
    strength,
    signals_required: asStringArray(obj["signals_required"], `${path}.signals_required`),
    signals_missing: asStringArray(obj["signals_missing"], `${path}.signals_missing`),
    evidence_summary: String(obj["evidence_summary"]),
    details: obj["details"] as Record<string, unknown>,
    findings: parseFindings(obj["findings"], `${path}.findings`),
    binding: Boolean(obj["binding"]),
    scope: String(obj["scope"]),
    domains: asStringArray(obj["domains"], `${path}.domains`),
    basis,
  }
}

/**
 * Findings are a closed list, so an unrecognised `type` is refused rather than carried through as
 * free prose the detail pane would have to word for itself. The refusal is the point: a finding
 * kind this build has no wording for is a finding it cannot show, and showing nothing while
 * reporting success is the failure this whole package is written against.
 */
function parseFindings(value: unknown, path: string): readonly Finding[] {
  if (!Array.isArray(value)) {
    throw new Error(`${path} must be an array`)
  }
  return value.map((item, i) => {
    const at = `${path}[${i}]`
    if (item === null || typeof item !== "object" || Array.isArray(item)) {
      throw new Error(`${at} must be an object`)
    }
    const f = item as Record<string, unknown>
    if (f["type"] !== "certificate") {
      throw new Error(`${at}.type is not a finding kind this build renders: ${JSON.stringify(f["type"])}`)
    }
    if (f["verdict"] !== "FAIL") {
      throw new Error(
        `${at}.verdict must be "FAIL" — the Python reports a certificate finding only where the ` +
          `measurement failed; got ${JSON.stringify(f["verdict"])}`,
      )
    }
    const index = f["decision_index"]
    if (index !== null && index !== undefined && typeof index !== "number") {
      throw new Error(`${at}.decision_index must be a number or null; got ${JSON.stringify(index)}`)
    }
    return {
      type: "certificate",
      verdict: "FAIL",
      decision_index: typeof index === "number" ? index : null,
    } satisfies CertificateFinding
  })
}

function asStringArray(value: unknown, path: string): readonly string[] {
  if (!Array.isArray(value)) {
    throw new Error(`${path} must be an array of strings`)
  }
  return value.map((item) => {
    if (typeof item !== "string") {
      throw new Error(`${path} must contain only strings`)
    }
    return item
  })
}