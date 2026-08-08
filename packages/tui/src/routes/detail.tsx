/**
 * The detail route: one result, as much of it as this audience is shown.
 *
 * Every block is gated by a flag from `PROJECTIONS[audience]` in `types/audiences.ts`, and **the
 * gating here mirrors `render.renderResult`'s, flag for flag**. That is the point of the module:
 * the projection changes what is shown and never what is claimed, so a reader who runs
 * `reasonsmith check --audience deployer` and a reader who presses `a` until the footer says
 * *deployer* must be shown the same things.
 *
 * What a reader must not break:
 *
 *   - **The verdict and the clause are on every row of the table.** No projection drops either, so
 *     neither is behind a flag. A verdict without the duty it is about is not a smaller report, it
 *     is an unreadable one.
 *   - **The evidence basis is behind `strength`.** The lay reader is shown *no basis at all*, on the
 *     same flag that withholds the rung, because a basis is a kind and not a rank and being told one
 *     hands a reader this tool's evidence model rather than an answer.
 *   - **`missingCapabilities` and `signalNames` are different findings and different flags.** A
 *     missing capability says the system cannot emit a signal at all; a signal absent from the trace
 *     says this log did not. The deployer sees the first and not the second, which is the whole
 *     reason they are separate rows.
 *   - **`basisSentence` is the only place any rendering words a basis**, so a ceiling reads as the
 *     *duty's* rather than as an exposure the system withheld.
 *   - **The certificate block is where the finding lives.** `missing_reasons` names the reasons the
 *     decision's own inference used and its notice did not state — measured against the inference
 *     artefact, never read from the log. It is the sharpest thing this tool produces, so it is
 *     printed in the verdict's own colour rather than dimmed into the rest of the details. The
 *     decision *index* inside it is a pointer at a real record and is behind `witnesses`.
 */

import { For, Show } from "solid-js"
import { SyntaxStyle } from "@opentui/core"
import {
  CERTIFICATES_KEY,
  COUNTEREXAMPLE_KEY,
  OFFENDING_TRACE_SEGMENT_KEY,
  PROBE_BUDGET_KEY,
  SIGNALS_ABSENT_FROM_TRACE_KEY,
  TRUTH_DEGREE_KEY,
  VACUOUS_TRIGGER_KEY,
  VIOLATION_STEP_INDICES_KEY,
} from "../types/detail-keys.ts"
import type { RequirementResult } from "../types/schema.ts"
import { basisSentence } from "../types/render.ts"
import { useReport } from "../context/report.tsx"
import { useRoute } from "../context/route.tsx"
import { useTheme } from "../context/theme.tsx"
import { Clickable } from "../ui/clickable.tsx"
import { VerdictChip } from "../ui/verdict-chip.tsx"
import { type Color, wrap } from "../theme.ts"

/**
 * One `SyntaxStyle` for every `<markdown>` on this screen. The renderer needs a syntax style to
 * colour headings and emphasis; an empty one bolds headings and dims everything else by convention,
 * which is exactly what this screen wants. A single instance for the lifetime of the process — the
 * renderable does not own the style, and the OS reclaims it on exit.
 */
const SYNTAX_STYLE = SyntaxStyle.create()

const WIDTH = 94

export function Detail() {
  const t = useTheme()
  const report = useReport()
  const route = useRoute()

  return (
    <box
      flexDirection="column"
      flexGrow={1}
      minHeight={0}
      width="100%"
      borderStyle="rounded"
      borderColor={t.color.border}
    >
      <Clickable cursor="pointer" paddingLeft={1} paddingRight={1} onClick={() => route.back()}>
        <text fg={t.color.info} attributes={t.attr.underline} wrapMode="none" content="← back to findings" />
      </Clickable>
      <scrollbox
        flexGrow={1}
        minHeight={0}
        width="100%"
        paddingLeft={1}
        paddingRight={1}
        backgroundColor={t.color.bg}
        verticalScrollbarOptions={{
          showArrows: true,
          trackOptions: {
            foregroundColor: t.color.info,
            backgroundColor: t.color.surface,
          },
        }}
        scrollbarOptions={{
          showArrows: true,
          trackOptions: {
            foregroundColor: t.color.info,
            backgroundColor: t.color.surface,
          },
        }}
      >
        <Show
          when={report.current()}
          fallback={<text fg={t.color.textMuted} content="No requirement selected." />}
        >
          {(result) => <Body result={result()} />}
        </Show>
      </scrollbox>
    </box>
  )
}

function Body(props: { result: RequirementResult }) {
  const t = useTheme()
  const report = useReport()
  const view = () => report.view()
  const tone = () => t.resultTone(props.result.verdict, props.result.strength)

  const classification = () =>
    [
      props.result.binding ? "binding" : "interpretive",
      props.result.scope ? `scope ${props.result.scope}` : null,
      props.result.domains.length > 0 ? `domains ${props.result.domains.join(", ")}` : null,
    ]
      .filter((part): part is string => part !== null)
      .join(" · ")

  const absentFromTrace = () => {
    const absent = props.result.details[SIGNALS_ABSENT_FROM_TRACE_KEY]
    return Array.isArray(absent) ? absent.map(String) : []
  }

  return (
    <box flexDirection="column" width="100%">
      <box
        flexDirection="row"
        gap={1}
        height={1}
        borderStyle="rounded"
        borderColor={t.color.border}
        title={props.result.requirement_id}
        titleAlignment="left"
      >
        <VerdictChip
          verdict={props.result.verdict}
          strength={props.result.strength}
          showStrength={view().strength}
          bold
        />
        <text fg={tone().color} attributes={t.attr.bold} wrapMode="none" content={tone().label} />
      </box>

      {/* On every row of the projection table: no audience is shown a verdict without its clause. */}
      <Field label="clause" value={props.result.source_clause} />

      <Show when={view().classification}>
        <Field label="classification" value={classification()} />
      </Show>

      {/*
        Gated on `strength`, not on a flag of its own: the lay projection is shown no basis at all,
        on the same flag that already withholds the rung.
      */}
      <Show when={view().strength}>
        <Field label="evidence basis" value={basisSentence(props.result.basis)} />
      </Show>

      <Show when={view().signalNames && props.result.signals_required.length > 0}>
        <Field label="requires" value={props.result.signals_required.join(", ")} />
      </Show>

      <Show when={view().signalNames && absentFromTrace().length > 0}>
        <Field label="absent from the trace" value={absentFromTrace().join(", ")} />
      </Show>

      {/*
        A different finding from the one above, and a different flag: this says the system cannot
        emit the signal at all, not that this log did not carry it.
      */}
      <Show when={view().missingCapabilities && props.result.signals_missing.length > 0}>
        <Field
          label="missing capability signals"
          value={props.result.signals_missing.join(", ")}
          color={t.color.unattainable}
        />
      </Show>

      <Show when={view().witnesses}>
        <Witnesses result={props.result} />
      </Show>

      <Show when={view().evidence && props.result.evidence_summary}>
        <MarkdownField label="evidence" text={props.result.evidence_summary} />
      </Show>

      <Show when={view().probeBudget}>
        <ProbeBudget result={props.result} />
      </Show>

      <Show when={view().evidence}>
        <VacuousTrigger result={props.result} />
        <TruthDegree result={props.result} />
        <Certificates result={props.result} showDecisionIndex={view().witnesses} />
      </Show>

      <Show when={view().plainAccount}>
        <LayAccount />
      </Show>
    </box>
  )
}

function Field(props: { label: string; value: string; color?: Color }) {
  const t = useTheme()
  return (
    <box flexDirection="column" marginTop={1}>
      <text fg={t.color.textMuted} attributes={t.attr.dim} wrapMode="none" content={props.label} />
      <For each={wrap(props.value, WIDTH)}>
        {(line) => <text fg={props.color ?? t.color.text} wrapMode="none" content={line} />}
      </For>
    </box>
  )
}

function Paragraph(props: { label: string; text: string }) {
  const t = useTheme()
  return (
    <box flexDirection="column" marginTop={1}>
      <text fg={t.color.textMuted} attributes={t.attr.dim} wrapMode="none" content={props.label} />
      <For each={wrap(props.text, WIDTH)}>
        {(line) => <text fg={t.color.textSecondary} wrapMode="none" content={line} />}
      </For>
    </box>
  )
}

/**
 * A labelled block whose body is rendered through OpenTUI's `<markdown>`. Used for the
 * `evidence_summary` because the field is free-form prose and bold/italic in the source should
 * survive into the panel — the way they survive into the text rendering this command also reaches.
 */
function MarkdownField(props: { label: string; text: string }) {
  const t = useTheme()
  return (
    <box flexDirection="column" marginTop={1}>
      <text fg={t.color.textMuted} attributes={t.attr.dim} wrapMode="none" content={props.label} />
      <markdown
        content={props.text}
        syntaxStyle={SYNTAX_STYLE}
        fg={t.color.textSecondary}
        bg={t.color.bg}
      />
    </box>
  )
}

function Witnesses(props: { result: RequirementResult }) {
  const t = useTheme()
  const segment = () => {
    const raw = props.result.details[OFFENDING_TRACE_SEGMENT_KEY]
    return Array.isArray(raw) ? (raw as Record<string, unknown>[]) : []
  }
  const offending = () => {
    const first = segment()[0]
    if (first === undefined) return null
    const id = first.decision_id ?? first.artifact_logs_decision_record
    if (typeof id === "string" && id.trim()) return id.trim()
    const indices = props.result.details[VIOLATION_STEP_INDICES_KEY]
    if (Array.isArray(indices) && indices.length > 0) return `decision #${String(indices[0])}`
    return "decision #0"
  }
  const counterexample = () => {
    const raw = props.result.details[COUNTEREXAMPLE_KEY]
    return raw && typeof raw === "object" ? JSON.stringify(raw) : null
  }

  return (
    <>
      <Show when={props.result.verdict === "violated" && offending()}>
        {(name) => <Field label="first offending decision" value={name()} color={t.color.bad} />}
      </Show>
      <Show when={counterexample()}>
        {(text) => <Field label="counterexample" value={text()} color={t.color.bad} />}
      </Show>
    </>
  )
}

function ProbeBudget(props: { result: RequirementResult }) {
  const t = useTheme()
  const budget = () => props.result.details[PROBE_BUDGET_KEY] as Record<string, unknown> | undefined

  return (
    <Show when={budget()}>
      {(b) => (
        <box flexDirection="column" marginTop={1}>
          <text
            fg={t.color.textMuted}
            attributes={t.attr.dim}
            wrapMode="none"
            content="probe budget — the bound on what this verdict claims"
          />
          <text
            fg={t.color.text}
            wrapMode="none"
            content={`${String(b().trials)} trial(s)  ·  seed ${String(b().seed)}`}
          />
          <Show when={b().input_space && typeof b().input_space === "object"}>
            <For each={Object.entries(b().input_space as Record<string, unknown>)}>
              {([key, value]) => (
                <text
                  fg={t.color.textMuted}
                  wrapMode="none"
                  content={`  ${key}: ${String(value)}`}
                />
              )}
            </For>
          </Show>
        </box>
      )}
    </Show>
  )
}

function VacuousTrigger(props: { result: RequirementResult }) {
  const t = useTheme()
  const trigger = () =>
    props.result.details[VACUOUS_TRIGGER_KEY] as Record<string, unknown> | undefined

  return (
    <Show when={trigger()}>
      {(v) => (
        <box flexDirection="column" marginTop={1}>
          <text
            fg={t.color.unattainable}
            attributes={t.attr.bold}
            wrapMode="none"
            content="the trigger fired nowhere"
          />
          <For
            each={wrap(
              `Nothing in ${String(v().domain)} made the antecedent ${String(v().antecedent)} ` +
                "true, so this evidence would report every system alike satisfied and says nothing " +
                "about this one.",
              WIDTH,
            )}
          >
            {(line) => <text fg={t.color.textSecondary} wrapMode="none" content={line} />}
          </For>
        </box>
      )}
    </Show>
  )
}

/**
 * A truth degree, formatted here the way `render.degree_sentence` formats it there: beside its
 * algebra, and on a result that carries **no** strength — so `0.7` can never read as a fraction of
 * a rung.
 */
function TruthDegree(props: { result: RequirementResult }) {
  const t = useTheme()
  const degree = () => props.result.details[TRUTH_DEGREE_KEY] as Record<string, unknown> | undefined

  return (
    <Show when={degree()}>
      {(d) => (
        <Field
          label="truth degree — a measurement, not a verdict"
          value={`${String(d().degree)} over the ${String(d().algebra)} algebra`}
        />
      )}
    </Show>
  )
}

function Certificates(props: { result: RequirementResult; showDecisionIndex: boolean }) {
  const t = useTheme()
  const certs = () => {
    const raw = props.result.details[CERTIFICATES_KEY]
    return Array.isArray(raw) ? (raw as Record<string, unknown>[]) : []
  }

  return (
    <Show when={certs().length > 0}>
      <box flexDirection="column" marginTop={1}>
        <text
          fg={t.color.textMuted}
          attributes={t.attr.dim}
          wrapMode="none"
          content="reason-deletion certificates — measured against the inference artefact, not read from the log"
        />
        <For each={certs()}>
          {(cert) => {
            const missing = Array.isArray(cert.missing_reasons)
              ? (cert.missing_reasons as unknown[])
              : []
            const head = props.showDecisionIndex
              ? `decision #${String(cert.decision_index)}`
              : "a certified decision"
            return (
              <box flexDirection="column" marginTop={1}>
                <text
                  fg={t.color.text}
                  wrapMode="none"
                  content={
                    `${head}  ·  ${String(cert.reasons_found)} reason(s) found  ·  ` +
                    `${String(cert.reasons_deleted)} the answer did not depend on`
                  }
                />
                <Show when={missing.length > 0}>
                  <text
                    fg={t.color.bad}
                    attributes={t.attr.bold}
                    wrapMode="none"
                    content="  reasons the stated notice left out:"
                  />
                  <For each={missing}>
                    {(reason) => (
                      <text fg={t.color.bad} wrapMode="none" content={`    · ${String(reason)}`} />
                    )}
                  </For>
                </Show>
                <Show when={typeof cert.attribution === "string"}>
                  <For each={wrap(String(cert.attribution), WIDTH - 2)}>
                    {(line) => (
                      <text
                        fg={t.color.textMuted}
                        attributes={t.attr.dim}
                        wrapMode="none"
                        content={`  ${line}`}
                      />
                    )}
                  </For>
                </Show>
              </box>
            )
          }}
        </For>
      </box>
    </Show>
  )
}

/**
 * The lay projection's own content — the one thing a projection *emits* rather than suppresses.
 *
 * Everything printed is quoted: the decision and the reason out of the trace this run already read,
 * and a reason left unstated out of the certificate engine's own measurement. Nothing here
 * paraphrases a statute, explains a decision, or advises.
 *
 * The second heading is printed whether or not anything was found, because **absence of a finding is
 * never completeness**: silence under it reads to this reader as a clean result, and it is not one.
 */
function LayAccount() {
  const t = useTheme()
  const report = useReport()

  /**
   * Every duty answered on the `artifact` basis — whatever its verdict — because a reader shown only
   * the breaches would read the silence on the others as a clean result. `anyMeasured` and `missing`
   * are the two facts the three branches below turn on, and they are exactly `render.laySections`'s.
   */
  const certified = () => {
    const missing: string[] = []
    let anyMeasured = false
    for (const result of report.results().filter((r) => r.basis === "artifact")) {
      const raw = result.details[CERTIFICATES_KEY]
      if (!Array.isArray(raw)) continue
      anyMeasured = true
      for (const cert of raw as Record<string, unknown>[]) {
        const reasons = cert.missing_reasons
        if (Array.isArray(reasons)) missing.push(...reasons.map(String))
      }
    }
    return { anyMeasured, missing: [...new Set(missing)] }
  }

  return (
    <box flexDirection="column" marginTop={1}>
      {/*
        The Python JSON does not carry the per-decision account — `ConformanceReport.decisions` is
        deliberately absent from `to_dict()` to keep the JSON a *findings* record, not a
        re-publication of the source log. The TUI therefore prints the same wording the affected-
        individual text rendering prints when it has no log to quote, and the lay view is honest
        about that. The reasons section below *is* reachable from the JSON, because the certificate
        engine's measurement of which reasons were struck travels in `details["certificates"]`.
      */}
      <text
        fg={t.color.text}
        attributes={t.attr.bold}
        wrapMode="none"
        content="WHAT THE SYSTEM RECORDED ABOUT THE DECISIONS"
      />
      <For
        each={wrap(
          "This tool's JSON record does not carry the source log; it carries the findings of " +
            "the run that read it. The same wording appears in `reasonsmith check --audience " +
            "affected-individual`, where the source log is in hand and is quoted in full.",
          WIDTH,
        )}
      >
        {(line) => <text fg={t.color.textMuted} wrapMode="none" content={line} />}
      </For>

      {/*
        Printed whatever the answer — including when nothing measured it. Silence under this heading
        reads to this reader as a clean result and it is not one. The three branches and their
        wording are `render.laySections`'s, so the TUI and `reasonsmith check --audience
        affected-individual` tell the same person the same thing.
      */}
      <box flexDirection="column" marginTop={1}>
        <text
          fg={t.color.text}
          attributes={t.attr.bold}
          wrapMode="none"
          content="WHETHER THE STATED REASONS WERE ALL THE REASONS"
        />
        <Show
          when={certified().anyMeasured}
          fallback={
            <For
              each={wrap(
                "Nothing in this run measured that. No inference artefact was opened up, so this " +
                  "report does not say the reasons you were given were complete, and does not say " +
                  "they were not.",
                WIDTH,
              )}
            >
              {(line) => <text fg={t.color.textMuted} wrapMode="none" content={line} />}
            </For>
          }
        >
          <Show
            when={certified().missing.length > 0}
            fallback={
              <For
                each={wrap(
                  "Every reason the decision's own inference used is one the statement names, as " +
                    "far as this run could measure. It measured only the decisions the system " +
                    "opened up.",
                  WIDTH,
                )}
              >
                {(line) => <text fg={t.color.textMuted} wrapMode="none" content={line} />}
              </For>
            }
          >
            <text
              fg={t.color.text}
              wrapMode="none"
              content="These reasons the decision's own inference used were not stated to you:"
            />
            <For each={certified().missing}>
              {(reason) => <text fg={t.color.bad} wrapMode="none" content={`  · ${reason}`} />}
            </For>
          </Show>
        </Show>
      </box>
    </box>
  )
}
