/**
 * API配置文件
 * 定义所有后端接口的URL和配置
 */

const DEFAULT_API_BASE_URL = '/api'

function normalizeBaseUrl(url) {
  return (url || DEFAULT_API_BASE_URL).replace(/\/+$/, '')
}

function normalizeEndpoint(endpoint) {
  return endpoint.startsWith('/') ? endpoint : `/${endpoint}`
}

// API基础配置
export const API_CONFIG = {
  // 基础URL
  // 开发环境默认走 Vite 代理；需要直连后端时可配置 VITE_API_BASE_URL
  BASE_URL: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL),
  
  // 版本
  VERSION: 'v1',
  
  // 大遥感栅格上传和计算耗时较长，开发演示环境给到30分钟
  TIMEOUT: 30 * 60 * 1000,
  
  // 请求头
  HEADERS: {
    'Content-Type': 'application/json',
  }
}

// API端点配置
export const API_ENDPOINTS = {
  // 用户认证
  AUTH: {
    CSRF: '/users/csrf/',
    LOGIN: '/users/login/',
    LOGOUT: '/users/logout/',
    REGISTER: '/users/register/',
    PROFILE: '/users/profile/',
    ME: '/users/me/',
    USERS: '/users/',
    USER_DETAIL: (id) => `/users/${id}/`,
    USER_PERMISSIONS: (id) => `/users/${id}/permissions/`,
    USER_ASSIGN_PERMISSIONS: (id) => `/users/${id}/assign_permissions/`,
    PERMISSION_SCHEMA: '/users/permission_schema/',
    REFRESH_TOKEN: '/users/token/refresh/',
  },
  
  // 遥感影像管理
  REMOTE_SENSING: {
    LIST: '/environment/remote-sensing-images/',
    UPLOAD: '/environment/remote-sensing-images/',
    ANALYZE_UPLOAD: '/environment/remote-sensing/analyze-upload/',
    DETAIL: (id) => `/environment/remote-sensing-images/${id}/`,
    DELETE: (id) => `/environment/remote-sensing-images/${id}/`,
    UPDATE: (id) => `/environment/remote-sensing-images/${id}/`,
    CALCULATE_INDICES: (id) => `/environment/remote-sensing-images/${id}/calculate_indices/`,
    GET_INDICES: (id) => `/environment/remote-sensing-images/${id}/indices/`,
  },
  
  // 生态指数计算
  ECOLOGICAL_INDICES: {
    LIST: '/environment/ecological-indices/',
    CREATE: '/environment/ecological-indices/',
    DETAIL: (id) => `/environment/ecological-indices/${id}/`,
    CALCULATE: '/environment/ecological-indices/calculate/',
    RSEI_CALCULATE: '/environment/rsei-results/calculate/',
    // 土地利用综合指数计算
    LANDUSE_INDICES: '/environment/ecological-landuse-indices/',
    // 新增：生态环境结构指数计算
    STRUCTURE_INDICES: '/environment/ecological-structure-indices/',
    // 新增：生态环境胁迫指数计算
    STRESS_INDICES: '/environment/ecological-stress-indices/',
  },
  
  // 处理任务
  PROCESSING_TASKS: {
    LIST: '/environment/processing-tasks/',
    CREATE: '/environment/processing-tasks/',
    DETAIL: (id) => `/environment/processing-tasks/${id}/`,
    STATUS: (id) => `/environment/processing-tasks/${id}/status/`,
  },
  
  // 地理空间服务
  SPATIAL: {
    WMS_CAPABILITIES: '/environment/spatial/wms/capabilities/',
    WMS_MAP: '/environment/spatial/wms/map/',
    WFS_CAPABILITIES: '/environment/spatial/wfs/capabilities/',
    SPATIAL_LAYERS: '/environment/spatial/layers/',
    HIGHRES_IMAGERY_LIST: '/environment/spatial/highres-imagery/',
    HIGHRES_IMAGERY_PUBLISH: '/environment/spatial/highres-imagery/publish/',
    BUSINESS_LAYERS: '/environment/business-layers/',
    BUSINESS_LAYER_DETAIL: (id) => `/environment/business-layers/${id}/`,
    BUSINESS_LAYER_PUBLISH: (id) => `/environment/business-layers/${id}/publish/`,
    BUSINESS_LAYER_UNPUBLISH: (id) => `/environment/business-layers/${id}/unpublish/`,
    BUSINESS_LAYER_STYLE: (id) => `/environment/business-layers/${id}/style/`,
    BUSINESS_LAYER_LOGS: (id) => `/environment/business-layers/${id}/logs/`,
    PUBLISH_TO_GEOSERVER: '/environment/spatial/publish/',
    GEOSERVER_STATUS: '/environment/spatial/geoserver/status/',
  },

  // 民众意见反馈
  FEEDBACK: {
    CREATE: '/environment/feedback/',
    LIST: '/environment/feedback/',
    DETAIL: (id) => `/environment/feedback/${id}/`,
    DELETE: (id) => `/environment/feedback/${id}/`,
    CLEAR: '/environment/feedback/clear/'
  },
  
  // 气候监测统计
  CLIMATE_MONITORING: {
    UPLOAD: '/environment/climate-monitoring/upload/',
    ANALYZE: '/environment/climate-monitoring/analyze/',
    RESULTS: (taskId) => `/environment/climate-monitoring/results/${taskId}/`,
    STATUS: (taskId) => `/environment/processing-tasks/${taskId}/status/`,
    DOWNLOAD_REPORT: (taskId) => `/environment/climate-monitoring/report/${taskId}/download/`
  },

  // 重大工程叠加分析
  OVERLAY_ANALYSIS: {
    TASKS: '/environment/overlay-analysis-tasks/',
    UPLOAD_ECOLOGY_RASTER: '/environment/overlay-analysis-tasks/upload-ecology-raster/',
    UPLOAD_ECONOMY_VECTOR: '/environment/overlay-analysis-tasks/upload-economy-vector/',
    UPLOAD_ENGINEERING_VECTOR: '/environment/overlay-analysis-tasks/upload-engineering-vector/',
    SYNC_LATEST_RSEI: '/environment/overlay-analysis-tasks/sync-latest-rsei/',
    AVAILABLE_RSEI_SOURCES: '/environment/overlay-analysis-tasks/available-rsei-sources/',
    CLEAR_RSEI_CACHE: '/environment/overlay-analysis-tasks/clear-rsei-cache/',
    DELETE_UPLOADED_LAYER: '/environment/overlay-analysis-tasks/delete-uploaded-layer/',
    UPLOADED_LAYER_METADATA: '/environment/overlay-analysis-tasks/uploaded-layer-metadata/'
  }
}

// 构建完整的API URL
export function buildApiUrl(endpoint) {
  return `${API_CONFIG.BASE_URL}/${API_CONFIG.VERSION}${normalizeEndpoint(endpoint)}`
}

// 获取所有API URL
export function getAllApiUrls() {
  const urls = {}
  
  // 遍历所有端点，构建完整URL
  Object.keys(API_ENDPOINTS).forEach(category => {
    urls[category] = {}
    Object.keys(API_ENDPOINTS[category]).forEach(key => {
      const endpoint = API_ENDPOINTS[category][key]
      if (typeof endpoint === 'function') {
        urls[category][key] = endpoint
      } else {
        urls[category][key] = buildApiUrl(endpoint)
      }
    })
  })
  
  return urls
}

export default {
  API_CONFIG,
  API_ENDPOINTS,
  buildApiUrl,
  getAllApiUrls
} 
