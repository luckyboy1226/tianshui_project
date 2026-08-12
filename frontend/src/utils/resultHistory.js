const STORAGE_PREFIX = 'tianshui_result_history_v1'
const DEFAULT_LIMIT = 6

function getStorageKey(featureKey) {
  return `${STORAGE_PREFIX}:${featureKey}`
}

function safeParse(rawValue, fallback) {
  if (!rawValue) {
    return fallback
  }

  try {
    return JSON.parse(rawValue)
  } catch (error) {
    console.warn('解析历史结果失败:', error)
    return fallback
  }
}

function ensureArray(value) {
  return Array.isArray(value) ? value : []
}

export function loadResultHistory(featureKey) {
  if (typeof window === 'undefined') {
    return []
  }

  const items = safeParse(localStorage.getItem(getStorageKey(featureKey)), [])
  return ensureArray(items).sort((a, b) => Number(b.timestamp || 0) - Number(a.timestamp || 0))
}

export function saveResultHistory(featureKey, item, options = {}) {
  if (typeof window === 'undefined' || !item) {
    return []
  }

  const maxItems = Number(options.maxItems) > 0 ? Number(options.maxItems) : DEFAULT_LIMIT
  const nextItem = {
    id: item.id || `${featureKey}_${Date.now()}`,
    title: item.title || '未命名结果',
    subtitle: item.subtitle || '',
    timestamp: Number(item.timestamp || Date.now()),
    payload: item.payload || null
  }

  const history = loadResultHistory(featureKey).filter((entry) => entry.id !== nextItem.id)
  history.unshift(nextItem)

  const trimmed = history.slice(0, maxItems)
  localStorage.setItem(getStorageKey(featureKey), JSON.stringify(trimmed))
  return trimmed
}

export function removeResultHistory(featureKey, itemId) {
  if (typeof window === 'undefined') {
    return []
  }

  const nextItems = loadResultHistory(featureKey).filter((item) => item.id !== itemId)
  localStorage.setItem(getStorageKey(featureKey), JSON.stringify(nextItems))
  return nextItems
}

export function clearResultHistory(featureKey) {
  if (typeof window === 'undefined') {
    return
  }

  localStorage.removeItem(getStorageKey(featureKey))
}

export function formatHistoryTime(timestamp) {
  if (!timestamp) {
    return ''
  }

  try {
    return new Date(timestamp).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (error) {
    return ''
  }
}
