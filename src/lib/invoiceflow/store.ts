import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  acknowledgeSecurity,
  acknowledgeVariance,
  approveInvoice,
  confirmDuplicate,
  correctField,
  markUnique,
  rejectInvoice,
  rerunValidation,
  resetDemo,
  retryDelivery,
  simulateWorkflow,
  switchUser,
  syncAccounting,
  type ActionResult,
} from "./engine.ts";
import { createSeedState } from "./seed.ts";
import type { AppState, FieldName, WorkflowExecution } from "./types.ts";

interface Actions {
  hydrateIfNeeded: () => void;
  apply: (result: ActionResult) => ActionResult;
  switchUser: (userId: string) => ActionResult;
  resetDemo: () => ActionResult;
  correctField: (publicId: string, name: FieldName, value: string) => ActionResult;
  rerunValidation: (publicId: string) => ActionResult;
  acknowledgeVariance: (publicId: string, reason: string) => ActionResult;
  acknowledgeSecurity: (publicId: string, reason: string) => ActionResult;
  approveInvoice: (publicId: string, reason?: string) => ActionResult;
  rejectInvoice: (publicId: string, reason: string) => ActionResult;
  confirmDuplicate: (publicId: string) => ActionResult;
  markUnique: (publicId: string, reason: string) => ActionResult;
  syncAccounting: (publicId: string) => ActionResult;
  retryDelivery: (deliveryId: string) => ActionResult;
  simulateWorkflow: (workflow: WorkflowExecution["workflow"], invoicePublicId: string | null) => ActionResult;
}

export type InvoiceStore = AppState & Actions;

export const useInvoiceStore = create<InvoiceStore>()(
  persist(
    (set, get) => {
      const seed = createSeedState();
      const apply = (result: ActionResult) => {
        set({ ...result.state });
        return result;
      };
      return {
        ...seed,
        hydrateIfNeeded: () => {
          if (get().invoices.length === 0) set(createSeedState());
        },
        apply,
        switchUser: (userId) => apply(switchUser(get(), userId)),
        resetDemo: () => apply(resetDemo(get())),
        correctField: (publicId, name, value) => apply(correctField(get(), publicId, name, value)),
        rerunValidation: (publicId) => apply(rerunValidation(get(), publicId)),
        acknowledgeVariance: (publicId, reason) => apply(acknowledgeVariance(get(), publicId, reason)),
        acknowledgeSecurity: (publicId, reason) => apply(acknowledgeSecurity(get(), publicId, reason)),
        approveInvoice: (publicId, reason) => apply(approveInvoice(get(), publicId, reason)),
        rejectInvoice: (publicId, reason) => apply(rejectInvoice(get(), publicId, reason)),
        confirmDuplicate: (publicId) => apply(confirmDuplicate(get(), publicId)),
        markUnique: (publicId, reason) => apply(markUnique(get(), publicId, reason)),
        syncAccounting: (publicId) => apply(syncAccounting(get(), publicId)),
        retryDelivery: (deliveryId) => apply(retryDelivery(get(), deliveryId)),
        simulateWorkflow: (workflow, invoicePublicId) => apply(simulateWorkflow(get(), workflow, invoicePublicId)),
      };
    },
    {
      name: "invoiceflow-demo",
      partialize: (s) => ({
        currentUserId: s.currentUserId,
        invoices: s.invoices,
        vendors: s.vendors,
        deliveries: s.deliveries,
        auditEvents: s.auditEvents,
        workflowExecutions: s.workflowExecutions,
        ingestionKeys: s.ingestionKeys,
        syncKeys: s.syncKeys,
        purchaseOrders: s.purchaseOrders,
        dailyVolume: s.dailyVolume,
        workspace: s.workspace,
        users: s.users,
      }),
    },
  ),
);

export function useCurrentUser() {
  return useInvoiceStore((s) => s.users.find((u) => u.id === s.currentUserId) ?? s.users[0]);
}
