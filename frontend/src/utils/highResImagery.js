import { spatialService } from '../services/api.js'

export const PREFERRED_HIGHRES_IMAGERY_FILE = '2023.tif'
const PREFERRED_HIGHRES_IMAGERY_STEM = PREFERRED_HIGHRES_IMAGERY_FILE.replace(/\.[^.]+$/, '')

function basename(path = '') {
  return String(path).split('/').pop()?.split('\\').pop() || ''
}

function normalizeBusinessLayerImageryRecord(layer) {
  if (!layer || layer.layer_type !== 'raster') return null

  const rasterPath = layer.metadata?.source_raster_path || ''
  const fileName = basename(rasterPath || layer.file || '') || `${layer.name || PREFERRED_HIGHRES_IMAGERY_STEM}.tif`
  const layerName = String(layer.name || '').trim()
  const stem = fileName.replace(/\.[^.]+$/, '')
  const isPreferred =
    fileName === PREFERRED_HIGHRES_IMAGERY_FILE ||
    layerName === PREFERRED_HIGHRES_IMAGERY_STEM ||
    stem === PREFERRED_HIGHRES_IMAGERY_STEM

  if (!isPreferred) return null

  return {
    ...layer,
    id: `business:${layer.id}`,
    business_layer_id: layer.id,
    file_name: fileName,
    relative_path: fileName,
    source_kind: 'business_layer',
    status: layer.status || 'ready',
    metadata: layer.metadata || {}
  }
}

async function fetchPreferredBusinessLayerImageryRecord() {
  const response = await spatialService.getBusinessLayers()
  const list = Array.isArray(response?.results) ? response.results : (Array.isArray(response) ? response : [])
  for (const item of list) {
    const normalized = normalizeBusinessLayerImageryRecord(item)
    if (normalized) {
      return normalized
    }
  }
  return null
}

export async function fetchPreferredHighResImageryRecord() {
  const businessRecord = await fetchPreferredBusinessLayerImageryRecord()
  if (businessRecord) {
    return businessRecord
  }

  const response = await spatialService.getHighResImageryList()
  const list = Array.isArray(response?.results) ? response.results : []
  if (!list.length) return null
  return {
    ...(list.find(item => item.file_name === PREFERRED_HIGHRES_IMAGERY_FILE) || list[0]),
    source_kind: 'fixed_highres'
  }
}

export async function ensurePreferredHighResImageryRecord() {
  let imageryRecord = await fetchPreferredHighResImageryRecord()
  if (!imageryRecord?.id) {
    throw new Error('未找到可用的遥感影像底图')
  }

  if (!imageryRecord.geoserver_layer_name || imageryRecord.status !== 'published') {
    if (imageryRecord.source_kind === 'business_layer' && imageryRecord.business_layer_id) {
      imageryRecord = await spatialService.publishBusinessLayer(imageryRecord.business_layer_id)
      imageryRecord = {
        ...(normalizeBusinessLayerImageryRecord(imageryRecord) || imageryRecord),
        source_kind: 'business_layer'
      }
    } else {
      const response = await spatialService.publishHighResImagery({
        imagery_id: imageryRecord.id
      })
      imageryRecord = {
        ...(response?.result || imageryRecord),
        source_kind: 'fixed_highres'
      }
    }
  }

  if (!imageryRecord?.geoserver_layer_name) {
    throw new Error('遥感影像底图未成功发布')
  }

  return imageryRecord
}

export function getHighResImageryQualifiedLayerName(imageryRecord) {
  const workspace = imageryRecord?.geoserver_workspace || 'tianshuipy'
  return `${workspace}:${imageryRecord?.geoserver_layer_name || ''}`
}
