import { defineConfig } from 'vitepress'

const base = process.env.DOCS_BASE || '/'

const zhTheme = {
  siteTitle: 'Enterprise Agent',
  nav: [
    { text: '指南', link: '/getting-started' },
    { text: '架构', link: '/ARCHITECTURE' },
    { text: '路线图', link: '/roadmap' },
    { text: '面试', link: '/INTERVIEW' },
    { text: '在线 Demo', link: 'https://agent.majhoon.site' }
  ],
  sidebar: [
    {
      text: '概览',
      items: [
        { text: '项目介绍', link: '/' },
        { text: '快速开始', link: '/getting-started' },
        { text: '系统架构', link: '/ARCHITECTURE' },
        { text: '开发路线图', link: '/roadmap' }
      ]
    },
    {
      text: '演示',
      items: [
        { text: '演示指南', link: '/DEMO' }
      ]
    },
    {
      text: '面试',
      items: [
        { text: '面试手册', link: '/INTERVIEW' }
      ]
    }
  ],
  outline: {
    level: [2, 3] as [number, number],
    label: '本页目录'
  },
  docFooter: {
    prev: '上一页',
    next: '下一页'
  },
  editLink: {
    pattern: 'https://github.com/yvanu/enterprise-agent-platform/edit/main/docs/:path',
    text: '在 GitHub 上编辑此页'
  },
  lastUpdated: {
    text: '最后更新'
  },
  returnToTopLabel: '返回顶部',
  sidebarMenuLabel: '菜单',
  darkModeSwitchLabel: '主题',
  lightModeSwitchTitle: '切换到浅色模式',
  darkModeSwitchTitle: '切换到深色模式',
  langMenuLabel: '切换语言'
}

const enTheme = {
  siteTitle: 'Enterprise Agent',
  nav: [
    { text: 'Guide', link: '/en/getting-started' },
    { text: 'Architecture', link: '/en/ARCHITECTURE' },
    { text: 'Roadmap', link: '/en/roadmap' },
    { text: 'Interview', link: '/en/INTERVIEW' },
    { text: 'Live Demo', link: 'https://agent.majhoon.site' }
  ],
  sidebar: [
    {
      text: 'Overview',
      items: [
        { text: 'Introduction', link: '/en/' },
        { text: 'Getting Started', link: '/en/getting-started' },
        { text: 'Architecture', link: '/en/ARCHITECTURE' },
        { text: 'Development Roadmap', link: '/en/roadmap' }
      ]
    },
    {
      text: 'Operate',
      items: [
        { text: 'Demo Guide', link: '/en/DEMO' }
      ]
    },
    {
      text: 'Interview',
      items: [
        { text: 'Interview Handbook', link: '/en/INTERVIEW' }
      ]
    }
  ],
  outline: {
    level: [2, 3] as [number, number],
    label: 'On this page'
  },
  docFooter: {
    prev: 'Previous',
    next: 'Next'
  },
  editLink: {
    pattern: 'https://github.com/yvanu/enterprise-agent-platform/edit/main/docs/:path',
    text: 'Edit this page on GitHub'
  },
  lastUpdated: {
    text: 'Updated'
  },
  returnToTopLabel: 'Return to top',
  sidebarMenuLabel: 'Menu',
  darkModeSwitchLabel: 'Theme',
  lightModeSwitchTitle: 'Switch to light theme',
  darkModeSwitchTitle: 'Switch to dark theme',
  langMenuLabel: 'Change language'
}

export default defineConfig({
  base,
  cleanUrls: true,
  lastUpdated: true,
  head: [
    ['meta', { name: 'theme-color', content: '#ffffff' }],
    ['meta', { property: 'og:title', content: 'Enterprise Agent Platform' }],
    ['meta', { property: 'og:description', content: 'Safe, observable, governable Multi-Agent Control Plane' }]
  ],

  locales: {
    root: {
      label: '简体中文',
      lang: 'zh-CN',
      title: 'Enterprise Agent Platform',
      description: '面向企业场景的安全、可观测、可治理 Multi-Agent Control Plane。',
      themeConfig: zhTheme,
      markdown: {
        container: {
          tipLabel: '提示',
          warningLabel: '警告',
          dangerLabel: '危险',
          infoLabel: '信息',
          detailsLabel: '详情'
        },
        codeCopyButton: {
          tooltipText: '复制代码',
          copiedText: '已复制'
        }
      }
    },
    en: {
      label: 'English',
      lang: 'en-US',
      link: '/en/',
      title: 'Enterprise Agent Platform',
      description: 'Architecture, operations and interview documentation for an enterprise Multi-Agent control plane.',
      themeConfig: enTheme,
      markdown: {
        container: {
          tipLabel: 'TIP',
          warningLabel: 'WARNING',
          dangerLabel: 'DANGER',
          infoLabel: 'INFO',
          detailsLabel: 'Details'
        },
        codeCopyButton: {
          tooltipText: 'Copy code',
          copiedText: 'Copied'
        }
      }
    }
  },

  themeConfig: {
    socialLinks: [
      { icon: 'github', link: 'https://github.com/yvanu/enterprise-agent-platform' }
    ],
    search: {
      provider: 'local'
    },
    footer: {
      message: 'Enterprise Agent Platform · Architecture and interview documentation',
      copyright: 'Built from the project repository'
    },
    i18nRouting: true
  }
})
