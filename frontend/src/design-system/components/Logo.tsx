import logoUrl from "../../assets/logo.jpeg";
import { cn } from "../utils/cn";

interface LogoProps {
  className?: string;
  size?: number;
}

/** The Advantage Pro / Vectra Technosoft brand mark. */
export function Logo({ className, size = 96 }: LogoProps) {
  return (
    <img
      src={logoUrl}
      alt="Advantage Pro — Vectra Technosoft"
      width={size}
      height={size}
      className={cn("rounded-full", className)}
    />
  );
}
