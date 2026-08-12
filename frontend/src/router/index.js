// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'MapView',
    component: () => import('../views/MapView.vue')
  },
  // 可以继续添加其他路由
  {
    path: '/remote-sensing-analysis',
    name: 'RemoteSensingAnalysis',
    component: () => import('../views/RemoteSensingAnalysis.vue')
  },
  {
    path: '/feedback',
    name: 'CitizenFeedback',
    component: () => import('../views/CitizenFeedback.vue')
  },
  {
    path: '/ecological-index',
    name: 'EcologicalIndex',
    component: () => import('../views/EcologicalIndex.vue')
  },
  {
    path: '/climate-monitoring',
    name: 'ClimateMonitoring',
    component: () => import('../views/ClimateMonitoring.vue')
  },
  {
    path: '/overlay-analysis',
    name: 'OverlayAnalysis',
    component: () => import('../views/OverlayAnalysis.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
