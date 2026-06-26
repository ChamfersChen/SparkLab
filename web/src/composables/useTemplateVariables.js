/**
 * 模板变量提取与提示语覆盖校验。
 *
 * 与后端 sparklab.services.template_service.TemplateService._extract_variables
 * 保持一致的 `\{\{(.*?)\}\}` 正则与 dict.fromkeys 去重顺序。
 *
 * - extractVariables(input): 从 Input 段提取所有 {{变量名}},按出现顺序去重返回
 * - validateHintsCoverage(input, hints): 校验 input 中出现的每个变量都已被 hints 覆盖,
 *   返回缺失的变量名数组(空数组 = 全部覆盖)
 *
 * 纯函数风格,无副作用,可在 setup 之外或测试中直接 import 使用。
 */

const VAR_PATTERN = /\{\{(.*?)\}\}/g

export function extractVariables(inputText) {
  if (!inputText) return []
  const seen = new Set()
  const out = []
  for (const match of inputText.matchAll(VAR_PATTERN)) {
    const name = match[1]
    if (!seen.has(name)) {
      seen.add(name)
      out.push(name)
    }
  }
  return out
}

export function validateHintsCoverage(inputText, hints) {
  if (hints == null) return []
  const used = new Set(extractVariables(inputText))
  const covered = new Set(Object.keys(hints))
  return extractVariables(inputText).filter((v) => !covered.has(v))
}
