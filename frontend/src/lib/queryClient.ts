import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (count, error) => {
        const status = (error as { response?: { status?: number } })?.response?.status;
        // 仅对 5xx 或网络错误重试，4xx 不重试
        return count < 1 && (!status || status >= 500);
      },
      staleTime: 10_000,
    },
  },
});
