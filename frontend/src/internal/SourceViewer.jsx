import React, { useEffect, useState, useMemo } from 'react'
import hljs from 'highlight.js/lib/common'
import 'highlight.js/styles/github.css'
import internal from './api'

const EXT_LANG = {
  js: 'javascript', jsx: 'javascript',
  ts: 'typescript', tsx: 'typescript',
  py: 'python', json: 'json', css: 'css', html: 'xml',
  md: 'markdown', sh: 'bash', yml: 'yaml', yaml: 'yaml',
  sql: 'sql', toml: 'ini',
}

function HighlightedCode({ content, language }) {
  const html = useMemo(() => {
    const lang = EXT_LANG[language] || (hljs.getLanguage(language) ? language : null)
    try {
      if (lang) return hljs.highlight(content, { language: lang, ignoreIllegals: true }).value
      return hljs.highlightAuto(content).value
    } catch {
      // Fallback to a safely-escaped raw view if highlighting blows up.
      const div = document.createElement('div'); div.textContent = content
      return div.innerHTML
    }
  }, [content, language])
  return (
    <pre className="overflow-auto text-xs p-3 leading-relaxed whitespace-pre flex-1">
      <code
        className={`hljs language-${EXT_LANG[language] || language || 'plaintext'}`}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </pre>
  )
}

function FileTree({ items, onPick, picked }) {
  return (
    <ul className="text-xs font-mono">
      {items.map((it) => (
        <li key={it.path}>
          <button
            onClick={() => onPick(it)}
            className={`block w-full text-left px-2 py-0.5 rounded hover:bg-slate-100 ${
              picked === it.path ? 'bg-slate-900 text-white hover:bg-slate-900' : ''
            }`}
          >
            {it.type === 'dir' ? '📁 ' : '📄 '}{it.name}
            {it.type === 'file' && it.size !== null && (
              <span className="text-slate-400 ml-1">{Math.round(it.size / 1024)}k</span>
            )}
          </button>
        </li>
      ))}
    </ul>
  )
}

export default function SourceViewer() {
  const [path, setPath] = useState('')
  const [tree, setTree] = useState([])
  const [crumbs, setCrumbs] = useState([])
  const [file, setFile] = useState(null)
  const [err, setErr] = useState('')

  const loadTree = async (p) => {
    setErr('')
    try {
      const { data } = await internal.get('/api/internal/portal/source/tree', {
        params: p ? { path: p } : {},
      })
      setTree(data.items)
      setPath(data.path || '')
      setCrumbs((data.path || '').split('/').filter(Boolean))
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Failed to load tree')
    }
  }

  useEffect(() => { loadTree('') }, [])

  const pick = async (it) => {
    if (it.type === 'dir') {
      loadTree(it.path)
      return
    }
    setErr('')
    try {
      const { data } = await internal.get('/api/internal/portal/source/file', {
        params: { path: it.path },
      })
      setFile(data)
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Failed to load file')
      setFile(null)
    }
  }

  const goCrumb = (i) => {
    const p = crumbs.slice(0, i + 1).join('/')
    loadTree(p)
  }

  const copyPath = () => {
    if (file?.path) navigator.clipboard.writeText(file.path)
  }

  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-2xl font-semibold">Source viewer</h1>
        <p className="text-xs text-slate-500">
          Read-only browser of <code>backend/</code> and <code>frontend/src/</code>.
          To make actual changes, edit in the workspace and redeploy.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-1 text-xs">
        <button onClick={() => loadTree('')} className="text-slate-500 hover:text-slate-900">root</button>
        {crumbs.map((c, i) => (
          <React.Fragment key={i}>
            <span className="text-slate-300">/</span>
            <button onClick={() => goCrumb(i)} className="text-slate-700 hover:text-slate-900 font-mono">{c}</button>
          </React.Fragment>
        ))}
      </div>
      {err && <div className="text-xs text-red-600">{err}</div>}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="border border-slate-200 rounded-md p-2 max-h-[75vh] overflow-y-auto">
          <FileTree items={tree} onPick={pick} picked={file?.path} />
        </div>
        <div className="md:col-span-3 border border-slate-200 rounded-md overflow-hidden flex flex-col max-h-[75vh]">
          {!file ? (
            <div className="text-sm text-slate-500 p-4">Select a file to view its contents.</div>
          ) : (
            <>
              <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border-b border-slate-200">
                <code className="text-xs font-mono">{file.path}</code>
                <span className="text-xs text-slate-500">{Math.round(file.size / 1024)} kB</span>
                <button onClick={copyPath} className="ml-auto text-xs px-2 py-0.5 bg-slate-200 rounded">
                  Copy path
                </button>
              </div>
              {file.is_binary ? (
                <div className="p-4 text-sm text-slate-500">Binary file — preview unavailable.</div>
              ) : (
                <HighlightedCode content={file.content} language={file.language} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
