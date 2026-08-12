<template>
  <div class="geojson-uploader">
    <div class="upload-container" @click="triggerFileUpload" @dragover.prevent="onDragOver" @dragleave.prevent="onDragLeave" @drop.prevent="onDrop" :class="{ 'drag-over': isDragOver }">
      <div class="upload-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="#1890ff" stroke-width="2" fill="none"/>
          <path d="M14 2V8H20" stroke="#1890ff" stroke-width="2" fill="none"/>
          <path d="M12 18V12" stroke="#1890ff" stroke-width="2" stroke-linecap="round"/>
          <path d="M9 15L12 12L15 15" stroke="#1890ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="upload-text">
        <h3>上传GeoJSON文件</h3>
        <p>拖放文件到此处或点击选择文件</p>
        <p class="file-types">支持的文件类型: .geojson, .json</p>
      </div>
    </div>

    <div v-if="selectedFile" class="file-info">
      <div class="file-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
          <polyline points="10 9 9 9 8 9"></polyline>
        </svg>
      </div>
      <div class="file-details">
        <div class="file-name">{{ selectedFile.name }}</div>
        <div class="file-size">{{ formatFileSize(selectedFile.size) }}</div>
      </div>
      <button class="remove-btn" @click.stop="clearFile">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div v-if="geoJSONData && !error" class="preview-container">
      <div class="preview-header">
        <h4>预览数据</h4>
        <div class="feature-count">{{ featureCount }}个要素</div>
      </div>
      <div class="preview-content">
        <div class="preview-info">
          <div class="info-item">
            <span class="info-label">类型:</span>
            <span class="info-value">{{ geoJSONType }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">坐标系:</span>
            <span class="info-value">{{ geoJSONCRS || 'WGS84 (默认)' }}</span>
          </div>
        </div>
        <div class="preview-actions">
          <button class="preview-btn" @click="loadToMap">加载到地图</button>
          <button class="generate-btn" @click="generateSampleData">生成示例数据</button>
        </div>
      </div>
    </div>

    <input 
      ref="fileInput" 
      type="file" 
      accept=".geojson,.json" 
      style="display: none;" 
      @change="handleFileChange"
    >
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// Props
const props = defineProps({
  maxFileSize: {
    type: Number,
    default: 10 * 1024 * 1024 // 10MB
  }
})

// Emits
const emit = defineEmits(['file-loaded', 'file-cleared', 'load-to-map', 'generate-sample'])

// Refs
const fileInput = ref(null)
const selectedFile = ref(null)
const geoJSONData = ref(null)
const error = ref(null)
const isDragOver = ref(false)

// 计算属性
const featureCount = computed(() => {
  if (!geoJSONData.value) return 0
  if (geoJSONData.value.type === 'FeatureCollection') {
    return geoJSONData.value.features?.length || 0
  }
  return geoJSONData.value.type === 'Feature' ? 1 : 0
})

const geoJSONType = computed(() => {
  if (!geoJSONData.value) return ''
  return geoJSONData.value.type
})

const geoJSONCRS = computed(() => {
  if (!geoJSONData.value || !geoJSONData.value.crs) return null
  return geoJSONData.value.crs.properties?.name || JSON.stringify(geoJSONData.value.crs)
})

// 方法
const triggerFileUpload = () => {
  if (!selectedFile.value) {
    fileInput.value.click()
  }
}

const handleFileChange = (event) => {
  const file = event.target.files[0]
  if (file) {
    processFile(file)
  }
}

const onDragOver = (event) => {
  isDragOver.value = true
}

const onDragLeave = (event) => {
  isDragOver.value = false
}

const onDrop = (event) => {
  isDragOver.value = false
  const file = event.dataTransfer.files[0]
  if (file) {
    processFile(file)
  }
}

const processFile = (file) => {
  // 检查文件大小
  if (file.size > props.maxFileSize) {
    error.value = `文件大小超过限制 (最大 ${formatFileSize(props.maxFileSize)})`
    return
  }

  // 检查文件类型
  if (!file.name.toLowerCase().endsWith('.geojson') && !file.name.toLowerCase().endsWith('.json')) {
    error.value = '只支持 GeoJSON 文件格式 (.geojson, .json)'
    return
  }

  selectedFile.value = file
  error.value = null

  // 读取文件内容
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result)
      
      // 验证是否为有效的 GeoJSON
      if (!isValidGeoJSON(data)) {
        error.value = '无效的 GeoJSON 格式'
        return
      }

      geoJSONData.value = data
      emit('file-loaded', { file, data })
    } catch (err) {
      console.error('解析 GeoJSON 失败:', err)
      error.value = '解析文件失败，请确保文件是有效的 GeoJSON 格式'
      geoJSONData.value = null
    }
  }

  reader.onerror = () => {
    error.value = '读取文件失败'
    geoJSONData.value = null
  }

  reader.readAsText(file)
}

const isValidGeoJSON = (data) => {
  // 基本验证
  if (!data || typeof data !== 'object') return false
  
  // 检查类型
  const validTypes = ['FeatureCollection', 'Feature', 'Point', 'MultiPoint', 
                      'LineString', 'MultiLineString', 'Polygon', 'MultiPolygon', 
                      'GeometryCollection']
  
  if (!data.type || !validTypes.includes(data.type)) return false
  
  // 更详细的验证可以根据需要添加
  return true
}

const clearFile = () => {
  selectedFile.value = null
  geoJSONData.value = null
  error.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
  emit('file-cleared')
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const loadToMap = () => {
  if (geoJSONData.value) {
    emit('load-to-map', {
      data: geoJSONData.value,
      fileName: selectedFile.value.name
    })
  }
}

const generateSampleData = () => {
  // 生成示例 GeoJSON 数据
  const sampleData = generateRandomGeoJSON()
  geoJSONData.value = sampleData
  selectedFile.value = { 
    name: '示例数据.geojson', 
    size: JSON.stringify(sampleData).length 
  }
  emit('generate-sample', sampleData)
}

// 生成随机 GeoJSON 数据
const generateRandomGeoJSON = () => {
  // 天水市附近的随机点
  const centerLon = 105.7 // 天水市经度
  const centerLat = 34.6  // 天水市纬度
  
  // 生成随机多边形
  const features = []
  
  // 生成3个随机多边形
  for (let i = 0; i < 3; i++) {
    // 随机偏移
    const offsetLon = (Math.random() - 0.5) * 0.2
    const offsetLat = (Math.random() - 0.5) * 0.2
    
    // 生成多边形的点
    const points = []
    const sides = Math.floor(Math.random() * 3) + 4 // 4-6边形
    const radius = Math.random() * 0.05 + 0.02 // 半径
    
    for (let j = 0; j < sides; j++) {
      const angle = (j / sides) * Math.PI * 2
      const lon = centerLon + offsetLon + Math.cos(angle) * radius
      const lat = centerLat + offsetLat + Math.sin(angle) * radius
      points.push([lon, lat])
    }
    
    // 闭合多边形
    points.push([...points[0]])
    
    // 创建要素
    features.push({
      type: 'Feature',
      properties: {
        id: i + 1,
        name: `示例区域 ${i + 1}`,
        type: ['生态修复区', '环境治理区', '生态保护区'][i % 3],
        area: `${(Math.random() * 20 + 5).toFixed(1)} km²`,
        status: ['规划中', '进行中', '已完成'][i % 3]
      },
      geometry: {
        type: 'Polygon',
        coordinates: [points]
      }
    })
  }
  
  return {
    type: 'FeatureCollection',
    features: features
  }
}
</script>

<style scoped>
.geojson-uploader {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.upload-container {
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 24px;
  text-align: center;
  background-color: #fafafa;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-container:hover, .drag-over {
  border-color: #1890ff;
  background-color: #e6f7ff;
}

.upload-icon {
  color: #8c8c8c;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-icon svg {
  width: 48px;
  height: 48px;
}

.upload-text h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #333;
}

.upload-text p {
  margin: 0;
  font-size: 14px;
  color: #666;
}

.file-types {
  margin-top: 8px;
  font-size: 12px !important;
  color: #999 !important;
}

.file-info {
  display: flex;
  align-items: center;
  padding: 12px;
  background: #f0f8ff;
  border: 1px solid #d6e8ff;
  border-radius: 6px;
}

.file-icon {
  color: #1890ff;
  margin-right: 12px;
}

.file-details {
  flex: 1;
}

.file-name {
  font-size: 14px;
  color: #333;
  font-weight: 500;
  margin-bottom: 4px;
  word-break: break-all;
}

.file-size {
  font-size: 12px;
  color: #999;
}

.remove-btn {
  background: none;
  border: none;
  color: #ff4d4f;
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.remove-btn:hover {
  background-color: #fff1f0;
}

.error-message {
  padding: 10px;
  background-color: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 6px;
  color: #ff4d4f;
  font-size: 14px;
}

.preview-container {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
}

.preview-header {
  background-color: #fafafa;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-header h4 {
  margin: 0;
  font-size: 14px;
  color: #333;
}

.feature-count {
  font-size: 12px;
  color: #666;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 10px;
}

.preview-content {
  padding: 16px;
}

.preview-info {
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  margin-bottom: 8px;
}

.info-label {
  width: 80px;
  font-size: 14px;
  color: #666;
}

.info-value {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.preview-actions {
  display: flex;
  gap: 12px;
}

.preview-btn, .generate-btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.preview-btn {
  background-color: #1890ff;
  color: white;
}

.preview-btn:hover {
  background-color: #40a9ff;
}

.generate-btn {
  background-color: #52c41a;
  color: white;
}

.generate-btn:hover {
  background-color: #73d13d;
}
</style>
