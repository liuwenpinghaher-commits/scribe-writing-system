import { Component } from 'react'

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('[scribe3] UI 渲染异常:', error, info?.componentStack)
  }

  reset = () => this.setState({ error: null })

  render() {
    if (this.state.error) {
      return (
        <div role="alert" className="m-3 rounded-xl border border-danger/40 bg-danger/5 p-4 max-w-full">
          <h2 className="text-ink text-[15px] font-semibold mb-1">界面出错了</h2>
          <p className="text-faint text-[13px] mb-3">
            本视图渲染异常，你的书稿未受影响。可重试或刷新页面。
          </p>
          <pre className="text-[11px] text-faint/80 whitespace-pre-wrap break-words mb-3">
            {String(this.state.error?.message || this.state.error)}
          </pre>
          <button
            onClick={this.reset}
            className="h-8 px-3 rounded-lg border border-line text-[13px] text-ink hover:border-brand/50"
          >
            重试
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
