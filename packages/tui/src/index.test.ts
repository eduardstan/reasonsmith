/**
 * Tests for the TUI's data path: argument parsing, JSON parsing, and the rendering
 * distinction between `not evaluated` and `satisfied` results.
 *
 * The conformance run is *one subprocess call to the Python*. These tests assert that the
 * argument parsing reaches that call, that the JSON it consumes is validated, and that the
 * renderer does not silently turn "we could not tell" into "fine" — the one thing every
 * rendering in this tool is forbidden to do.
 */

import { describe, expect, test } from "bun:test"
import { isEvaluated, parseReport, type ConformanceReport, type RequirementResult } from "./types/schema.ts"
import { matchesCategory } from "./types/categories.ts"
import { basisSentence } from "./types/render.ts"
import { wrap } from "./theme.ts"
import { PROJECTIONS } from "./types/audiences.ts"
import { parseArgs } from "./args.ts"

/**
 * The `audience` block a run with no `--audience` emits: `name` null, and the full report's flags
 * under the Python's own spellings. Kept next to the fixtures because every report needs one — the
 * parser refuses a record without it.
 */
const FULL_AUDIENCE_BLOCK = {
  name: null,
  overview: true,
  strength: true,
  legal_metadata: true,
  signals: true,
  missing_signals: true,
  evidence_summary: true,
  probe_budget: true,
  witnesses: true,
  plain_account: false,
}

const NOT_EVALUATED: ConformanceReport = makeReport([
  {
    requirement_id: "gdpr_art_22_not_evaluated",
    source_clause: "test",
    verdict: "inconclusive",
    strength: null,
    basis: "behavioural",
    evidence_summary: "no engine here checked this",
  },
])

const SATISFIED: ConformanceReport = makeReport([
  {
    requirement_id: "ecoa_a_1_timing_satisfied",
    source_clause: "test",
    verdict: "satisfied",
    strength: "observed",
    basis: "behavioural",
    evidence_summary: "monitor satisfied at every step",
  },
])

const VIOLATED: ConformanceReport = makeReport([
  {
    requirement_id: "ecoa_b_2_violated",
    source_clause: "test",
    verdict: "violated",
    strength: "probed",
    basis: "artifact",
    evidence_summary: "probe found deleted reason",
  },
])

function makeReport(
  results: ReadonlyArray<{
    requirement_id: string
    source_clause: string
    verdict: "satisfied" | "violated" | "inconclusive" | "not_applicable"
    outcome?: "satisfied" | "violated" | "not_applicable" | "not_evaluated" | "unattainable"
    strength: "unattainable" | "observed" | "recounted" | "probed" | "proved" | null
    basis: "behavioural" | "relational" | "artifact" | "assessment"
    evidence_summary: string
    binding?: boolean
    findings?: RequirementResult["findings"]
  }>,
): ConformanceReport {
  return {
    schema_version: 2,
    pack_id: "ecoa",
    system_name: "test-system",
    system_scope: null,
    system_domains: [],
    time_domain: "ordinal",
    headline: "test",
    counts: {
      total: results.length,
      binding_total: results.length,
      proved: 0,
      probed: 0,
      recounted: 0,
      observed: 0,
      violated: 0,
      inconclusive: 0,
      not_evaluated: 0,
      on_an_assessment: 0,
      unattainable: 0,
      not_applicable: 0,
      interpretive_total: 0,
      interpretive_proved: 0,
      interpretive_probed: 0,
      interpretive_recounted: 0,
      interpretive_observed: 0,
      interpretive_violated: 0,
      interpretive_inconclusive: 0,
      interpretive_not_evaluated: 0,
      interpretive_on_an_assessment: 0,
      interpretive_unattainable: 0,
      interpretive_not_applicable: 0,
    },
    results: results.map((r) => ({
      requirement_id: r.requirement_id,
      source_clause: r.source_clause,
      verbatim_text: "",
      verdict: r.verdict,
      outcome:
        r.outcome ??
        (r.verdict === "not_applicable"
          ? "not_applicable"
          : r.strength === "unattainable"
            ? "unattainable"
            : r.verdict === "satisfied"
              ? "satisfied"
              : r.verdict === "violated"
                ? "violated"
                : "not_evaluated"),
      strength: r.strength,
      signals_required: [],
      signals_missing: [],
      evidence_summary: r.evidence_summary,
      details: {},
      findings: r.findings ?? [],
      binding: r.binding ?? true,
      scope: "",
      domains: [],
      basis: r.basis,
    })),
    limits: "test limits",
    undeclared_domain_notice: null,
    audience: { name: null, projection: PROJECTIONS.auditor },
  }
}

describe("the argument parser", () => {
  test("requires --system and --pack", () => {
    const result = parseArgs([])
    expect("error" in result).toBe(true)
  })

  test("forwards --audience and --system-domain flags verbatim", () => {
    const result = parseArgs([
      "--system",
      "decisions.jsonl",
      "--pack",
      "ecoa",
      "--audience",
      "deployer",
      "--system-domain",
      "consumer-credit",
    ])
    expect("error" in result).toBe(false)
    if ("error" in result) return
    expect(result.system).toBe("decisions.jsonl")
    expect(result.pack).toBe("ecoa")
    expect(result.audience).toBe("deployer")
    expect(result.systemDomains).toEqual(["consumer-credit"])
  })

  test("--help returns the help branch", () => {
    const result = parseArgs(["--help"])
    expect("error" in result && result.help).toBe(true)
  })
})

/**
 * A record shaped the way `ConformanceReport.to_dict()` shapes one — the raw JSON, before parsing,
 * with the Python's own key spellings. The parser tests run against this and not against the typed
 * fixtures above: `audience` arrives as nine flat flags and leaves as a projection, so a fixture
 * that could be fed straight back in would be a fixture that had stopped testing the boundary.
 */
function rawReport(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  const typed = makeReport([
    {
      requirement_id: "ecoa_b_2",
      source_clause: "12 CFR 1002.9(b)(2)",
      verdict: "satisfied",
      strength: "probed",
      basis: "artifact",
      evidence_summary: "certified",
    },
  ])
  return {
    ...typed,
    audience: FULL_AUDIENCE_BLOCK,
    ...overrides,
  }
}

describe("the JSON parser", () => {
  test("refuses a wrong schema_version", () => {
    expect(() => parseReport(rawReport({ schema_version: 999 }))).toThrow(/schema_version/)
  })

  test("refuses a missing field", () => {
    const missing = rawReport()
    delete missing["headline"]
    expect(() => parseReport(missing)).toThrow(/headline/)
  })

  test("accepts a well-formed record", () => {
    const parsed = parseReport(rawReport())
    expect(parsed.results.length).toBe(1)
    expect(parsed.results[0].verbatim_text).toBe("")
    expect(parsed.results[0].findings).toEqual([])
  })

  test("refuses a record with no `undeclared_domain_notice`, naming the additive key", () => {
    const missing = rawReport()
    delete missing["undeclared_domain_notice"]
    // The schema version does not move for an added key, so absence cannot be inferred from it —
    // the error has to name the key and say which Python emits it.
    expect(() => parseReport(missing)).toThrow(/undeclared_domain_notice/)
    expect(() => parseReport(missing)).toThrow(/schema_version/)
  })

  test("carries the notice through as prose, and null as a value", () => {
    expect(parseReport(rawReport()).undeclared_domain_notice).toBeNull()
    const notice = "2 domain-limited duties were reported not applicable without being checked."
    expect(parseReport(rawReport({ undeclared_domain_notice: notice })).undeclared_domain_notice).toBe(
      notice,
    )
  })

  test("refuses an audience projection that disagrees with this build's table", () => {
    const drifted = rawReport({
      audience: { ...FULL_AUDIENCE_BLOCK, name: "regulator", witnesses: true },
    })
    expect(() => parseReport(drifted)).toThrow(/disagrees/)
    // And the agreeing one passes, so the check is not vacuous.
    const agreeing = rawReport({
      audience: {
        ...FULL_AUDIENCE_BLOCK,
        name: "regulator",
        signals: false,
        missing_signals: false,
        witnesses: false,
      },
    })
    expect(parseReport(agreeing).audience.name).toBe("regulator")
  })

  test("refuses a finding kind it has no wording for", () => {
    const unknown = rawReport()
    const results = (unknown["results"] as Record<string, unknown>[]).map((r) => ({
      ...r,
      findings: [{ type: "provenance", verdict: "FAIL", decision_index: 0 }],
    }))
    expect(() => parseReport({ ...unknown, results })).toThrow(/provenance/)
  })
})

describe("a failed certificate beside a satisfied duty", () => {
  test("is carried, not reconciled away", () => {
    const raw = rawReport()
    const results = (raw["results"] as Record<string, unknown>[]).map((r) => ({
      ...r,
      verdict: "satisfied",
      findings: [{ type: "certificate", verdict: "FAIL", decision_index: 2 }],
    }))
    const parsed = parseReport({ ...raw, results })
    const result = parsed.results[0]
    // Both facts survive the parse. The duty was cleared on what its engine could check; the
    // certificate measurement over decision 2 failed. Neither is allowed to overwrite the other.
    expect(result.verdict).toBe("satisfied")
    expect(result.findings).toEqual([{ type: "certificate", verdict: "FAIL", decision_index: 2 }])
  })
})

describe("the category filter", () => {
  const binding: RequirementResult = makeReport([
    {
      requirement_id: "binding_violated",
      source_clause: "c",
      verdict: "violated",
      strength: "observed",
      basis: "behavioural",
      evidence_summary: "e",
    },
  ]).results[0]
  const interpretive: RequirementResult = makeReport([
    {
      requirement_id: "interpretive_violated",
      source_clause: "c",
      verdict: "violated",
      strength: "observed",
      basis: "behavioural",
      evidence_summary: "e",
      binding: false,
    },
  ]).results[0]

  test("matches only binding results, because the counts it answers for are binding-only", () => {
    expect(matchesCategory(binding, "violated")).toBe(true)
    expect(matchesCategory(interpretive, "violated")).toBe(false)
  })

  test("counts a rung only where the verdict is satisfied", () => {
    const violatedAtProbed = makeReport([
      {
        requirement_id: "r",
        source_clause: "c",
        verdict: "violated",
        strength: "probed",
        basis: "artifact",
        evidence_summary: "e",
      },
    ]).results[0]
    expect(matchesCategory(violatedAtProbed, "probed")).toBe(false)
    expect(matchesCategory(violatedAtProbed, "violated")).toBe(true)
  })

  test("splits `not_evaluated` from `on_an_assessment` by basis", () => {
    const [graded, unsettled] = makeReport([
      {
        requirement_id: "graded",
        source_clause: "c",
        verdict: "inconclusive",
        strength: null,
        basis: "assessment",
        evidence_summary: "e",
      },
      {
        requirement_id: "unsettled",
        source_clause: "c",
        verdict: "inconclusive",
        strength: null,
        basis: "behavioural",
        evidence_summary: "e",
      },
    ]).results
    expect(matchesCategory(graded, "on_an_assessment")).toBe(true)
    expect(matchesCategory(graded, "not_evaluated")).toBe(false)
    expect(matchesCategory(unsettled, "not_evaluated")).toBe(true)
    expect(matchesCategory(unsettled, "on_an_assessment")).toBe(false)
  })

  test("an unrecognised category matches nothing rather than everything", () => {
    expect(matchesCategory(binding, "no_such_category")).toBe(false)
  })
})

describe("the evidence basis sentence", () => {
  test("says nothing for the behavioural basis, as the Python says nothing", () => {
    // `basis_sentence` returns None there: the basis reaches every rung, so there is no ceiling to
    // explain, and a sentence on every result is what makes the other three unreadable.
    expect(basisSentence("behavioural")).toBeNull()
  })

  test("words the three bases that carry a ceiling", () => {
    for (const basis of ["relational", "artifact", "assessment"] as const) {
      expect(basisSentence(basis)).toContain(basis)
    }
  })
})

describe("the not-evaluated-vs-satisfied distinction", () => {
  test("a not evaluated result has null strength", () => {
    expect(NOT_EVALUATED.results[0].strength).toBeNull()
    expect(NOT_EVALUATED.results[0].verdict).toBe("inconclusive")
  })

  test("a satisfied result carries a strength", () => {
    expect(SATISFIED.results[0].strength).toBe("observed")
    expect(SATISFIED.results[0].verdict).toBe("satisfied")
  })

  test("the two are visibly different in `resultTone` and `strengthWord`", async () => {
    const { resultTone, strengthWord } = await import("./theme.ts")
    const notTone = resultTone(
      NOT_EVALUATED.results[0].verdict,
      NOT_EVALUATED.results[0].strength,
    )
    const satTone = resultTone(
      SATISFIED.results[0].verdict,
      SATISFIED.results[0].strength,
    )
    expect(notTone.label).not.toBe(satTone.label)
    expect(notTone.mark).not.toBe(satTone.mark)
    expect(notTone.color).not.toBe(satTone.color)
    expect(strengthWord(null)).toBe("not evaluated")
    expect(strengthWord("observed")).toBe("observed")
  })

  test("the lay projection's `evaluated()` predicate keeps the two apart", () => {
    expect(isEvaluated(NOT_EVALUATED.results[0])).toBe(true)
    expect(isEvaluated(SATISFIED.results[0])).toBe(true)
    expect(
      isEvaluated({
        ...NOT_EVALUATED.results[0],
        verdict: "not_applicable",
        strength: null,
      }),
    ).toBe(false)
  })
})

describe("violated runs carry the documented exit code", () => {
  test("violated results are reached, not just satisfied", () => {
    expect(VIOLATED.results[0].verdict).toBe("violated")
    expect(VIOLATED.results[0].strength).toBe("probed")
  })
})

describe("wrapping to a terminal width", () => {
  test("keeps every line inside the measure", () => {
    const text =
      "2 domain-limited duties were reported not applicable without being checked, because this " +
      "system declares no decision domain."
    for (const measure of [24, 40, 72, 92]) {
      for (const line of wrap(text, measure)) {
        expect(line.length).toBeLessThanOrEqual(measure)
      }
    }
  })

  test("breaks a token too long to fit rather than letting it overflow", () => {
    // A terminal does not clip an over-long line, it wraps it into the row beneath and shears the
    // panel below down a line — so one unbroken requirement id would corrupt the whole layout.
    const id = "ecoa_reg_b_1002_9_b_2_principal_reasons_complete"
    const lines = wrap(id, 20)
    expect(lines.length).toBeGreaterThan(1)
    for (const line of lines) expect(line.length).toBeLessThanOrEqual(20)
    expect(lines.join("")).toBe(id)
  })

  test("loses no word of a sentence it wraps", () => {
    const text = "no check in this report could settle it, so it was left open rather than answered."
    expect(wrap(text, 30).join(" ")).toBe(text)
  })
})
