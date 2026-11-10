import { useMutation } from '@tanstack/react-query'
import { analyzeSimulation } from '@/features/simulation/api/simulationApi.js'

export function useAnalyzeSimulation(options = {}) {
  return useMutation({ mutationFn: analyzeSimulation, ...options })
}

