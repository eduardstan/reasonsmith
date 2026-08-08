/**
 * The border character sets, named once so panels agree.
 *
 * Lifted from nikcli's `component/border.tsx`. Borders are a layout primitive here rather than a
 * decoration: `SplitBorder` is the single rule between two columns, `GlassBorder` is the rounded box
 * a dialog floats in, and `EmptyBorder` reserves the cells without drawing them — which is how a
 * panel keeps its width when its rule is turned off, instead of reflowing every row beside it.
 */

export const EmptyBorder = {
  topLeft: "",
  bottomLeft: "",
  vertical: "",
  topRight: "",
  bottomRight: "",
  horizontal: " ",
  bottomT: "",
  topT: "",
  cross: "",
  leftT: "",
  rightT: "",
} as const

/** One vertical rule, for a column that sits beside another. */
export const SplitBorder = {
  border: ["left"] as const,
  customBorderChars: { ...EmptyBorder, vertical: "│" },
}

/** The rounded box a dialog is drawn in. */
export const GlassBorder = {
  border: ["top", "bottom", "left", "right"] as const,
  customBorderChars: {
    topLeft: "╭",
    topRight: "╮",
    bottomLeft: "╰",
    bottomRight: "╯",
    vertical: "│",
    horizontal: "─",
    topT: "┬",
    bottomT: "┴",
    leftT: "├",
    rightT: "┤",
    cross: "┼",
  },
}

/** A single rule under a masthead or between sections. */
export const SEPARATOR = {
  horizontal: "─",
  vertical: "│",
  dot: "·",
} as const
