import { initTRPC } from "@trpc/server";
import superjson from "superjson";

import { getDb } from "@/server/db";

export type TRPCContext = {
  db: ReturnType<typeof getDb>;
};

export const createTRPCContext = async (): Promise<TRPCContext> => ({
  db: getDb(),
});

const t = initTRPC.context<TRPCContext>().create({
  transformer: superjson,
});

export const createTRPCRouter = t.router;
export const publicProcedure = t.procedure;
