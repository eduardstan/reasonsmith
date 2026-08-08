/**
 * Clickable surface — pointer cursor via renderer, hover highlight, single/double click.
 */

import { type JSX, createSignal } from "solid-js"
import type { MousePointerStyle } from "@opentui/core"
import { useRenderer } from "@opentui/solid"
import { useTheme } from "../context/theme.tsx"

export interface ClickableProps {
  readonly children: JSX.Element
  readonly onClick?: () => void
  readonly onDoubleClick?: () => void
  readonly onHover?: () => void
  readonly onLeave?: () => void
  readonly cursor?: MousePointerStyle
  readonly active?: boolean
  readonly flexDirection?: "row" | "column"
  readonly gap?: number
  readonly height?: number
  readonly width?: number | "auto" | `${number}%`
  readonly flexGrow?: number
  readonly flexShrink?: number
  readonly minWidth?: number
  readonly paddingLeft?: number
  readonly paddingRight?: number
}

export function Clickable(props: ClickableProps) {
  const t = useTheme()
  const renderer = useRenderer()
  const [hovered, setHovered] = createSignal(false)
  let lastUp = 0

  const background = () => {
    if (props.active) return t.color.surfaceRaised
    if (hovered()) return t.color.surfaceRaised
    return undefined
  }

  const pointer = props.cursor ?? "pointer"

  return (
    <box
      flexDirection={props.flexDirection ?? "row"}
      gap={props.gap}
      height={props.height}
      width={props.width}
      flexGrow={props.flexGrow}
      flexShrink={props.flexShrink}
      minWidth={props.minWidth}
      paddingLeft={props.paddingLeft}
      paddingRight={props.paddingRight}
      backgroundColor={background()}
      onMouseOver={() => {
        setHovered(true)
        renderer.setMousePointer(pointer)
        props.onHover?.()
      }}
      onMouseOut={() => {
        setHovered(false)
        renderer.setMousePointer("default")
        props.onLeave?.()
      }}
      onMouseUp={() => {
        const now = Date.now()
        if (props.onDoubleClick && now - lastUp < 400) {
          props.onDoubleClick()
          lastUp = 0
          return
        }
        lastUp = now
        props.onClick?.()
      }}
    >
      {props.children}
    </box>
  )
}
