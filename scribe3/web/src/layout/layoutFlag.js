export function isFourPaneLayoutEnabled(storage = localStorage) {
  try {
    return storage?.getItem?.('s3.layout.v2') !== '0'
  } catch {
    return true
  }
}
