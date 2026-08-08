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
 */

import { isBasis, isStrength, isVerdict, type EvidenceBasis, type StrengthOrNull, type Verdict } from "./verdict.ts"

/** `JSON_SCHEMA_VERSION` from `src/reasonsmith/report.py`. Bump on the Python side, then here. */
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
 * One requirement's result. The fields here are exactly the keys every result carries — no field is
 * optional, every field is what the Python reports. `details` is the bag every engine writes into;
 * the TUI reads only the keys it has a name for.
 */
export interface RequirementResult {
  readonly requirement_id: string
  readonly source_clause: string
  readonly verdict: Verdict
  readonly strength: StrengthOrNull
  readonly signals_required: readonly string[]
  readonly signals_missing: readonly string[]
  readonly evidence_summary: string
  readonly details: Readonly<Record<string, unknown>>
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
 * The full notice that runs of duties skipped for an undeclared domain. This mirrors
 * `ConformanceReport.undeclaredDomainNotice` from the Python and is printed in the findings header
 * exactly the way the Python prints it in stderr and `render_text` prints it on the text surface —
 * the TUI agrees because the wording is in `LIMITS_DOCUMENTATION_URL` below.
 */
export function undeclaredDomainNotice(report: ConformanceReport): string | null {
  const skipped = report.results.filter((r) => r.details["skipped_for_undeclared_domain"] === true)
  if (skipped.length === 0) return null
  const duties = skipped.length === 1 ? "duty was" : "duties were"
  return (
    `${skipped.length} domain-limited ${duties} reported not applicable without being checked, ` +
    "because this system declares no decision domain. Nothing in this report says those duties " +
    "are met. Declare what kind of decision this system makes — --system-domain <domain>, " +
    "repeatable, or a system_domains attribute on the adapter — and run it again."
  )
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
  ] as const) {
    if (!(key in obj)) {
      throw new Error(`the JSON record is missing ${JSON.stringify(key)}`)
    }
  }
  if (!Array.isArray(obj["results"])) {
    throw new Error("`results` must be an array")
  }
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
    "verdict",
    "strength",
    "signals_required",
    "signals_missing",
    "evidence_summary",
    "details",
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
  const strengthRaw = obj["strength"]
  const basisRaw = obj["basis"]
  if (typeof verdictRaw !== "string" || !isVerdict(verdictRaw)) {
    throw new Error(`${path}.verdict is not a recognised verdict: ${JSON.stringify(verdictRaw)}`)
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
  const verdict = verdictRaw as Verdict
  const strength = strengthRaw as StrengthOrNull
  const basis = basisRaw as EvidenceBasis
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
    verdict,
    strength,
    signals_required: asStringArray(obj["signals_required"], `${path}.signals_required`),
    signals_missing: asStringArray(obj["signals_missing"], `${path}.signals_missing`),
    evidence_summary: String(obj["evidence_summary"]),
    details: obj["details"] as Record<string, unknown>,
    binding: Boolean(obj["binding"]),
    scope: String(obj["scope"]),
    domains: asStringArray(obj["domains"], `${path}.domains`),
    basis,
  }
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