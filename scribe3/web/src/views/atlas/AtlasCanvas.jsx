import { useEffect, useMemo } from 'react'
import { MultiDirectedGraph } from 'graphology'
import { SigmaContainer, useLoadGraph, useRegisterEvents, useSigma } from '@react-sigma/core'
import '@react-sigma/core/lib/style.css'
import { Loader2 } from 'lucide-react'
import { REL_LABEL, relColor } from '../../lib/relColors'
import { buildGraph } from './graphBuild.js'

function GraphContent({ data, focus, theme, onPickNode }) {
  const loadGraph = useLoadGraph()
  const registerEvents = useRegisterEvents()
  const sigma = useSigma()

  useEffect(() => {
    const g = buildGraph(data, focus, theme)
    loadGraph(g)
    requestAnimationFrame(() => {
      try { sigma.getCamera().animatedReset({ duration: 0 }) } catch { /* */ }
    })
  }, [data, focus, theme, loadGraph, sigma])

  useEffect(() => {
    registerEvents({
      clickNode: ({ node }) => {
        const g = sigma.getGraph()
        if (!g.hasNode(node)) return
        onPickNode({
          id: node,
          label: g.getNodeAttribute(node, '_rawlabel'),
          type: g.getNodeAttribute(node, '_type'),
          secret: g.getNodeAttribute(node, '_secret'),
        })
      },
      clickStage: () => onPickNode(null),
    })
  }, [registerEvents, sigma, onPickNode])

  useEffect(() => {
    window.__s3Atlas = {
      nodes: () => sigma.getGraph().nodes(),
      nodeViewport: (id) => {
        const g = sigma.getGraph()
        if (!g.hasNode(id)) return null
        return sigma.graphToViewport({ x: g.getNodeAttribute(id, 'x'), y: g.getNodeAttribute(id, 'y') })
      },
    }
    return () => { delete window.__s3Atlas }
  }, [sigma])

  return null
}

export function AtlasCanvas({ raw, focus, theme, loading, present, onPickNode }) {
  const sigmaSettings = useMemo(() => ({
    renderLabels: true,
    labelColor: { color: theme['--color-ink'] },
    labelFont: 'inherit',
    labelSize: 12,
    labelDensity: 0.7,
    labelGridCellSize: 70,
    defaultEdgeType: 'arrow',
    enableEdgeEvents: false,
    allowInvalidContainer: true,
  }), [theme])

  return (
    <div className="flex-1 min-h-0 min-w-0 relative" data-testid="atlas-canvas">
      <SigmaContainer
        key={focus}
        graph={MultiDirectedGraph}
        settings={sigmaSettings}
        style={{ width: '100%', height: '100%', background: 'transparent' }}
      >
        {raw && (
          <GraphContent data={raw} focus={focus} theme={theme} onPickNode={onPickNode} />
        )}
      </SigmaContainer>
      {loading && (
        <div className="absolute top-3 left-3 z-10 inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface/90 backdrop-blur px-2.5 py-1 text-f12 text-faint shadow-sm">
          <Loader2 size={13} className="animate-spin" /> 更新中…
        </div>
      )}
      {present.length > 0 && (
        <div className="absolute bottom-3 left-3 z-10 rounded-lg border border-line bg-surface/90 backdrop-blur px-3 py-2 flex flex-col gap-1 shadow-sm">
          <span className="text-meta font-medium text-faint mb-0.5">角色关系</span>
          {present.map((rel) => (
            <span key={rel} className="inline-flex items-center gap-1.5 text-meta text-ink">
              <i className="w-3 h-[2px] rounded-full inline-block" style={{ background: relColor(rel) }} />
              {REL_LABEL[rel] || rel}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
