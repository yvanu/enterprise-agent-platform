import { defineConfig } from 'vitepress'

const base = process.env.DOCS_BASE || '/'

export default defineConfig({
  title: 'Enterprise Agent Platform',
  description: 'Architecture, operations and interview documentation for an enterprise Multi-Agent control plane.',
  base,
  cleanUrls: true,
  lastUpdated: true,
  head: [
    ['meta', { name: 'theme-color', content: '#ffffff' }],
    ['meta', { property: 'og:title', content: 'Enterprise Agent Platform' }],
    ['meta', { property: 'og:description', content: 'Safe, observable, governable Multi-Agent Control Plane' }]
  ],
  themeConfig: {
    siteTitle: 'Enterprise Agent',
    nav: [
      { text: 'Guide', link: '/getting-started' },
      { text: 'Architecture', link: '/ARCHITECTURE' },
      { text: 'Interview', link: '/INTERVIEW' },
      { text: 'Live Demo', link: 'https://agent.majhoon.site' }
    ],
    sidebar: [
      {
        text: 'Overview',
        items: [
          { text: 'Introduction', link: '/' },
          { text: 'Getting Started', link: '/getting-started' },
          { text: 'Architecture', link: '/ARCHITECTURE' }
        ]
      },
      {
        text: 'Operate',
        items: [
          { text: 'Demo Guide', link: '/DEMO' }
        ]
      },
      {
        text: 'Interview',
        items: [
          { text: 'Interview Handbook', link: '/INTERVIEW' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/yvanu/enterprise-agent-platform' }
    ],
    search: {
      provider: 'local'
    },
    outline: {
      level: [2, 3],
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
    footer: {
      message: 'Enterprise Agent Platform · Architecture and interview documentation',
      copyright: 'Built from the project repository'
    }
  }
})
