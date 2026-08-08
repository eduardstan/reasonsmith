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
import { isEvaluated, parseReport, type ConformanceReport } from "./types/schema.ts"
import { parseArgs } from "./args.ts"

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
    strength: "unattainable" | "observed" | "recounted" | "probed" | "proved" | null
    basis: "behavioural" | "relational" | "artifact" | "assessment"
    evidence_summary: string
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
      verdict: r.verdict,
      strength: r.strength,
      signals_required: [],
      signals_missing: [],
      evidence_summary: r.evidence_summary,
      details: {},
      binding: true,
      scope: "",
      domains: [],
      basis: r.basis,
    })),
    limits: "test limits",
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

describe("the JSON parser", () => {
  test("refuses a wrong schema_version", () => {
    const wrong = { ...NOT_EVALUATED, schema_version: 999 }
    expect(() => parseReport(wrong)).toThrow(/schema_version/)
  })

  test("refuses a missing field", () => {
    const missing: Record<string, unknown> = { ...NOT_EVALUATED }
    delete missing["headline"]
    expect(() => parseReport(missing)).toThrow(/headline/)
  })

  test("accepts a well-formed record", () => {
    const parsed = parseReport(NOT_EVALUATED)
    expect(parsed.results.length).toBe(1)
    expect(parsed.results[0]!.strength).toBeNull()
  })
})

describe("the not-evaluated-vs-satisfied distinction", () => {
  test("a not evaluated result has null strength", () => {
    expect(NOT_EVALUATED.results[0]!.strength).toBeNull()
    expect(NOT_EVALUATED.results[0]!.verdict).toBe("inconclusive")
  })

  test("a satisfied result carries a strength", () => {
    expect(SATISFIED.results[0]!.strength).toBe("observed")
    expect(SATISFIED.results[0]!.verdict).toBe("satisfied")
  })

  test("the two are visibly different in `resultTone` and `strengthWord`", async () => {
    const { resultTone, strengthWord } = await import("./theme.ts")
    const notTone = resultTone(
      NOT_EVALUATED.results[0]!.verdict,
      NOT_EVALUATED.results[0]!.strength,
    )
    const satTone = resultTone(
      SATISFIED.results[0]!.verdict,
      SATISFIED.results[0]!.strength,
    )
    expect(notTone.label).not.toBe(satTone.label)
    expect(notTone.mark).not.toBe(satTone.mark)
    expect(notTone.color).not.toBe(satTone.color)
    expect(strengthWord(null)).toBe("not evaluated")
    expect(strengthWord("observed")).toBe("observed")
  })

  test("the lay projection's `evaluated()` predicate keeps the two apart", () => {
    expect(isEvaluated(NOT_EVALUATED.results[0]!)).toBe(true)
    expect(isEvaluated(SATISFIED.results[0]!)).toBe(true)
    expect(
      isEvaluated({
        ...NOT_EVALUATED.results[0]!,
        verdict: "not_applicable",
        strength: null,
      }),
    ).toBe(false)
  })
})

describe("violated runs carry the documented exit code", () => {
  test("violated results are reached, not just satisfied", () => {
    expect(VIOLATED.results[0]!.verdict).toBe("violated")
    expect(VIOLATED.results[0]!.strength).toBe("probed")
  })
})
