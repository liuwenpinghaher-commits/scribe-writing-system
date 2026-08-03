import './authFetch.js' // must be first: wraps fetch for Bearer + 401 → login
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ErrorBoundary } from './ErrorBoundary.jsx'
// toast 统一走 sonner(ui/Toast 的 ToastHost,由 App 顶层挂载);不再包旧自绘 ToastProvider。
createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>,
)
