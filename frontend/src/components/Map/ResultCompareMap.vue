<template>
  <div class="compare-card">
    <div class="compare-head">
      <div>
        <h3>{{ title }}</h3>
        <p>{{ descriptionText }}</p>
      </div>
      <div class="compare-actions">
        <label class="opacity-control">
          <span>结果透明度</span>
          <input v-model="overlayOpacity" type="range" min="35" max="100" step="5" />
          <strong>{{ overlayOpacity }}%</strong>
        </label>
        <label class="imagery-toggle" :class="{ active: referenceImageryVisible, disabled: imageryLoading || !overlayAvailable }">
          <input
            type="checkbox"
            :checked="referenceImageryVisible"
            :disabled="imageryLoading || !overlayAvailable"
            @change="toggleReferenceImagery"
          />
          <span>{{ imageryLoading ? '影像加载中...' : '遥感影像底图' }}</span>
        </label>
      </div>
    </div>

    <div v-if="overlayAvailable" ref="mapEl" class="compare-map"></div>
    <div v-else class="compare-empty">{{ resolvedEmptyText }}</div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import 'ol/ol.css'
import Map from 'ol/Map'
import View from 'ol/View'
import ImageLayer from 'ol/layer/Image'
import TileLayer from 'ol/layer/Tile'
import ImageStatic from 'ol/source/ImageStatic'
import XYZ from 'ol/source/XYZ'
import { ScaleLine, defaults as defaultControls } from 'ol/control'
import { unByKey } from 'ol/Observable'
import { transformExtent } from 'ol/proj'
import { MapUtils } from '../../utils/mapUtils'
import {
  ensurePreferredHighResImageryRecord,
  getHighResImageryQualifiedLayerName
} from '../../utils/highResImagery.js'
import { API_CONFIG } from '../../config/api.js'

const props = defineProps({
  title: {
    type: String,
    default: '结果对比'
  },
  description: {
    type: String,
    default: ''
  },
  compareOverlay: {
    type: Object,
    default: null
  },
  emptyText: {
    type: String,
    default: '当前结果暂不支持地图叠加对比'
  }
})

const geoserverProxyUrl = `${API_CONFIG.BASE_URL}/${API_CONFIG.VERSION}/environment/geoserver/ows/`
const blankTileUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mO88ePHTwAJiwPL8wIMlQAAAABJRU5ErkJggg=='
const mapEl = ref(null)
const overlayOpacity = ref(65)
const referenceImageryVisible = ref(false)
const imageryLoading = ref(false)
const overlayLoadError = ref(false)

const descriptionText = computed(() => (
  props.description || '打开遥感影像底图后，可将当前分析结果直接叠加在上面进行对比。'
))
const overlayExtent = computed(() => resolveOverlayExtent())
const overlayAvailable = computed(() => Boolean(
  overlayExtent.value && props.compareOverlay?.overlay_image_url && !overlayLoadError.value
))
const resolvedEmptyText = computed(() => (
  overlayLoadError.value
    ? '结果叠加图文件不存在或生成失败，当前仅保留主结果图展示。请重新分析后再尝试对比。'
    : props.emptyText
))

let map
let baseLayer
let resultLayer
let referenceImageryLayer
let resizeObserver
let resultLayerErrorKey = null
let resultLayerLoadKey = null

onMounted(() => {
  if (!overlayAvailable.value) return
  initMap()
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  clearResultLayerEvents()
  if (map) {
    map.setTarget(undefined)
  }
})

watch(overlayAvailable, async available => {
  if (!available) {
    removeResultLayer()
    referenceImageryVisible.value = false
    return
  }

  await nextTick()

  if (!map) {
    initMap()
    return
  }
  rebuildResultLayer()
}, { flush: 'post' })

watch(() => props.compareOverlay, async () => {
  overlayLoadError.value = false
  await nextTick()
  if (!map) {
    if (overlayAvailable.value) {
      initMap()
    }
    return
  }
  rebuildResultLayer()
}, { deep: true, flush: 'post' })

watch(overlayOpacity, value => {
  if (resultLayer) {
    resultLayer.setOpacity(Number(value) / 100)
  }
})

function createBlankBaseLayer() {
  return new TileLayer({
    source: new XYZ({
      url: blankTileUrl,
      maxZoom: 22
    }),
    visible: true
  })
}

function initMap() {
  if (map || !mapEl.value) return
  baseLayer = createBlankBaseLayer()
  baseLayer.setZIndex(0)

  map = new Map({
    target: mapEl.value,
    layers: [baseLayer],
    view: new View({
      projection: 'EPSG:3857',
      center: [0, 0],
      zoom: 2
    }),
    controls: defaultControls({ zoom: true, rotate: false, attribution: false }).extend([
      new ScaleLine({ units: 'metric', bar: true, text: true, minWidth: 120 })
    ])
  })

  resizeObserver = new ResizeObserver(() => {
    map?.updateSize()
  })
  resizeObserver.observe(mapEl.value)
  requestAnimationFrame(() => {
    map?.updateSize()
  })

  rebuildResultLayer()
}

function getOverlayExtent() {
  return overlayExtent.value
}

function resolveOverlayExtent() {
  const bounds3857 = props.compareOverlay?.bounds_3857
  if (Array.isArray(bounds3857) && bounds3857.length === 4) {
    const extent = bounds3857.map(Number)
    if (extent.every(value => Number.isFinite(value))) {
      return extent
    }
  }

  const rawBounds = props.compareOverlay?.bounds
  const rawCrs = props.compareOverlay?.crs
  if (!Array.isArray(rawBounds) || rawBounds.length !== 4 || !rawCrs) {
    return null
  }

  const extent = rawBounds.map(Number)
  if (extent.some(value => !Number.isFinite(value))) {
    return null
  }

  try {
    return transformExtent(extent, rawCrs, 'EPSG:3857')
  } catch (error) {
    console.warn('结果范围转换到 EPSG:3857 失败:', rawCrs, error)
    return null
  }
}

function removeResultLayer() {
  if (!map || !resultLayer) return
  clearResultLayerEvents()
  map.removeLayer(resultLayer)
  resultLayer = null
}

function clearResultLayerEvents() {
  if (resultLayerErrorKey) {
    unByKey(resultLayerErrorKey)
    resultLayerErrorKey = null
  }
  if (resultLayerLoadKey) {
    unByKey(resultLayerLoadKey)
    resultLayerLoadKey = null
  }
}

function fitOverlayExtent() {
  const extent = getOverlayExtent()
  if (!map || !extent) return
  map.getView().fit(extent, { padding: [36, 36, 36, 36], duration: 250, maxZoom: 14 })
}

function buildVisualizationLayer(extent) {
  const source = new ImageStatic({
    url: props.compareOverlay.overlay_image_url,
    imageExtent: extent,
    projection: 'EPSG:3857'
  })

  resultLayerLoadKey = source.on('imageloadstart', () => {
    overlayLoadError.value = false
  })
  resultLayerErrorKey = source.on('imageloaderror', () => {
    console.warn('结果叠加图加载失败:', props.compareOverlay?.overlay_image_url || '')
    overlayLoadError.value = true
    referenceImageryVisible.value = false
    if (referenceImageryLayer) {
      referenceImageryLayer.setVisible(false)
    }
    removeResultLayer()
  })

  return new ImageLayer({
    source,
    opacity: Number(overlayOpacity.value) / 100
  })
}

function rebuildResultLayer() {
  if (!map) return
  overlayLoadError.value = false
  removeResultLayer()
  const extent = getOverlayExtent()
  if (!extent) return

  if (!props.compareOverlay?.overlay_image_url) {
    return
  }

  resultLayer = buildVisualizationLayer(extent)
  resultLayer.setZIndex(20)
  map.addLayer(resultLayer)
  fitOverlayExtent()
}

async function toggleReferenceImagery() {
  if (!overlayAvailable.value) return
  if (referenceImageryVisible.value) {
    referenceImageryVisible.value = false
    if (referenceImageryLayer) {
      referenceImageryLayer.setVisible(false)
    }
    return
  }

  imageryLoading.value = true
  try {
    if (!referenceImageryLayer) {
      const imageryRecord = await ensurePreferredHighResImageryRecord()
      const layerName = getHighResImageryQualifiedLayerName(imageryRecord)
      referenceImageryLayer = imageryRecord.source_kind === 'business_layer'
        ? MapUtils.loadWMS(geoserverProxyUrl, layerName, {
          visible: true,
          opacity: 1,
          serverType: 'geoserver',
          metadata: imageryRecord.metadata
        })
        : MapUtils.loadStaticWMSImage(geoserverProxyUrl, layerName, {
          visible: true,
          opacity: 1,
          serverType: 'geoserver',
          metadata: imageryRecord.metadata,
          imageUrl: imageryRecord.preview_image_url || undefined
        })
      referenceImageryLayer.setZIndex(10)
      map.addLayer(referenceImageryLayer)
    } else {
      referenceImageryLayer.setVisible(true)
    }
    referenceImageryVisible.value = true
    fitOverlayExtent()
  } catch (error) {
    console.error('加载遥感影像底图失败:', error)
  } finally {
    imageryLoading.value = false
  }
}
</script>

<style scoped>
.compare-card {
  margin-top: 18px;
  padding: 16px;
  border: 1px solid #dbe6f0;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbfe 100%);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.07);
}

.compare-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.compare-head h3 {
  margin: 0;
  color: #22354a;
  font-size: 17px;
  font-weight: 700;
}

.compare-head p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.compare-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.imagery-toggle {
  min-height: 38px;
  padding: 8px 12px;
  border: 1px solid #cddaea;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #35506d;
  background: #fff;
  cursor: pointer;
}

.imagery-toggle input {
  margin: 0;
}

.imagery-toggle.active {
  border-color: #5f7f9d;
  background: #edf5fc;
  color: #264f77;
}

.imagery-toggle.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.opacity-control {
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid #d5e1ed;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #42576c;
  background: #fff;
  font-size: 13px;
}

.opacity-control input {
  width: 130px;
}

.compare-map {
  margin-top: 14px;
  width: 100%;
  height: 360px;
  border: 1px solid #dbe6f0;
  border-radius: 14px;
  overflow: hidden;
  background: #eef4f8;
}

.compare-empty {
  margin-top: 14px;
  padding: 32px 18px;
  border: 1px dashed #c9d6e3;
  border-radius: 14px;
  color: #70859a;
  background: #fbfdff;
  text-align: center;
}

:deep(.ol-scale-bar) {
  left: 14px;
  bottom: 14px;
}

@media (max-width: 960px) {
  .compare-head {
    flex-direction: column;
  }

  .compare-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .compare-map {
    height: 300px;
  }
}
</style>
