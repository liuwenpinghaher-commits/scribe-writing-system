export function displayToolName(name = '') {
  return String(name)
    .replace(/^mcp_scribe3_(?:read|write)_/, '')
    .replace(/^mcp_scribe3_/, '')
    .replace(/^s3_/, '')
}
