import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        // Base
        "h-10 w-full min-w-0 rounded-lg px-3 py-2 text-sm",
        // Colors
        "bg-[#0a0a0f] text-slate-200 border border-[#2a2a3a]",
        "placeholder:text-slate-600",
        // Focus
        "focus:outline-none focus:border-cyan-500/50 focus:shadow-[0_0_20px_-5px_rgba(34,211,238,0.3)]",
        // Hover
        "hover:border-[#3a3a4a]",
        // Transition
        "transition-all duration-200",
        // File input
        "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-slate-300",
        // Disabled
        "disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { Input }
