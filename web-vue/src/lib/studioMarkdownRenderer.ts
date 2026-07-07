import MarkdownIt from 'markdown-it'
import { highlightStudioCode } from '@/lib/studioMarkdownHighlighter'

interface StudioMarkdownRenderOptions {
  cache?: boolean
}

const MAX_RENDER_CACHE_SIZE = 360
const renderCache = new Map<string, string>()

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight: (code, language) => highlightStudioCode(code, language || 'text'),
})

markdown.renderer.rules.fence = (tokens, idx, options) => {
  const token = tokens[idx]
  const language = token.info.trim().split(/\s+/)[0] || 'text'
  const highlighted = options.highlight?.(token.content, language, '') || markdown.utils.escapeHtml(token.content)
  const langLabel = markdown.utils.escapeHtml(language)
  return `<div class="studio-code-block" data-language="${langLabel}">`
    + `<button type="button" class="studio-code-copy" title="复制代码">复制</button>`
    + `<pre class="hljs studio-code-pre">`
    + `<code class="language-${langLabel}">${highlighted}</code>`
    + `</pre>`
    + `</div>`
}

export function renderStudioMarkdown(content: string, options: StudioMarkdownRenderOptions = {}) {
  const key = String(content || '')
  if (options.cache === false) return renderPreparedStudioMarkdown(key)

  const cached = renderCache.get(key)
  if (cached !== undefined) {
    renderCache.delete(key)
    renderCache.set(key, cached)
    return cached
  }

  const rendered = renderPreparedStudioMarkdown(key)
  renderCache.set(key, rendered)
  while (renderCache.size > MAX_RENDER_CACHE_SIZE) {
    const firstKey = renderCache.keys().next().value
    if (firstKey === undefined) break
    renderCache.delete(firstKey)
  }
  return rendered
}

function renderPreparedStudioMarkdown(content: string) {
  return markdown.render(prepareStudioMarkdownContent(content))
}

function prepareStudioMarkdownContent(content: string) {
  return wrapHtmlDocumentCode(String(content || ''))
}

function wrapHtmlDocumentCode(content: string) {
  if (!content || content.includes('```') || content.includes('~~~')) return content
  const firstContentIndex = content.search(/\S/)
  if (firstContentIndex < 0) return content

  const leading = content.slice(0, firstContentIndex)
  const body = content.slice(firstContentIndex)
  if (!/^<!doctype\s+html>/i.test(body)) return content

  const closesHtmlDocument = /<\/html>\s*$/i.test(body)
  return `${leading}\n\`\`\`html\n${body}${closesHtmlDocument ? '\n```\n' : ''}`
}
