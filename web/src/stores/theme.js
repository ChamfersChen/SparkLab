import { defineStore } from 'pinia'

/**
 * 主题切换 - light / dark。
 * 通过给 <html> 添加 'dark' class 触发 :root.dark 下的 CSS 变量覆盖。
 */
export const useThemeStore = defineStore('theme', {
  state: () => ({
    theme: 'light' // 'light' | 'dark'
  }),
  actions: {
    apply() {
      const html = document.documentElement
      if (this.theme === 'dark') {
        html.classList.add('dark')
      } else {
        html.classList.remove('dark')
      }
    },
    setTheme(value) {
      this.theme = value
      this.apply()
    },
    toggle() {
      this.setTheme(this.theme === 'light' ? 'dark' : 'light')
    }
  },
  persist: { pick: ['theme'] }
})
