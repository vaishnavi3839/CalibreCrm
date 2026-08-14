import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function tempClass(temp?: string | null) {
  if (temp === "hot") return "temp-hot";
  if (temp === "warm") return "temp-warm";
  if (temp === "cold") return "temp-cold";
  return "bg-cloud-100 text-navy-700";
}

export function formatLabel(value?: string | null) {
  if (!value) return "—";
  return value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
