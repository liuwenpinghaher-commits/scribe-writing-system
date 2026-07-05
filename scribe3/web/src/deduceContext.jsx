import { createContext, useContext, useState } from 'react'
// 演绎当前选中:'truth'(场景真相)或某 character_id。左树选、中区显示,共享一份。
const Ctx = createContext(null)
export function DeduceProvider({ children }) {
  const [selected, setSelected] = useState('truth')
  return <Ctx.Provider value={{ selected, setSelected }}>{children}</Ctx.Provider>
}
export function useDeduceSel() { return useContext(Ctx) || { selected: 'truth', setSelected: () => {} } }
