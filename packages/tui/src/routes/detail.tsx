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
 *   - **A failed certificate is shown beside the verdict it disagrees with, not instead of it.**
 *     `result.findings` may report a `certificate` `FAIL` on a duty whose verdict is `satisfied`,
 *     and that pairing *is* the finding: the duty was cleared on what its engine could check, and
 *     the certificate measurement over the same decision failed. Reconciling the two here — showing
 *     the verdict and dropping the finding, or letting the finding colour the verdict — would be
 *     this renderer deciding which half of a measured disagreement its reader may see.
 */

import { For, Show } from "solid-js"
import { SyntaxStyle } from "@opentui/core"
import {
  CERTIFICATE_KEY,
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
import { isClaimedSemantics } from "../types/verdict.ts"
import { basisSentence } from "../types/render.ts"
import { useLayout } from "../context/layout.tsx"
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

export function Detail() {
  const t = useTheme()
  const report = useReport()
  const route = useRoute()
  const layout = useLayout()

  return (
    <box
      flexDirection="column"
      flexGrow={1}
      minHeight={0}
      width="100%"
      borderStyle="rounded"
      borderColor={t.color.border}
    >
      {/*
        `height` and `flexShrink` are both load-bearing. Without them this row claimed no height and
        the scroll region below drew over it, interleaving the two lines character by character —
        `←cbacketobfindingsb_2_principal_reasons_complete`.
      */}
      <Clickable
        cursor="pointer"
        height={1}
        flexShrink={0}
        paddingLeft={layout.pad()}
        paddingRight={layout.pad()}
        onClick={() => route.back()}
      >
        <text fg={t.color.info} attributes={t.attr.underline} wrapMode="none" content="← back to findings" />
      </Clickable>
      <scrollbox
        flexGrow={1}
        minHeight={0}
        width="100%"
        paddingLeft={layout.pad()}
        paddingRight={layout.pad()}
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
      {/*
        The requirement id as a heading, the verdict on the row beneath it, and no frame around
        either. This was a bordered box one row tall — the same defect the status bar and the footer
        carried — so its top border was drawn over the `← back to findings` link above it and the two
        came out interleaved: `←─back_togfindings9_b_2_principal_reasons_complete`. A border needs
        three rows to hold one row of content, and a frame here would be three rows spent saying
        what bold already says.
      */}
      <box flexDirection="column" width="100%">
        <text
          fg={t.color.text}
          attributes={t.attr.bold}
          wrapMode="none"
          content={props.result.requirement_id}
        />
        <box flexDirection="row" gap={1} height={1}>
          <VerdictChip
            verdict={props.result.verdict}
            strength={props.result.strength}
            showStrength={view().strength}
            bold
          />
          <text fg={tone().color} attributes={t.attr.bold} wrapMode="none" content={tone().label} />
        </box>
      </box>

      {/*
        Beside the verdict and before anything else, because a certificate that failed under a
        satisfied duty is the one thing on this screen a reader would otherwise not go looking for.
      */}
      <Show when={view().evidence}>
        <Findings result={props.result} showDecisionIndex={view().witnesses} />
      </Show>

      {/* On every row of the projection table: no audience is shown a verdict without its clause. */}
      <Field label="clause" value={props.result.source_clause} />

      <Show when={view().classification}>
        <Field label="classification" value={classification()} />
      </Show>

      {/*
        The clause's own words, quoted from the pack and never reflowed. Behind the same flag as the
        rest of the legal metadata (`legal_metadata` on the Python side): the lay projection is not
        shown statutory text, which is the other half of the rule that it paraphrases none.
      */}
      <Show when={view().classification && props.result.verbatim_text.trim() !== ""}>
        <Verbatim label="the clause, as the regulation writes it" text={props.result.verbatim_text} />
      </Show>

      {/*
        Gated on `strength`, not on a flag of its own: the lay projection is shown no basis at all,
        on the same flag that already withholds the rung. `basisSentence` is null for the
        behavioural basis, where the Python renders nothing — an absent ceiling, not a missing row.
      */}
      <Show when={view().strength && basisSentence(props.result.basis)}>
        {(sentence) => <Field label="evidence basis" value={sentence()} />}
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
        <SemanticsGap result={props.result} />
      </Show>

      <Show when={view().plainAccount}>
        <LayAccount />
      </Show>
    </box>
  )
}

function Field(props: { label: string; value: string; color?: Color }) {
  const t = useTheme()
  const layout = useLayout()
  return (
    <box flexDirection="column" marginTop={1}>
      <text fg={t.color.textMuted} attributes={t.attr.dim} wrapMode="none" content={props.label} />
      <For each={wrap(props.value, layout.measure())}>
        {(line) => <text fg={props.color ?? t.color.text} wrapMode="none" content={line} />}
      </For>
    </box>
  )
}

function Paragraph(props: { label: string; text: string }) {
  const t = useTheme()
  const layout = useLayout()
  return (
    <box flexDirection="column" marginTop={1}>
      <text fg={t.color.textMuted} attributes={t.attr.dim} wrapMode="none" content={props.label} />
      <For each={wrap(props.text, layout.measure())}>
        {(line) => <text fg={t.color.textSecondary} wrapMode="none" content={line} />}
      </For>
    </box>
  )
}

/**
 * Quoted text, set with its own line structure kept.
 *
 * `Paragraph` cannot be used for this. It runs the text through `wrap`, which splits on any
 * whitespace and rejoins on single spaces — so a clause whose paragraphs, sub-clause indents and
 * hard breaks are part of how it reads comes out as one reflowed block. The Python carries
 * `verbatim_text` "unchanged and never reflowed, truncated or whitespace-normalised" precisely
 * because the pack's copy is the authority and every rendering of it is a passthrough.
 *
 * So the source's own newlines are the line breaks, and wrapping happens only where a single line is
 * wider than the terminal — the one reflow a fixed grid leaves no choice about, and it is marked by
 * indenting the continuation so a reader can see which breaks are the clause's and which are ours.
 */
function Verbatim(props: { label: string; text: string }) {
  const t = useTheme()
  const layout = useLayout()
  const lines = () =>
    props.text.split("\n").flatMap((line) => {
      const measure = layout.measure() - 2
      if (line.length <= measure) return [line]
      const [first, ...rest] = wrap(line, measure)
      return [first ?? "", ...rest.map((row) => `  ${row}`)]
    })

  return (
    <box flexDirection="column" marginTop={1}>
      <text fg={t.color.textMuted} attributes={t.attr.dim} wrapMode="none" content={props.label} />
      <For each={lines()}>
        {(line) => (
          <text fg={t.color.textSecondary} attributes={t.attr.italic} wrapMode="none" content={line} />
        )}
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

/**
 * The findings reported beside this verdict, and nothing about the verdict itself.
 *
 * The wording is chosen so the pairing survives being read quickly: a `FAIL` under a `satisfied`
 * duty says *the duty was cleared on what it could check, and this measurement failed*, which is
 * two facts and not a contradiction. The block is drawn in the violation colour whatever the
 * verdict is, because the finding's own severity is not the verdict's.
 */
function Findings(props: { result: RequirementResult; showDecisionIndex: boolean }) {
  const t = useTheme()
  const layout = useLayout()
  const certificateFailures = () => props.result.findings.filter((f) => f.type === "certificate")

  return (
    <Show when={certificateFailures().length > 0}>
      <box flexDirection="column" marginTop={1}>
        <text
          fg={t.color.bad}
          attributes={t.attr.bold}
          wrapMode="none"
          content={
            props.result.verdict === "satisfied"
              ? "a certificate measurement failed under this satisfied duty"
              : "a certificate measurement failed"
          }
        />
        <For
          each={wrap(
            "The duty above was settled on what its engine could check. Separately, the " +
              "reason-deletion certificate over the decision(s) named below did not hold. Both are " +
              "reported; neither stands in for the other.",
            layout.measure(),
          )}
        >
          {(line) => <text fg={t.color.textSecondary} wrapMode="none" content={line} />}
        </For>
        <For each={certificateFailures()}>
          {(finding) => (
            <text
              fg={t.color.bad}
              wrapMode="none"
              content={
                props.showDecisionIndex && finding.decision_index !== null
                  ? `  · certificate FAIL at decision #${finding.decision_index}`
                  : "  · certificate FAIL at a certified decision"
              }
            />
          )}
        </For>
      </box>
    </Show>
  )
}

/**
 * The semantics an artefact claimed, beside the semantics it was measured against.
 *
 * A value gap is only readable next to what produced it, which is why the pair is printed together
 * and never the claim alone. `claimed_semantics` is a closed vocabulary on the Python side, so a
 * value outside it is named as unrecognised rather than printed as though it were one more
 * semantics this tool knows how to compare — an author's prose is not a semantics.
 */
function SemanticsGap(props: { result: RequirementResult }) {
  const t = useTheme()
  const records = () => {
    const raw = props.result.details[CERTIFICATE_KEY]
    return Array.isArray(raw) ? (raw as Record<string, unknown>[]) : []
  }
  const gaps = () =>
    records().filter((r) => r.claimed_semantics !== undefined || r.exact_semantics !== undefined)

  const claim = (record: Record<string, unknown>): string => {
    const claimed = record.claimed_semantics
    if (claimed === null || claimed === undefined) return "no semantics declared"
    if (!isClaimedSemantics(claimed)) {
      return `${JSON.stringify(claimed)} (not a semantics this build recognises)`
    }
    return claimed
  }

  return (
    <Show when={gaps().length > 0}>
      <box flexDirection="column" marginTop={1}>
        <text
          fg={t.color.textMuted}
          attributes={t.attr.dim}
          wrapMode="none"
          content="claimed semantics, and what it was measured against"
        />
        <For each={gaps()}>
          {(record) => (
            <box flexDirection="column">
              <text
                fg={t.color.text}
                wrapMode="none"
                content={
                  `decision #${String(record.decision_index)}  ·  claimed ${claim(record)}  ·  ` +
                  `measured against ${
                    record.exact_semantics === null || record.exact_semantics === undefined
                      ? "nothing exact"
                      : String(record.exact_semantics)
                  }`
                }
              />
              <Show when={record.value_gap !== null && record.value_gap !== undefined}>
                <text
                  fg={t.color.bad}
                  wrapMode="none"
                  content={
                    `  value gap ${String(record.value_gap)}  ·  engine ` +
                    `${String(record.engine_value)} vs exact ${String(record.exact_value)}`
                  }
                />
              </Show>
            </box>
          )}
        </For>
      </box>
    </Show>
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
  const layout = useLayout()
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
              layout.measure(),
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
  const layout = useLayout()
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
                  <For each={wrap(String(cert.attribution), layout.measure() - 2)}>
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
 * Three sections, against `render._lay_sections`'s three. The second is printed whether or not
 * anything was found, because **absence of a finding is never completeness**: silence under it reads
 * to this reader as a clean result, and it is not one. The third states how much of the pack this
 * run never settled, and is the bound on everything above it.
 *
 * Where the wording departs from the Python it is because the JSON cannot carry what the text
 * rendering quotes, and each departure says so on the spot. The *branches* never depart: which
 * sentence a reader gets is decided by the same counts the Python decides it by, and a divergence
 * there is a defect rather than an adaptation.
 */
function LayAccount() {
  const t = useTheme()
  const report = useReport()
  const layout = useLayout()

  /**
   * The certificates this run produced and the reasons they found unstated — gathered exactly as
   * `render._lay_sections` gathers them, which is over **every** result and with **no** deduplication.
   *
   * Both of those were wrong here, in ways that changed what this reader was told. The gather was
   * restricted to the `artifact` basis, and `anyMeasured` was set from the mere presence of the key
   * rather than from a certificate existing — so a result carrying an empty certificate list took
   * the *"every reason was stated"* branch where the Python takes the *"nothing measured that"*
   * branch, which are opposite claims to make to someone asking why they were refused. And the
   * reasons were passed through a `Set`, so two decisions that each left the same reason unstated
   * were reported as one.
   */
  const certified = () => {
    const missing: string[] = []
    let certificates = 0
    for (const result of report.results()) {
      const raw = result.details[CERTIFICATES_KEY]
      if (!Array.isArray(raw)) continue
      for (const cert of raw as Record<string, unknown>[]) {
        certificates += 1
        const reasons = cert.missing_reasons
        if (Array.isArray(reasons)) missing.push(...reasons.map(String))
      }
    }
    return { certificates, missing }
  }

  /**
   * `WHAT THIS REPORT COULD NOT CHECK`, in `render._lay_sections`'s three branches and its wording.
   *
   * The section is the whole reason the lay account can be read as an answer rather than as a
   * verdict: it is where a run says how much of the pack it never settled. Dropping it left this
   * reader — the one least able to notice the omission — with the findings and none of their
   * bounds. The section is omitted only when all three counts are zero, exactly as the Python omits
   * it, because a heading over nothing is the other half of the same defect.
   */
  const unchecked = () => {
    const results = report.results()
    const duties = (n: number) => (n === 1 ? "duty" : "duties")
    const lines: string[] = []
    const unattainable = results.filter((r) => r.strength === "unattainable").length
    const unsettled = results.filter(
      (r) => r.strength === null && r.verdict !== "not_applicable",
    ).length
    const inapplicable = results.filter((r) => r.verdict === "not_applicable").length
    if (unattainable > 0) {
      lines.push(
        `${unattainable} ${duties(unattainable)}: the system supplied nothing any check here ` +
          "could read, so it was not checked either way.",
      )
    }
    if (unsettled > 0) {
      lines.push(
        `${unsettled} ${duties(unsettled)}: no check in this report could settle it, so it was ` +
          "left open rather than answered.",
      )
    }
    if (inapplicable > 0) {
      lines.push(
        `${inapplicable} ${duties(inapplicable)}: not one this run applies to this system, so ` +
          "nothing here says it was met.",
      )
    }
    return lines
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
          layout.measure(),
        )}
      >
        {(line) => <text fg={t.color.textMuted} wrapMode="none" content={line} />}
      </For>

      {/*
        Printed whatever the answer — including when nothing measured it. Silence under this heading
        reads to this reader as a clean result and it is not one.

        The three branches are `render._lay_sections`'s, decided by the same two counts. The
        sentences are not quite its sentences: the Python's say "the reasons above", pointing at the
        decisions it quoted in its first section, and this rendering has no first section to point
        at — the JSON carries the findings of the run, not the log it read. Quoting the Python
        verbatim here would leave a reader chasing a passage that is not on the screen.
      */}
      <box flexDirection="column" marginTop={1}>
        <text
          fg={t.color.text}
          attributes={t.attr.bold}
          wrapMode="none"
          content="WHETHER THE STATED REASONS WERE ALL THE REASONS"
        />
        <Show
          when={certified().certificates > 0}
          fallback={
            <For
              each={wrap(
                "Nothing in this run measured that. No inference artefact was opened up, so this " +
                  "report does not say the reasons you were given were complete, and does not say " +
                  "they were not.",
                layout.measure(),
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
                  layout.measure(),
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

      {/*
        The third section of `render._lay_sections`, in its wording. It is dropped only when it has
        no line to carry, which is the Python's own condition.
      */}
      <Show when={unchecked().length > 0}>
        <box flexDirection="column" marginTop={1}>
          <text
            fg={t.color.text}
            attributes={t.attr.bold}
            wrapMode="none"
            content="WHAT THIS REPORT COULD NOT CHECK"
          />
          <For each={unchecked()}>
            {(line) => (
              <For each={wrap(line, layout.measure())}>
                {(row) => <text fg={t.color.textMuted} wrapMode="none" content={row} />}
              </For>
            )}
          </For>
        </box>
      </Show>
    </box>
  )
}
