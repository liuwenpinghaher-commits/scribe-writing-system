import { mkdir, writeFile } from 'node:fs/promises'
import { dirname } from 'node:path'

export function compactDiagnostic(value, limit = 1200) {
  const serialized = JSON.stringify(value)
  return (serialized === undefined ? String(value) : serialized).slice(0, limit)
}

export async function captureJourneyResult(run) {
  try {
    const value = await run()
    return { ok: true, ...value }
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : compactDiagnostic(error),
    }
  }
}

export async function writeJsonArtifact(path, payload) {
  await mkdir(dirname(path), { recursive: true })
  await writeFile(path, JSON.stringify(payload, null, 2))
}
