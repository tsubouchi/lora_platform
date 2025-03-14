"use client"

import * as React from "react"
import {
  DropZone as AriaDropZone,
  DropZoneProps as AriaDropZoneProps,
  composeRenderProps,
} from "react-aria-components"

import { cn } from "@/lib/utils"

const DropZone = ({ className, ...props }: AriaDropZoneProps) => (
  <AriaDropZone
    className={composeRenderProps(className, (className) =>
      cn(
        "flex h-[150px] w-full flex-col items-center justify-center gap-2 rounded-md border border-dashed text-white ring-offset-background",
        /* Drop Target */
        "data-[drop-target]:border-solid data-[drop-target]:border-primary-500 data-[drop-target]:bg-[#111]",
        /* Focus Visible */
        "data-[focus-visible]:outline-none data-[focus-visible]:ring-2 data-[focus-visible]:ring-primary-500 data-[focus-visible]:ring-offset-2",
        className
      )
    )}
    {...props}
  />
)

export { DropZone }

export function DropZoneDemo() {
  let [dropped, setDropped] = React.useState(false)

  return (
    <DropZone onDrop={() => setDropped(true)} className='bg-[#0f0f0f]'>
      <p className="text-white">
        {dropped ? "Successful drop!" : "Drop files here"}
      </p>
    </DropZone>
  )
} 