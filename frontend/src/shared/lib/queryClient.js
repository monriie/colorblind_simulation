import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Soal kuis tidak berubah dalam satu sesi -> stale time panjang,
      // supaya pindah-pindah halaman kuis tidak refetch berulang.
      staleTime: 5 * 60 * 1000, // 5 menit
      retry: 1,
    },
  },
})
