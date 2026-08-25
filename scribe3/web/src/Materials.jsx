import { MaterialImport } from './MaterialImport'
import { MaterialNetwork } from './MaterialNetwork'
import { matLeafNode } from './MaterialList'

export { MATERIAL_KINDS } from './materialKinds'
export { MaterialNew } from './MaterialNew'
export { MaterialDetail } from './MaterialDetail'
export { MaterialList } from './MaterialList'

export function MaterialImportPane({ onCancel, onImported }) {
  return <MaterialImport onCancel={onCancel} onImported={onImported} />
}

export function MaterialNetworkPane({ onSelect }) {
  return <MaterialNetwork onSelect={(m) => onSelect?.(matLeafNode(m))} />
}
