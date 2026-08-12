import TileLayer from 'ol/layer/Tile'
import ImageLayer from 'ol/layer/Image'
import VectorLayer from 'ol/layer/Vector'
import XYZ from 'ol/source/XYZ'
import ImageWMS from 'ol/source/ImageWMS'
import TileWMS from 'ol/source/TileWMS'
import ImageStatic from 'ol/source/ImageStatic'
import VectorSource from 'ol/source/Vector'
import KML from 'ol/format/KML'
import GeoJSON from 'ol/format/GeoJSON'
import { transform, transformExtent } from 'ol/proj'

// 天地图token（请替换为你自己的）
const TDT_TOKEN = '69874af7f35c741d7132c50f80acad29'

function createTiandituUrls(layer) {
  return Array.from({ length: 8 }, (_, index) =>
    `https://t${index}.tianditu.gov.cn/${layer}_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=${layer}&STYLE=default&FORMAT=tiles&TILEMATRIXSET=w&tk=${TDT_TOKEN}&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}`
  )
}

const osmUrls = [
  'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
  'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
  'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png'
]

// 地图工具类
export class MapUtils {
  // 创建底图图层
  static createBaseMap(type) {
    switch (type) {
      case 'blank':
        return new TileLayer({
          source: new XYZ({
            url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mO88ePHTwAJiwPL8wIMlQAAAABJRU5ErkJggg==',
            maxZoom: 22
          }),
          visible: true
        })
      case 'osm':
        return new TileLayer({
          source: new XYZ({
            urls: osmUrls,
            crossOrigin: 'anonymous',
            maxZoom: 19
          }),
          visible: true,
          preload: 1
        })
      case 'tdt_vec': // 天地图标准矢量
        return new TileLayer({
          source: new XYZ({
            urls: createTiandituUrls('vec'),
            crossOrigin: 'anonymous'
          }),
          visible: true,
          preload: 1
        })
      case 'tdt_img': // 天地图影像
        return new TileLayer({
          source: new XYZ({
            urls: createTiandituUrls('img'),
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
      case 'tdt_ter': // 天地图地形
        return new TileLayer({
          source: new XYZ({
            urls: createTiandituUrls('ter'),
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
      case 'tdt_gray': // 天地图灰色
        return new TileLayer({
          source: new XYZ({
            urls: createTiandituUrls('vec'),
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
      case 'satellite': // 兼容原有影像
        return new TileLayer({
          source: new XYZ({
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
      case 'terrain': // 兼容原有地形
        return new TileLayer({
          source: new XYZ({
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
      default:
        // 默认天地图标准矢量
        return new TileLayer({
          source: new XYZ({
            urls: createTiandituUrls('vec'),
            crossOrigin: 'anonymous'
          }),
          visible: true
        })
    }
  }

  // 加载KML文件
  static loadKML(url, options = {}) {
    const source = new VectorSource({
      url: url,
      format: new KML({
        extractStyles: options.extractStyles !== false
      })
    })

    return new VectorLayer({
      source: source,
      visible: options.visible !== false,
      style: options.style
    })
  }

  // 加载WMS服务
  static loadWMS(url, layers, options = {}) {
    const layerExtent = this.resolveMetadataExtent(options.metadata, options.targetProjection)
    const source = new TileWMS({
      url: url,
      params: {
        'LAYERS': layers,
        'VERSION': options.version || '1.1.1',
        'FORMAT': options.format || 'image/png',
        'TRANSPARENT': options.transparent !== false,
        'TILED': options.tiled !== false,
        ...(options.params || {})
      },
      serverType: options.serverType || 'geoserver',
      crossOrigin: 'anonymous'
    })

    return new TileLayer({
      source: source,
      visible: options.visible !== false,
      opacity: options.opacity !== undefined ? options.opacity : 1,
      extent: layerExtent || undefined
    })
  }

  // 加载ImageWMS服务（用于叠加分析的栅格图层）
  static loadImageWMS(url, layers, options = {}) {
    const layerExtent = this.resolveMetadataExtent(options.metadata, options.targetProjection)
    const source = new ImageWMS({
      url: url,
      params: {
        'LAYERS': layers,
        'VERSION': options.version || '1.1.1',
        'FORMAT': options.format || 'image/png',
        'TRANSPARENT': options.transparent !== false,
        ...(options.params || {})
      },
      serverType: options.serverType || 'geoserver',
      crossOrigin: 'anonymous',
      ratio: options.ratio || 1
    })

    const layer = new ImageLayer({
      source: source,
      visible: options.visible !== false,
      opacity: options.opacity !== undefined ? options.opacity : 0.7,
      extent: layerExtent || undefined
    })

    // 设置图层ID（用于管理）
    if (options.layerId) {
      layer.set('layerId', options.layerId)
      layer.set('layerName', options.layerName || options.layerId)
      layer.set('layerType', 'raster')
    }

    return layer
  }

  static resolveMetadataExtent(metadata = {}, targetProjection = 'EPSG:3857') {
    const bounds = Array.isArray(metadata.bounds) ? metadata.bounds.map(Number) : null
    if (!bounds || bounds.length !== 4 || bounds.some(value => !Number.isFinite(value))) {
      return null
    }

    const sourceCrs = metadata.crs || 'EPSG:4326'
    try {
      return sourceCrs === targetProjection ? bounds : transformExtent(bounds, sourceCrs, targetProjection)
    } catch (error) {
      console.warn('图层范围转换失败，按经纬度处理:', error)
      return targetProjection === 'EPSG:4326'
        ? bounds
        : transformExtent(bounds, 'EPSG:4326', targetProjection)
    }
  }

  // 加载固定范围的WMS影像，作为服务不可用时的降级显示。
  static loadStaticWMSImage(url, layers, options = {}) {
    const metadata = options.metadata || {}
    const bounds = Array.isArray(metadata.bounds) ? metadata.bounds.map(Number) : null
    if (!bounds || bounds.length !== 4 || bounds.some(value => !Number.isFinite(value))) {
      return this.loadImageWMS(url, layers, options)
    }

    const sourceCrs = metadata.crs || 'EPSG:4326'
    const targetProjection = options.targetProjection || 'EPSG:3857'
    let imageExtent = bounds
    try {
      imageExtent = sourceCrs === targetProjection ? bounds : transformExtent(bounds, sourceCrs, targetProjection)
    } catch (error) {
      console.warn('静态WMS影像范围转换失败，按经纬度处理:', error)
      imageExtent = targetProjection === 'EPSG:4326'
        ? bounds
        : transformExtent(bounds, 'EPSG:4326', targetProjection)
    }

    const extentWidth = Math.max(1, imageExtent[2] - imageExtent[0])
    const extentHeight = Math.max(1, imageExtent[3] - imageExtent[1])
    const aspectRatio = extentWidth / extentHeight
    const imageWidth = options.width || 2048
    const imageHeight = Math.max(256, Math.round(imageWidth / aspectRatio))
    const requestUrl = new URL(url, window.location.origin)
    requestUrl.searchParams.set('SERVICE', 'WMS')
    requestUrl.searchParams.set('VERSION', options.version || '1.1.1')
    requestUrl.searchParams.set('REQUEST', 'GetMap')
    requestUrl.searchParams.set('LAYERS', layers)
    requestUrl.searchParams.set('STYLES', options.styles || '')
    requestUrl.searchParams.set('SRS', targetProjection)
    requestUrl.searchParams.set('BBOX', imageExtent.join(','))
    requestUrl.searchParams.set('WIDTH', String(imageWidth))
    requestUrl.searchParams.set('HEIGHT', String(imageHeight))
    requestUrl.searchParams.set('FORMAT', options.format || 'image/png')
    requestUrl.searchParams.set('TRANSPARENT', String(options.transparent !== false))

    const source = new ImageStatic({
      url: options.imageUrl || requestUrl.toString(),
      imageExtent,
      projection: targetProjection,
      crossOrigin: 'anonymous'
    })

    source.on('imageloaderror', (event) => {
      console.error('静态遥感影像加载失败:', {
        layers,
        url: options.imageUrl || requestUrl.toString(),
        extent: imageExtent,
        event
      })
    })

    source.on('imageloadend', () => {
      console.log('静态遥感影像加载完成:', {
        layers,
        url: options.imageUrl || requestUrl.toString(),
        extent: imageExtent
      })
    })

    return new ImageLayer({
      source,
      visible: options.visible !== false,
      opacity: options.opacity !== undefined ? options.opacity : 1
    })
  }

  // 获取WMS GetFeatureInfo（用于点击获取信息）
  static async getFeatureInfo(layerSource, coordinate, map) {
    try {
      const viewResolution = map.getView().getResolution()
      const viewProjection = map.getView().getProjection()
      const viewSize = map.getSize()
      
      if (!viewSize || viewSize[0] === 0 || viewSize[1] === 0) {
        console.warn('地图尺寸无效:', viewSize)
        return null
      }
      
      // 对于TileWMS，需要手动构建GetFeatureInfo URL
      // 因为TileWMS可能不支持getFeatureInfoUrl方法
      const params = layerSource.getParams()
      const baseUrl = layerSource.getUrls()[0] || layerSource.getUrl()
      
      if (!baseUrl) {
        console.warn('无法获取WMS基础URL')
        return null
      }
      
      // 验证坐标有效性
      if (!coordinate || coordinate.length !== 2 || 
          isNaN(coordinate[0]) || isNaN(coordinate[1]) ||
          !isFinite(coordinate[0]) || !isFinite(coordinate[1])) {
        console.warn('坐标无效:', coordinate)
        return null
      }
      
      // 计算像素坐标（相对于地图容器）
      const pixel = map.getPixelFromCoordinate(coordinate)
      
      // 验证像素坐标有效性
      if (!pixel || pixel.length !== 2 || 
          isNaN(pixel[0]) || isNaN(pixel[1]) ||
          !isFinite(pixel[0]) || !isFinite(pixel[1])) {
        console.warn('像素坐标无效:', pixel, '坐标:', coordinate, '视图尺寸:', viewSize)
        return null
      }
      
      // 确保像素坐标在有效范围内
      const i = Math.max(0, Math.min(Math.round(pixel[0]), viewSize[0] - 1))
      const j = Math.max(0, Math.min(Math.round(pixel[1]), viewSize[1] - 1))
      
      // 验证计算后的i和j
      if (isNaN(i) || isNaN(j) || !isFinite(i) || !isFinite(j)) {
        console.warn('计算后的像素索引无效:', { i, j, pixel, viewSize })
        return null
      }
      
      // 获取地图视图范围
      const viewExtent = map.getView().calculateExtent(viewSize)
      let [minX, minY, maxX, maxY] = viewExtent
      
      // 获取投影代码
      const projectionCode = viewProjection.getCode() || 'EPSG:3857'
      
      // 使用 WMS 1.1.0（更兼容，BBOX 顺序简单）
      // WMS 1.1.0 统一使用 minX,minY,maxX,maxY 格式，不区分投影类型
      const bbox = `${minX},${minY},${maxX},${maxY}`
      
      // 构建GetFeatureInfo请求URL
      const url = new URL(baseUrl, window.location.origin)
      url.searchParams.set('SERVICE', 'WMS')
      url.searchParams.set('VERSION', '1.1.0')  // 使用 1.1.0 版本
      url.searchParams.set('REQUEST', 'GetFeatureInfo')
      url.searchParams.set('LAYERS', params.LAYERS)
      url.searchParams.set('STYLES', params.STYLES || '')
      url.searchParams.set('SRS', projectionCode)  // 1.1.0 使用 SRS 而不是 CRS
      url.searchParams.set('BBOX', bbox)
      url.searchParams.set('WIDTH', viewSize[0].toString())
      url.searchParams.set('HEIGHT', viewSize[1].toString())
      url.searchParams.set('QUERY_LAYERS', params.LAYERS)
      url.searchParams.set('INFO_FORMAT', 'application/json')
      url.searchParams.set('FEATURE_COUNT', '50')
      // WMS 1.1.0 使用 X 和 Y 参数（而不是 1.3.0 的 I 和 J）
      // X 是列索引，Y 是行索引（从上到下，0 在顶部）
      url.searchParams.set('X', i.toString())
      url.searchParams.set('Y', j.toString())  // 1.1.0 不需要反转
      
      console.log('GetFeatureInfo请求 (WMS 1.1.0):', {
        url: url.toString(),
        pixel: pixel,
        x: i,
        y: j,
        viewSize: viewSize,
        bbox: bbox,
        srs: projectionCode
      })
      
      // 发送请求（明确指定UTF-8字符集）
      const response = await fetch(url.toString(), {
        method: 'GET',
        mode: 'cors',
        headers: {
          'Accept': 'application/json; charset=UTF-8',
          'Accept-Charset': 'UTF-8'
        }
      })
      
      if (!response.ok) {
        console.warn(`GetFeatureInfo请求失败: ${response.status} ${response.statusText}`)
        // 尝试读取响应内容
        const text = await response.text()
        console.warn('响应内容:', text.substring(0, 500))
        return null
      }
      
      // 检查Content-Type
      const contentType = response.headers.get('content-type') || ''
      
      // 先读取为文本，确保使用 UTF-8 解码
      const text = await response.text()
      
      if (contentType.includes('application/json')) {
        try {
          // 解析 JSON（已经是 UTF-8 解码的文本）
          const data = JSON.parse(text)
          return data
        } catch (e) {
          console.warn('JSON解析失败:', e)
          return null
        }
      } else if (contentType.includes('text/html') || contentType.includes('text/xml')) {
        // GeoServer可能返回HTML错误页面或XML格式
        console.warn('GetFeatureInfo返回非JSON格式:', contentType)
        console.warn('响应内容:', text.substring(0, 500))
        return null
      } else {
        // 尝试解析为JSON
        try {
          const data = JSON.parse(text)
          return data
        } catch (e) {
          console.log('该位置无数据或响应格式非JSON')
          return null
        }
      }
    } catch (error) {
      console.error('获取GetFeatureInfo失败:', error)
      return null
    }
  }

  // 批量获取多个图层的GetFeatureInfo
  static async getMultipleFeatureInfo(layerSources, coordinate, map) {
    const results = {}
    
    for (const [layerId, layerSource] of Object.entries(layerSources)) {
      try {
        const info = await this.getFeatureInfo(layerSource, coordinate, map)
        if (info) {
          results[layerId] = info
        }
      } catch (error) {
        console.error(`获取图层 ${layerId} 的FeatureInfo失败:`, error)
      }
    }
    
    return results
  }

  // 从WMS URL加载栅格图层（用于叠加分析结果）
  static loadRasterFromWMS(wmsUrl, layerMetadata, options = {}) {
    try {
      console.log('loadRasterFromWMS 被调用:', { wmsUrl, layerMetadata, options })
      
      // 解析WMS URL，提取图层名称
      const urlObj = new URL(wmsUrl, window.location.origin)
      const layersParam = urlObj.searchParams.get('layers') || urlObj.searchParams.get('LAYERS')
      
      console.log('解析WMS URL:', {
        url: wmsUrl,
        origin: urlObj.origin,
        pathname: urlObj.pathname,
        layersParam: layersParam,
        allParams: Object.fromEntries(urlObj.searchParams)
      })
      
      if (!layersParam) {
        console.error('WMS URL中未找到layers参数')
        console.error('URL:', wmsUrl)
        console.error('所有参数:', Object.fromEntries(urlObj.searchParams))
        return null
      }

      // 提取图层名称（去除workspace前缀）
      const layerName = layersParam.includes(':') ? layersParam.split(':')[1] : layersParam
      const baseUrl = `${urlObj.origin}${urlObj.pathname}`

      console.log('提取的信息:', {
        layerName,
        baseUrl,
        fullLayersParam: layersParam
      })

      // 使用ImageWMS或TileWMS
      const useTileWMS = options.useTileWMS !== false  // 默认使用TileWMS以获得更好的性能
      
      if (useTileWMS) {
        // WMS 1.3.0使用CRS参数，1.1.0使用SRS参数
        // 根据GeoServer最佳实践，明确指定CRS
        const source = new TileWMS({
          url: baseUrl,
          params: {
            'LAYERS': layersParam,
            'VERSION': '1.3.0',
            'REQUEST': 'GetMap',
            'TRANSPARENT': true,
            'CRS': 'EPSG:3857', // WMS 1.3.0使用CRS
            'FORMAT': 'image/png',
            'TILED': true
          },
          serverType: 'geoserver',
          crossOrigin: 'anonymous',
          // 设置投影转换
          projection: 'EPSG:3857'
        })

        console.log('创建TileWMS源:', {
          url: baseUrl,
          params: source.getParams()
        })

        const layer = new TileLayer({
          source: source,
          visible: options.visible !== false,
          opacity: options.opacity !== undefined ? options.opacity : 0.7
        })

        // 设置图层元数据
        if (layerMetadata) {
          layer.set('layerId', layerMetadata.layer_name || layerName)
          layer.set('layerName', layerMetadata.description || layerName)
          layer.set('layerType', 'raster')
          layer.set('layerMetadata', layerMetadata)
        }

        console.log('创建的TileLayer:', {
          visible: layer.getVisible(),
          opacity: layer.getOpacity(),
          layerId: layer.get('layerId'),
          sourceUrl: baseUrl
        })

        // 监听错误，如果TileWMS失败，可以考虑fallback到ImageWMS
        source.on('tileloaderror', (event) => {
          console.warn('TileWMS瓦片加载失败，可以考虑切换到ImageWMS:', event)
        })

        return layer
      } else {
        // 使用ImageWMS
        return this.loadImageWMS(baseUrl, layersParam, {
          ...options,
          layerId: layerMetadata?.layer_name || layerName,
          layerName: layerMetadata?.description || layerName
        })
      }
    } catch (error) {
      console.error('加载栅格图层失败:', error)
      console.error('错误详情:', {
        message: error.message,
        stack: error.stack,
        wmsUrl,
        layerMetadata
      })
      return null
    }
  }

  // 加载WFS服务
  static loadWFS(url, typeName, options = {}) {
    const source = new VectorSource({
      format: new GeoJSON(),
      url: function(extent) {
        return url + '?' +
          'service=WFS&' +
          'version=1.0.0&' +
          'request=GetFeature&' +
          'typeName=' + typeName + '&' +
          'maxFeatures=50&' +
          'outputFormat=application/json&' +
          'srsname=EPSG:3857&' +
          'bbox=' + extent.join(',') + ',EPSG:3857'
      },
      strategy: options.strategy
    })

    return new VectorLayer({
      source: source,
      visible: options.visible !== false,
      style: options.style
    })
  }

  // 加载GeoJSON数据
  static loadGeoJSON(data, options = {}) {
    const source = new VectorSource({
      features: new GeoJSON().readFeatures(data, {
        featureProjection: 'EPSG:3857'
      })
    })

    return new VectorLayer({
      source: source,
      visible: options.visible !== false,
      style: options.style
    })
  }

  // 从本地文件加载数据
  static loadFromFile(file, options = {}) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      
      reader.onload = (event) => {
        try {
          let layer
          const content = event.target.result
          
          if (file.name.toLowerCase().endsWith('.kml')) {
            layer = this.loadKML(content, options)
          } else if (file.name.toLowerCase().endsWith('.geojson') || file.name.toLowerCase().endsWith('.json')) {
            const data = JSON.parse(content)
            layer = this.loadGeoJSON(data, options)
          } else {
            reject(new Error('不支持的文件格式'))
            return
          }
          
          resolve(layer)
        } catch (error) {
          reject(error)
        }
      }
      
      reader.onerror = () => {
        reject(new Error('文件读取失败'))
      }
      
      if (file.name.toLowerCase().endsWith('.kml')) {
        reader.readAsText(file)
      } else {
        reader.readAsText(file)
      }
    })
  }

  // 坐标转换
  static transformCoordinates(coordinates, fromProjection, toProjection) {
    return transform(coordinates, fromProjection, toProjection)
  }

  // 获取图层范围
  static getLayerExtent(layer) {
    const source = layer.getSource()
    if (source.getExtent) {
      return source.getExtent()
    }
    return null
  }

  // 缩放到图层
  static zoomToLayer(map, layer) {
    const extent = this.getLayerExtent(layer)
    if (extent) {
      map.getView().fit(extent, {
        padding: [50, 50, 50, 50],
        duration: 1000
      })
    }
  }
} 
