// vitest setup: Node.js 25 内置 localStorage 存根无 clear/setItem 等方法,
// 用简单的内存 Map 实现覆盖,让测试中 localStorage 行为正常。
const store = new Map()
const mockLocalStorage = {
  getItem: (k) => store.has(k) ? store.get(k) : null,
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
  clear: () => store.clear(),
  get length() { return store.size },
  key: (i) => [...store.keys()][i] ?? null,
}
Object.defineProperty(globalThis, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
  configurable: true,
})
