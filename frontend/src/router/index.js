const DashboardPage = () => import('../pages/DashboardPage.vue')
const PortfoliosPage = () => import('../pages/PortfoliosPage.vue')
const PortfolioDetailPage = () => import('../pages/PortfolioDetailPage.vue')
const PendingTradesPage = () => import('../pages/PendingTradesPage.vue')
const ComparisonPage = () => import('../pages/ComparisonPage.vue')
const SystemHealthPage = () => import('../pages/SystemHealthPage.vue')

export default [
  { path: '/', name: 'dashboard', component: DashboardPage },
  { path: '/portfolios', name: 'portfolios', component: PortfoliosPage },
  { path: '/portfolios/:name', name: 'portfolio-detail', component: PortfolioDetailPage, props: true },
  { path: '/trades', name: 'pending-trades', component: PendingTradesPage },
  { path: '/comparison', name: 'comparison', component: ComparisonPage },
  { path: '/system', name: 'system-health', component: SystemHealthPage }
]
