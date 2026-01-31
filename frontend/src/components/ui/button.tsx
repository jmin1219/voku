import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-semibold transition-all duration-200 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none",
  {
    variants: {
      variant: {
        default: 
          "bg-gradient-to-r from-cyan-500 to-cyan-400 text-black " +
          "shadow-[0_0_20px_-5px_rgba(34,211,238,0.5)] " +
          "hover:shadow-[0_0_30px_-5px_rgba(34,211,238,0.7)] hover:scale-[1.02] " +
          "active:scale-[0.98]",
        destructive:
          "bg-red-500/20 text-red-400 border border-red-500/30 " +
          "hover:bg-red-500/30 hover:shadow-[0_0_20px_-5px_rgba(248,113,113,0.3)]",
        outline:
          "border border-[#2a2a3a] bg-transparent text-slate-300 " +
          "hover:bg-[#1a1a24] hover:border-[#3a3a4a] hover:text-slate-100",
        secondary:
          "bg-[#1a1a24] text-slate-300 border border-[#2a2a3a] " +
          "hover:bg-[#22222e] hover:text-slate-100",
        ghost:
          "text-slate-400 hover:bg-[#1a1a24] hover:text-slate-200",
        link: "text-cyan-400 underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-5 py-2",
        xs: "h-7 gap-1 rounded-md px-2.5 text-xs",
        sm: "h-9 rounded-lg gap-1.5 px-4",
        lg: "h-12 rounded-lg px-8 text-base",
        icon: "size-10",
        "icon-xs": "size-7 rounded-md",
        "icon-sm": "size-9",
        "icon-lg": "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
