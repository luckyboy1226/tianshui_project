<template>
  <div id="overlay-map-container">
    <!-- 地图主体 -->
    <div id="overlay-map"></div>

    <!-- 缩放控制 -->
    <div class="zoom-controls">
      <button class="zoom-btn" @click="zoomIn" title="放大">+</button>
      <button class="zoom-btn" @click="zoomOut" title="缩小">-</button>
    </div>

    <!-- 坐标显示 -->
    <div class="coordinate-display">
      <div>经度: {{ coordinates.lng }}</div>
      <div>纬度: {{ coordinates.lat }}</div>
    </div>

    <!-- 叠加分析信息弹窗 -->
    <OverlayAnalysisPopup
      :visible="popup.visible"
      :coordinate="popup.coordinate"
      :ecology-data="popup.ecologyData"
      :economy-data="popup.economyData"
      :engineering-data="popup.engineeringData"
      @close="closePopup"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import 'ol/ol.css'
import { Map as OLMap } from 'ol'
import View from 'ol/View'
import { defaults as defaultControls } from 'ol/control'
import TileLayer from 'ol/layer/Tile'
import XYZ from 'ol/source/XYZ'
import TileWMS from 'ol/source/TileWMS'
// 不再需要坐标转换，直接使用 EPSG:4326
import { MapUtils } from '../../utils/mapUtils'
import {
  ensurePreferredHighResImageryRecord,
  getHighResImageryQualifiedLayerName
} from '../../utils/highResImagery.js'
import { API_CONFIG } from '../../config/api.js'
import { API_ENDPOINTS, buildApiUrl } from '../../config/api.js'
import request from '../../utils/http.js'
import OverlayAnalysisPopup from './OverlayAnalysisPopup.vue'

// Props
const props = defineProps({
  layerVisibility: {
    type: Object,
    default: () => ({
      ecology: true,
      economy: true,
      engineering: true,
      referenceImagery: false
    })
  },
  layerOpacity: {
    type: Object,
    default: () => ({
      referenceImagery: 100,
      ecology: 88,
      economy: 60,
      engineering: 80
    })
  },
  activeEcologyLayerKey: {
    type: String,
    default: 'ecology_synced'
  }
})

// 地图配置
const TDT_TOKEN = '69874af7f35c741d7132c50f80acad29'
const GEOSERVER_WORKSPACE = 'tianshuipy'
const GEOSERVER_OWS_PROXY = `${API_CONFIG.BASE_URL}/${API_CONFIG.VERSION}/environment/geoserver/ows/`
const TIANSHUI_CENTER = [105.7, 34.6] // 天水市中心坐标

// 地图实例
let map = null
let referenceImageryLayer = null
let ecologyRasterLayer = null
let ecologyDisplayLayer = null
let economyVectorLayer = null
let engineeringVectorLayer = null
let ecologyLayerMetadata = {}

const hasFeatureProperties = (item) => {
  if (!item) return false
  if (Array.isArray(item)) return item.length > 0
  if (typeof item === 'object') return Object.keys(item).length > 0
  return false
}

// 坐标显示
const coordinates = reactive({ lng: '105.7000', lat: '34.6000' })

// 弹窗数据
const popup = reactive({
  visible: false,
  coordinate: { lng: 0, lat: 0 },
  ecologyData: null,
  economyData: null,
  engineeringData: []
})

const ECOLOGY_LEVEL_CONFIG = [
  { code: 'excellent', label: '优秀', shortLabel: '优', riskCode: 'low-risk' },
  { code: 'good', label: '良好', shortLabel: '良', riskCode: 'low-risk' },
  { code: 'moderate', label: '中等', shortLabel: '中', riskCode: 'medium-risk' },
  { code: 'poor', label: '较差', shortLabel: '低', riskCode: 'medium-risk' },
  { code: 'bad', label: '差', shortLabel: '差', riskCode: 'high-risk' }
]

const ECOLOGY_CLASS_CODE_MAP = {
  0: ECOLOGY_LEVEL_CONFIG[4],
  1: ECOLOGY_LEVEL_CONFIG[4],
  2: ECOLOGY_LEVEL_CONFIG[3],
  3: ECOLOGY_LEVEL_CONFIG[2],
  4: ECOLOGY_LEVEL_CONFIG[1],
  5: ECOLOGY_LEVEL_CONFIG[0]
}

const ECOLOGY_GENERIC_CLASS_COLORS = {
  1: '#8b1e3f',
  2: '#c0392b',
  3: '#f08c7f',
  4: '#f1c453',
  5: '#9ccf72',
  6: '#2f8f5b'
}

const parseFiniteNumber = (value) => {
  if (value === null || value === undefined || value === '') {
    return null
  }

  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) ? parsed : null
}

const getEcologyClassification = (rawValue, sourceField = '') => {
  if (!Number.isFinite(rawValue)) {
    return null
  }

  const normalizedField = String(sourceField || '').toUpperCase()
  const isIntegerLike = Math.abs(rawValue - Math.round(rawValue)) < 1e-6

  if (isIntegerLike) {
    const roundedValue = Math.round(rawValue)
    const classInfo = ECOLOGY_CLASS_CODE_MAP[roundedValue]
    const looksLikeGradeField =
      normalizedField.includes('GRAY_INDEX') ||
      normalizedField.includes('CLASS') ||
      normalizedField.includes('GRADE') ||
      normalizedField.includes('LEVEL')

    if (classInfo && looksLikeGradeField) {
      return {
        ...classInfo,
        rawValue,
        displayValue: roundedValue,
        displayValueText: String(roundedValue),
        sourceMode: 'classified',
        normalizedValue: null,
        isHighRisk: classInfo.code === 'bad'
      }
    }

    if (roundedValue >= 1 && roundedValue <= 6) {
      return {
        code: `class_${roundedValue}`,
        label: `${roundedValue}级`,
        shortLabel: String(roundedValue),
        riskCode: 'unknown',
        rawValue,
        displayValue: roundedValue,
        displayValueText: String(roundedValue),
        sourceMode: 'classified_generic',
        normalizedValue: null,
        isHighRisk: false,
        color: ECOLOGY_GENERIC_CLASS_COLORS[roundedValue] || '#666666'
      }
    }
  }

  let normalizedValue = rawValue
  if (rawValue > 1 && rawValue <= 100) {
    normalizedValue = rawValue / 100
  }

  let classInfo = ECOLOGY_LEVEL_CONFIG[4]
  if (normalizedValue >= 0.8) classInfo = ECOLOGY_LEVEL_CONFIG[0]
  else if (normalizedValue >= 0.6) classInfo = ECOLOGY_LEVEL_CONFIG[1]
  else if (normalizedValue >= 0.4) classInfo = ECOLOGY_LEVEL_CONFIG[2]
  else if (normalizedValue >= 0.2) classInfo = ECOLOGY_LEVEL_CONFIG[3]

  return {
    ...classInfo,
    rawValue,
    displayValue: normalizedValue,
    displayValueText: normalizedValue.toFixed(3),
    sourceMode: 'continuous',
    normalizedValue,
    isHighRisk: classInfo.code === 'bad'
  }
}

// 监听图层可见性变化
watch(() => props.layerVisibility, (newVal) => {
  syncReferenceImageryVisibility(newVal.referenceImagery)
  syncEcologyLayerVisibility(newVal.ecology)
  if (economyVectorLayer) {
    economyVectorLayer.setVisible(newVal.economy)
  }
  if (engineeringVectorLayer) {
    engineeringVectorLayer.setVisible(newVal.engineering)
  }
}, { deep: true })

watch(() => props.layerOpacity, (newVal) => {
  applyLayerOpacity(newVal)
}, { deep: true })

watch(() => props.activeEcologyLayerKey, () => {
  refreshEcologyDisplayLayer()
})

// 创建高德底图（稳定可靠）
const createBaseMap = () => {
  return new TileLayer({
    source: new XYZ({
      url: 'https://webrd0{1-4}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
          crossOrigin: 'anonymous'
    }),
    visible: true,
    zIndex: 0
  })
}

const buildEcologyWMSLayer = (layerName) => {
  const wmsBaseUrl = GEOSERVER_OWS_PROXY
  const wmsCommonParams = {
    'VERSION': '1.1.0',
    'TILED': true,
    'TRANSPARENT': true,
    'FORMAT': 'image/png',
    'SRS': 'EPSG:4326'
  }

  return new TileLayer({
    source: new TileWMS({
      url: wmsBaseUrl,
      params: {
        ...wmsCommonParams,
        'LAYERS': `${GEOSERVER_WORKSPACE}:${layerName}`
      },
      serverType: 'geoserver',
      crossOrigin: 'anonymous'
    }),
    visible: props.layerVisibility.ecology,
    opacity: Number(props.layerOpacity?.ecology ?? 88) / 100,
    zIndex: 2
  })
}

// 创建WMS图层
const createWMSLayers = () => {
  const wmsBaseUrl = GEOSERVER_OWS_PROXY
  
  // WMS 通用参数（使用 1.1.0 版本，更兼容）
  const wmsCommonParams = {
    'VERSION': '1.1.0',
    'TILED': true,
    'TRANSPARENT': true,
    'FORMAT': 'image/png',
    'SRS': 'EPSG:4326'  // 使用 SRS 对应 WMS 1.1.0，与 View 投影一致
  }
  
  // 1. 经济矢量图层
  economyVectorLayer = new TileLayer({
    source: new TileWMS({
    url: wmsBaseUrl,
    params: {
        ...wmsCommonParams,
        'LAYERS': `${GEOSERVER_WORKSPACE}:economy_vector`
    },
    serverType: 'geoserver',
    crossOrigin: 'anonymous'
    }),
    visible: props.layerVisibility.economy,
    opacity: Number(props.layerOpacity?.economy ?? 60) / 100,
    zIndex: 3
  })
  
  // 2. 工程矢量图层
  engineeringVectorLayer = new TileLayer({
    source: new TileWMS({
    url: wmsBaseUrl,
    params: {
        ...wmsCommonParams,
        'LAYERS': `${GEOSERVER_WORKSPACE}:engineering_vector`
    },
    serverType: 'geoserver',
    crossOrigin: 'anonymous'
    }),
    visible: props.layerVisibility.engineering,
    opacity: Number(props.layerOpacity?.engineering ?? 80) / 100,
    zIndex: 4
  })
  
  return [economyVectorLayer, engineeringVectorLayer]
}

const applyLayerOpacity = (opacityConfig = {}) => {
  if (referenceImageryLayer) {
    referenceImageryLayer.setOpacity(Number(opacityConfig.referenceImagery ?? 100) / 100)
  }
  if (ecologyDisplayLayer) {
    ecologyDisplayLayer.setOpacity(Number(opacityConfig.ecology ?? 88) / 100)
  }
  if (ecologyRasterLayer) {
    ecologyRasterLayer.setOpacity(ecologyDisplayLayer ? 0 : Number(opacityConfig.ecology ?? 88) / 100)
  }
  if (economyVectorLayer) {
    economyVectorLayer.setOpacity(Number(opacityConfig.economy ?? 60) / 100)
  }
  if (engineeringVectorLayer) {
    engineeringVectorLayer.setOpacity(Number(opacityConfig.engineering ?? 80) / 100)
  }
  map?.render()
}

const ensureReferenceImageryLayer = async () => {
  if (!map) return
  if (referenceImageryLayer) {
    referenceImageryLayer.setVisible(true)
    return
  }

  const imageryRecord = await ensurePreferredHighResImageryRecord()
  const layerName = getHighResImageryQualifiedLayerName(imageryRecord)
  referenceImageryLayer = imageryRecord.source_kind === 'business_layer'
    ? MapUtils.loadWMS(GEOSERVER_OWS_PROXY, layerName, {
      visible: true,
      opacity: Number(props.layerOpacity?.referenceImagery ?? 100) / 100,
      serverType: 'geoserver',
      metadata: imageryRecord.metadata,
      targetProjection: 'EPSG:4326'
    })
    : MapUtils.loadStaticWMSImage(GEOSERVER_OWS_PROXY, layerName, {
      visible: true,
      opacity: Number(props.layerOpacity?.referenceImagery ?? 100) / 100,
      serverType: 'geoserver',
      metadata: imageryRecord.metadata,
      imageUrl: imageryRecord.preview_image_url || undefined,
      targetProjection: 'EPSG:4326'
    })
  referenceImageryLayer.setZIndex(1)
  map.addLayer(referenceImageryLayer)
}

const syncReferenceImageryVisibility = async (visible) => {
  if (!map) return
  if (!visible) {
    if (referenceImageryLayer) {
      referenceImageryLayer.setVisible(false)
    }
    return
  }

  try {
    await ensureReferenceImageryLayer()
  } catch (error) {
    console.error('加载叠加分析遥感影像底图失败:', error)
  }
}

const syncEcologyLayerVisibility = (visible) => {
  if (ecologyDisplayLayer) {
    ecologyDisplayLayer.setVisible(visible)
  }
  if (ecologyRasterLayer) {
    ecologyRasterLayer.setVisible(!ecologyDisplayLayer && visible)
  }
}

const loadOverlayLayerMetadata = async () => {
  try {
    const endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.UPLOADED_LAYER_METADATA)
    const response = await request.get(endpoint, {}, { skipAuth: true, silentError: true })
    ecologyLayerMetadata = response?.data || {}
  } catch (error) {
    console.warn('加载叠加图层元数据失败:', error)
    ecologyLayerMetadata = {}
  }
}

const getActiveEcologyMetadata = () => {
  const preferredKey = props.activeEcologyLayerKey || 'ecology_synced'
  const preferred = ecologyLayerMetadata?.[preferredKey]
  if (preferred?.published) {
    return preferred
  }

  const fallbackKeys = ['ecology_synced', 'ecology_uploaded']
  for (const key of fallbackKeys) {
    const item = ecologyLayerMetadata?.[key]
    if (item?.published) {
      return item
    }
  }

  return null
}

const refreshEcologyDisplayLayer = async () => {
  await loadOverlayLayerMetadata()
  const metadata = getActiveEcologyMetadata()
  const overlayImageUrl = metadata?.overlay_image_url
    ? `${metadata.overlay_image_url}${metadata.overlay_image_url.includes('?') ? '&' : '?'}v=${encodeURIComponent(metadata.updated_at || Date.now())}`
    : null
  const useStaticVisualization = Boolean(
    metadata?.published &&
    (overlayImageUrl || metadata?.visualization_file_url) &&
    ['latest_rsei', 'selected_rsei', 'uploaded_raster'].includes(metadata?.source_type)
  )

  if (!map) return

  if (ecologyRasterLayer) {
    map.removeLayer(ecologyRasterLayer)
    ecologyRasterLayer = null
  }

  if (metadata?.published && metadata?.layer_name) {
    ecologyRasterLayer = buildEcologyWMSLayer(metadata.layer_name)
    map.addLayer(ecologyRasterLayer)
  }

  if (!metadata?.published) {
    if (ecologyDisplayLayer) {
      map.removeLayer(ecologyDisplayLayer)
      ecologyDisplayLayer = null
    }
    return
  }

  if (useStaticVisualization) {
    if (ecologyDisplayLayer) {
      map.removeLayer(ecologyDisplayLayer)
      ecologyDisplayLayer = null
    }
    ecologyDisplayLayer = MapUtils.loadStaticWMSImage(GEOSERVER_OWS_PROXY, `${GEOSERVER_WORKSPACE}:${metadata.layer_name}`, {
      visible: props.layerVisibility.ecology,
      opacity: Number(props.layerOpacity?.ecology ?? 88) / 100,
      serverType: 'geoserver',
      metadata,
      imageUrl: overlayImageUrl || metadata.visualization_file_url,
      targetProjection: 'EPSG:4326'
    })
    ecologyDisplayLayer.setZIndex(2)
    map.addLayer(ecologyDisplayLayer)
    if (ecologyRasterLayer) {
      ecologyRasterLayer.setOpacity(0)
      ecologyRasterLayer.setVisible(false)
    }
    return
  }

  if (ecologyDisplayLayer) {
    map.removeLayer(ecologyDisplayLayer)
    ecologyDisplayLayer = null
  }
  if (ecologyRasterLayer) {
    ecologyRasterLayer.setOpacity(Number(props.layerOpacity?.ecology ?? 88) / 100)
    ecologyRasterLayer.setVisible(props.layerVisibility.ecology)
  }
}

// 初始化地图
const initMap = () => {
  try {
    console.log('🗺️ 初始化重大工程叠加分析地图...')
    
    const mapElement = document.getElementById('overlay-map')
    if (!mapElement) {
      console.error('❌ 地图容器未找到')
      return
    }
    
    console.log('📦 地图容器尺寸:', {
      width: mapElement.offsetWidth,
      height: mapElement.offsetHeight
    })
    
    // 创建高德底图
    const gaodeLayer = createBaseMap()
    
    // 创建三个WMS图层
    const wmsLayers = createWMSLayers()
    
    // 创建地图（直接使用经纬度坐标，不需要转换）
    map = new OLMap({
      target: 'overlay-map',
      layers: [gaodeLayer, ...wmsLayers],
      view: new View({
        projection: 'EPSG:4326',  // ✅ 关键：使用 EPSG:4326 投影
        center: [105.7, 34.6],     // ✅ 直接使用经纬度坐标
        zoom: 10
      }),
      controls: defaultControls({ zoom: false })
    })
    
    console.log('✅ 地图对象创建完成')
    console.log('📍 地图中心点:', map.getView().getCenter())
    console.log('📦 已加载图层数:', map.getLayers().getLength())
    console.log('🔍 地图尺寸:', map.getSize())
    
    // 设置地图点击事件
    map.on('click', handleMapClick)
    
    // 设置鼠标移动事件（更新坐标显示）
    map.on('pointermove', (event) => {
      // 坐标已经是 EPSG:4326 (经纬度)，无需转换
      const coord = event.coordinate
      if (coord && !isNaN(coord[0]) && !isNaN(coord[1])) {
        coordinates.lng = coord[0].toFixed(4)
        coordinates.lat = coord[1].toFixed(4)
      }
    })
    
    // 强制刷新地图
    setTimeout(() => {
      if (map) {
        map.updateSize()
        const newSize = map.getSize()
        console.log('🔄 地图尺寸更新:', newSize)
      map.render()
        console.log('✅ 地图渲染完成')
    }
  }, 200)

    syncReferenceImageryVisibility(props.layerVisibility.referenceImagery)
    applyLayerOpacity(props.layerOpacity)
    refreshEcologyDisplayLayer()
  
    // 再次刷新（确保底图显示）
  setTimeout(() => {
      if (map) {
    map.updateSize()
    map.render()
        console.log('🔄 地图二次刷新完成')
      }
  }, 500)
  
    } catch (error) {
    console.error('❌ 地图初始化失败:', error)
    console.error('错误堆栈:', error.stack)
  }
}

// 处理地图点击事件
const handleMapClick = async (event) => {
  try {
    console.log('🖱️ 地图点击事件触发')
    
    // 坐标已经是 EPSG:4326 (经纬度)，无需转换
    const coord = event.coordinate
    
    console.log('📍 点击坐标 (经纬度):', coord)
    
    // 重置弹窗数据
    popup.visible = false
    popup.coordinate = { lng: coord[0], lat: coord[1] }
    popup.ecologyData = null
    popup.economyData = null
    popup.engineeringData = []
        
        // 准备图层源映射
    const layerSources = {
      ecology: ecologyRasterLayer?.getSource(),
      economy: economyVectorLayer?.getSource(),
      engineering: engineeringVectorLayer?.getSource()
    }
    
    console.log('🔍 开始获取图层信息...')
        
        // 批量获取GetFeatureInfo
        const results = await MapUtils.getMultipleFeatureInfo(layerSources, coord, map)
    
    console.log('📊 GetFeatureInfo结果:', results)
        
        // 解析生态栅格数据
        if (results.ecology) {
      popup.ecologyData = parseEcologyData(results.ecology)
      console.log('🌿 生态数据:', popup.ecologyData)
        }
        
        // 解析经济矢量数据
        if (results.economy) {
      popup.economyData = parseEconomyData(results.economy)
      console.log('💰 经济数据:', popup.economyData)
        }
        
        // 解析工程矢量数据
        if (results.engineering) {
      popup.engineeringData = parseEngineeringData(results.engineering)
      console.log('🏗️ 工程数据:', popup.engineeringData)
        }
        
    const shouldOpenPopup =
      hasFeatureProperties(popup.ecologyData) ||
      hasFeatureProperties(popup.economyData) ||
      hasFeatureProperties(popup.engineeringData)

    if (!shouldOpenPopup) {
      console.log('ℹ️ 当前点击位置未命中任何业务图层')
      return
    }

    popup.visible = true
    console.log('✅ 弹窗已打开')
        
      } catch (error) {
    console.error('❌ 处理地图点击失败:', error)
  }
}

// 解析生态栅格数据
const parseEcologyData = (data) => {
  try {
    if (!data.features || data.features.length === 0) {
      return null
    }
    
      const feature = data.features[0]
      const properties = feature.properties || {}
      
    // 查找栅格值（优先识别RSEI结果或已分级后的编码值）
    let value = null
    let sourceField = null
    const possibleFields = ['RSEI', 'rsei', 'RESI', 'resi', 'GRAY_INDEX', 'Band1', 'value', 'pixel_value']
    
    for (const field of possibleFields) {
      const parsedValue = parseFiniteNumber(properties[field])
      if (parsedValue !== null) {
        value = parsedValue
        sourceField = field
        break
      }
    }
    
    if (value === null) {
      return null
    }

    const classification = getEcologyClassification(value, sourceField)
    if (!classification) {
      return null
    }

    return {
      value,
      sourceField,
      level: classification.label,
      levelCode: classification.code,
      shortLevel: classification.shortLabel,
      riskCode: classification.riskCode,
      isHighRisk: classification.isHighRisk,
      sourceMode: classification.sourceMode,
      normalizedValue: classification.normalizedValue,
      displayValue: classification.displayValue,
      displayValueText: classification.displayValueText,
      valueLabel: classification.sourceMode === 'classified' ? '分级编码' : 'RSEI值',
      rawProperties: properties
    }
  } catch (error) {
    console.error('解析生态数据失败:', error)
    return null
  }
}

// 解析经济矢量数据
const parseEconomyData = (data) => {
  try {
    if (!data.features || data.features.length === 0) {
      return null
    }
    
    const feature = data.features[0]
    const properties = feature.properties || {}
    
    // 调试：打印所有属性
    console.log('💰 经济数据原始属性:', properties)
    console.log('💰 所有属性键:', Object.keys(properties))

    const normalizeFieldName = (fieldName) => String(fieldName || '')
      .replace(/[\s_\-（）()\[\]{}【】.:：/\\]+/g, '')
      .toLowerCase()

    const fieldEntries = Object.keys(properties).map((key) => ({
      key,
      normalized: normalizeFieldName(key)
    }))

    const extractYear = (fieldName) => {
      const matches = String(fieldName || '').match(/(?:19|20)\d{2}/g)
      if (!matches || !matches.length) return null
      return Number.parseInt(matches[matches.length - 1], 10)
    }

    const parseNumberValue = (...keys) => {
      for (const key of keys) {
        const value = properties[key]
        if (value !== null && value !== undefined && value !== '') {
          const parsed = Number.parseFloat(value)
          if (!Number.isNaN(parsed)) {
            return parsed
          }
        }
      }
      return null
    }

    const findNumericFieldValue = (aliases = [], keywords = [], options = {}) => {
      const { preferredYear = null, excludedKeywords = [] } = options
      const normalizedAliases = aliases.map((item) => normalizeFieldName(item))
      const normalizedKeywords = keywords.map((item) => normalizeFieldName(item))
      const normalizedExcluded = excludedKeywords.map((item) => normalizeFieldName(item))
      let bestMatch = null

      for (const entry of fieldEntries) {
        const value = properties[entry.key]
        if (value === null || value === undefined || value === '') continue
        const parsed = Number.parseFloat(value)
        if (Number.isNaN(parsed)) continue
        if (normalizedExcluded.some((keyword) => keyword && entry.normalized.includes(keyword))) continue

        let score = 0
        if (normalizedAliases.includes(entry.normalized)) {
          score += 120
        }
        normalizedAliases.forEach((alias) => {
          if (alias && entry.normalized.includes(alias)) {
            score += 80
          }
        })
        normalizedKeywords.forEach((keyword) => {
          if (keyword && entry.normalized.includes(keyword)) {
            score += 35
          }
        })

        const year = extractYear(entry.key)
        if (preferredYear && year === preferredYear) {
          score += 60
        } else if (preferredYear && year) {
          score -= Math.abs(preferredYear - year)
        } else if (year) {
          score += Math.max(0, year - 2000)
        }

        if (score <= 0) continue
        if (!bestMatch || score > bestMatch.score) {
          bestMatch = { key: entry.key, value: parsed, score }
        }
      }

      return bestMatch
    }
    
    // 辅助函数：安全获取字符串值（处理空字符串、null、undefined、占位符）
    const getStringValue = (...keys) => {
      // 无效值列表（包括常见的占位符）
      const invalidValues = ['', 'null', 'undefined', 'N/A', 'NA', '-', 'none', 'None', 'NONE']
      
      for (const key of keys) {
        const value = properties[key]
        if (value !== null && value !== undefined) {
          const strValue = String(value).trim()
          // 检查是否为有效值
          if (strValue !== '') {
            // 检查是否只包含问号（任意数量）
            if (/^\?+$/.test(strValue)) {
              continue // 跳过，尝试下一个字段
            }
            // 检查是否在无效值列表中
            if (!invalidValues.includes(strValue)) {
              return strValue
            }
          }
        }
      }
      return null // 返回null，让前端组件处理
    }

    const findStringFieldValue = (aliases = [], keywords = []) => {
      const normalizedAliases = aliases.map((item) => normalizeFieldName(item))
      const normalizedKeywords = keywords.map((item) => normalizeFieldName(item))
      let bestMatch = null

      for (const entry of fieldEntries) {
        const rawValue = properties[entry.key]
        if (rawValue === null || rawValue === undefined) continue
        const value = String(rawValue).trim()
        if (!value || /^\?+$/.test(value)) continue
        if (['null', 'undefined', 'N/A', 'NA', '-', 'none', 'None', 'NONE'].includes(value)) continue

        let score = 0
        if (normalizedAliases.includes(entry.normalized)) {
          score += 120
        }
        normalizedAliases.forEach((alias) => {
          if (alias && entry.normalized.includes(alias)) {
            score += 80
          }
        })
        normalizedKeywords.forEach((keyword) => {
          if (keyword && entry.normalized.includes(keyword)) {
            score += 35
          }
        })
        if (score <= 0) continue
        if (!bestMatch || score > bestMatch.score) {
          bestMatch = { value, score }
        }
      }

      return bestMatch?.value || null
    }

    const pop2015 = parseNumberValue('2015_POP', 'POP_2015', 'pop_2015')
    const pop2020 = parseNumberValue('2020_POP', 'POP_2020', 'pop_2020')
    const pop2023 = parseNumberValue('2023_POP', 'POP_2023', 'pop_2023')
    const gdp2015 = parseNumberValue('2015_GDP', 'GDP_2015', 'gdp_2015')
    const gdp2020 = parseNumberValue('2020_GDP', 'GDP_2020', 'gdp_2020')
    const gdp2023 = parseNumberValue('2023_GDP', 'GDP_2023', 'gdp_2023')

    const gdpField2023 = findNumericFieldValue(
      ['2023_GDP', 'GDP_2023'],
      ['gdp', '生产总值', '地区生产总值', '经济总量', '总产值', '产值'],
      { preferredYear: 2023, excludedKeywords: ['pop', '人口', 'area', '面积'] }
    )
    const gdpField2020 = findNumericFieldValue(
      ['2020_GDP', 'GDP_2020'],
      ['gdp', '生产总值', '地区生产总值', '经济总量', '总产值', '产值'],
      { preferredYear: 2020, excludedKeywords: ['pop', '人口', 'area', '面积'] }
    )
    const gdpField2015 = findNumericFieldValue(
      ['2015_GDP', 'GDP_2015'],
      ['gdp', '生产总值', '地区生产总值', '经济总量', '总产值', '产值'],
      { preferredYear: 2015, excludedKeywords: ['pop', '人口', 'area', '面积'] }
    )
    const popField2023 = findNumericFieldValue(
      ['2023_POP', 'POP_2023'],
      ['pop', 'population', '人口', '常住人口'],
      { preferredYear: 2023, excludedKeywords: ['gdp', '产值', '收入', 'area', '面积'] }
    )
    const popField2020 = findNumericFieldValue(
      ['2020_POP', 'POP_2020'],
      ['pop', 'population', '人口', '常住人口'],
      { preferredYear: 2020, excludedKeywords: ['gdp', '产值', '收入', 'area', '面积'] }
    )
    const popField2015 = findNumericFieldValue(
      ['2015_POP', 'POP_2015'],
      ['pop', 'population', '人口', '常住人口'],
      { preferredYear: 2015, excludedKeywords: ['gdp', '产值', '收入', 'area', '面积'] }
    )

    const latestGDP = gdp2023 ?? gdpField2023?.value ?? gdp2020 ?? gdpField2020?.value ?? gdp2015 ?? gdpField2015?.value ?? parseNumberValue('GDP', 'gdp', 'Gdp')
    const latestPOP = pop2023 ?? popField2023?.value ?? pop2020 ?? popField2020?.value ?? pop2015 ?? popField2015?.value ?? parseNumberValue('POP', 'pop', 'Pop')
    const areaValue = parseNumberValue('area_km2', 'AREA_KM2', 'area__k2', 'AREA__K2', 'area', 'AREA')
      ?? findNumericFieldValue(
        ['area_km2', 'AREA_KM2'],
        ['area', '面积', 'km2', '平方公里'],
        { excludedKeywords: ['gdp', 'pop', '人口', '产值'] }
      )?.value
    
    return {
      admin_name: getStringValue('admin_name', 'ADMIN_NAME', 'name', 'NAME', 'Name', 'region_name', 'REGION_NAME')
        ?? findStringFieldValue(['admin_name', 'name', 'region_name'], ['名称', '行政区', '区域', '乡镇', '街道']),
      layer_name: getStringValue('layer', 'LAYER')
        ?? findStringFieldValue(['layer'], ['图层', '类型']),
      code: getStringValue('code', 'CODE')
        ?? findStringFieldValue(['code'], ['编码', '代码', '区划']),
      grade: getStringValue('grade', 'GRADE')
        ?? findStringFieldValue(['grade'], ['等级']),
      GDP: latestGDP,
      POP: latestPOP,
      GDP_2015: gdp2015 ?? gdpField2015?.value ?? null,
      GDP_2020: gdp2020 ?? gdpField2020?.value ?? null,
      GDP_2023: gdp2023 ?? gdpField2023?.value ?? null,
      POP_2015: pop2015 ?? popField2015?.value ?? null,
      POP_2020: pop2020 ?? popField2020?.value ?? null,
      POP_2023: pop2023 ?? popField2023?.value ?? null,
      area_km2: areaValue,
      rawProperties: properties
    }
  } catch (error) {
    console.error('解析经济数据失败:', error)
    return null
  }
}

// 解析工程矢量数据
const parseEngineeringData = (data) => {
  try {
    if (!data.features || data.features.length === 0) {
      return []
    }
    
    // 辅助函数：安全获取字符串值（处理空字符串、null、undefined、占位符）
    const getStringValue = (properties, ...keys) => {
      // 无效值列表（包括常见的占位符）
      const invalidValues = ['', 'null', 'undefined', 'N/A', 'NA', '-', 'none', 'None', 'NONE']
      
      for (const key of keys) {
        const value = properties[key]
        if (value !== null && value !== undefined) {
          const strValue = String(value).trim()
          // 检查是否为有效值
          if (strValue !== '') {
            // 检查是否只包含问号（任意数量）
            if (/^\?+$/.test(strValue)) {
              continue // 跳过，尝试下一个字段
            }
            // 检查是否在无效值列表中
            if (!invalidValues.includes(strValue)) {
              return strValue
            }
          }
        }
      }
      return null // 返回null，让前端组件处理
    }

    const parseNumberValue = (properties, ...keys) => {
      for (const key of keys) {
        const value = properties[key]
        if (value !== null && value !== undefined && value !== '') {
          const parsed = Number.parseFloat(value)
          if (!Number.isNaN(parsed)) {
            return parsed
          }
        }
      }
      return null
    }
    
    return data.features.map((feature, index) => {
      const properties = feature.properties || {}
      
      // 调试：打印第一个要素的属性
      if (index === 0) {
        console.log('🏗️ 工程数据原始属性:', properties)
        console.log('🏗️ 所有属性键:', Object.keys(properties))
      }
      
      return {
        proj_name: getStringValue(
          properties,
          'proj_name', 'PROJ_NAME',
          'project_name', 'PROJECT_NAME',
          'name', 'NAME',
          '地名'
        ),
        proj_segment: getStringValue(
          properties,
          'proj_segment', 'PROJ_SEGMENT',
          'project_segment', 'PROJECT_SEGMENT',
          'segment', 'SEGMENT',
          '项目段'
        ),
        proj_type: getStringValue(
          properties,
          'proj_type', 'PROJ_TYPE',
          'project_type', 'PROJECT_TYPE',
          'type', 'TYPE',
          'category', 'CATEGORY',
          '项目类'
        ),
        status: getStringValue(properties, 'status', 'STATUS', 'state', 'STATE'),
        start_date: getStringValue(properties, 'start_date', 'START_DATE', 'start_time', 'START_TIME', 'begin_date', 'BEGIN_DATE') || '',
        end_date: getStringValue(properties, 'end_date', 'END_DATE', 'end_time', 'END_TIME', 'finish_date', 'FINISH_DATE') || '',
        area_km2: parseNumberValue(properties, 'area_km2', 'AREA_KM2', 'area', 'AREA'),
        rawProperties: properties
      }
    })
  } catch (error) {
    console.error('解析工程数据失败:', error)
    return []
  }
}

// 切换图层可见性
const toggleLayer = (layerType) => {
  try {
    if (layerType === 'ecology' && ecologyRasterLayer) {
      syncEcologyLayerVisibility(props.layerVisibility.ecology)
    } else if (layerType === 'economy' && economyVectorLayer) {
      economyVectorLayer.setVisible(props.layerVisibility.economy)
    } else if (layerType === 'engineering' && engineeringVectorLayer) {
      engineeringVectorLayer.setVisible(props.layerVisibility.engineering)
    }
    
    map?.render()
  } catch (error) {
    console.error('切换图层失败:', error)
  }
}

// 刷新地图
const refreshMap = () => {
  handleRefreshMap()
}

// 暴露方法给父组件
defineExpose({
  toggleLayer,
  refreshMap
})

// 关闭弹窗
const closePopup = () => {
  popup.visible = false
}

// 处理地图刷新（上传完成后）
const handleRefreshMap = () => {
  console.log('🔄 数据上传完成，刷新地图图层...')

  refreshEcologyDisplayLayer()
  
  // 刷新所有WMS图层
  if (ecologyRasterLayer) {
    const source = ecologyRasterLayer.getSource()
    source.updateParams({ 'timestamp': Date.now() })
    source.refresh()
  }
  
  if (economyVectorLayer) {
    const source = economyVectorLayer.getSource()
    source.updateParams({ 'timestamp': Date.now() })
    source.refresh()
  }
  
  if (engineeringVectorLayer) {
    const source = engineeringVectorLayer.getSource()
    source.updateParams({ 'timestamp': Date.now() })
    source.refresh()
  }
  
  // 强制地图重新渲染
  if (map) {
    map.render()
  }
  
  console.log('✅ 地图图层已刷新')
}

// 缩放控制
const zoomIn = () => {
  const view = map?.getView()
  if (view) {
    const zoom = view.getZoom()
    view.animate({ zoom: zoom + 1, duration: 250 })
  }
}

const zoomOut = () => {
  const view = map?.getView()
  if (view) {
    const zoom = view.getZoom()
    view.animate({ zoom: zoom - 1, duration: 250 })
  }
}

// 生命周期
onMounted(() => {
  console.log('🚀 OverlayMapContainer 组件已挂载')
  
  // 等待DOM完全渲染
      setTimeout(() => {
    const mapElement = document.getElementById('overlay-map')
    if (mapElement) {
      console.log('✅ 地图容器已找到')
      console.log('📏 容器尺寸:', {
        offsetWidth: mapElement.offsetWidth,
        offsetHeight: mapElement.offsetHeight
      })
      
      // 如果容器尺寸为0，等待更长时间
      if (mapElement.offsetWidth === 0 || mapElement.offsetHeight === 0) {
        console.warn('⚠️ 容器尺寸为0，延迟初始化...')
    setTimeout(() => {
          initMap()
        }, 500)
  } else {
        initMap()
        }
      } else {
      console.error('❌ 地图容器未找到')
      }
    }, 100)
})

onUnmounted(() => {
  if (map) {
    map.setTarget(undefined)
    map = null
  }
})
</script>

<style scoped>
#overlay-map-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background: #e5e5e5;
}

#overlay-map {
  width: 100%;
  height: 100%;
  min-height: 400px;
  position: absolute;
  top: 0;
  left: 0;
  background: #e5e5e5;
}

/* 确保OpenLayers容器正确渲染 */
#overlay-map .ol-viewport {
  position: relative !important;
}

#overlay-map canvas {
  position: absolute;
}

/* 缩放控制 */
.zoom-controls {
  position: absolute;
  top: 20px;
  right: 20px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  overflow: hidden;
  z-index: 1000;
}

.zoom-btn {
  width: 40px;
  height: 40px;
  border: none;
  background: white;
  cursor: pointer;
  font-size: 18px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.zoom-btn:hover {
  background: #f5f5f5;
}

.zoom-btn:first-child {
  border-bottom: 1px solid #f0f0f0;
}

/* 坐标显示 */
.coordinate-display {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 12px;
  color: #333;
  line-height: 1.6;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  z-index: 1000;
  font-family: 'Courier New', monospace;
}

</style>
