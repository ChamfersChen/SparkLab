/**
 * 安全复制文本到剪贴板, HTTP 环境下降级为 execCommand
 * navigator.clipboard 需要 HTTPS 或 localhost, 否则为 undefined
 */
export async function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text)
  }
  // 降级: 使用 textarea + execCommand
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}
