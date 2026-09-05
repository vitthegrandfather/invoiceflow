import { toast } from "sonner";
import type { ActionResult } from "./engine.ts";

export function showResult(result: ActionResult) {
  if (!result.toast) return;
  const opts = { description: result.toast.description };
  if (result.toast.tone === "error") toast.error(result.toast.title, opts);
  else if (result.toast.tone === "success") toast.success(result.toast.title, opts);
  else toast.message(result.toast.title, opts);
}
