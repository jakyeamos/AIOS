import { appRouter } from "@/server/routers/_app";
import { createTRPCContext } from "@/server/trpc";

export const getCaller = async (): Promise<ReturnType<typeof appRouter.createCaller>> => {
  const context = await createTRPCContext();

  return appRouter.createCaller(context);
};
