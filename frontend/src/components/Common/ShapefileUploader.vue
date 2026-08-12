<template>
  <div class="shapefile-uploader">
    <div class="upload-container" @click="triggerFileUpload" @dragover.prevent="onDragOver" @dragleave.prevent="onDragLeave" @drop.prevent="onDrop" :class="{ 'drag-over': isDragOver }">
      <div class="upload-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
      </div>
      <div class="upload-text">
        <h3>上传Shapefile文件</h3>
        <p>拖放ZIP压缩包到此处或点击选择文件</p>
        <p class="file-types">支持的文件类型: .zip (包含.shp, .dbf, .shx等文件)</p>
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

    <div v-if="isProcessing" class="processing-message">
      <div class="spinner"></div>
      <span>正在处理Shapefile文件...</span>
    </div>

    <div v-if="geoJSONData && !error && !isProcessing" class="preview-container">
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
            <span class="info-label">属性字段:</span>
            <span class="info-value">{{ attributeFields.join(', ') }}</span>
          </div>
        </div>
        <div class="preview-actions">
          <button class="preview-btn" @click="loadToMap">加载到地图</button>
        </div>
      </div>
    </div>

    <input 
      ref="fileInput" 
      type="file" 
      accept=".zip" 
      style="display: none;" 
      @change="handleFileChange"
    >
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import * as shpjs from 'shpjs'
import JSZip from 'jszip'

// Props
const props = defineProps({
  maxFileSize: {
    type: Number,
    default: 20 * 1024 * 1024 // 20MB
  }
})

// Emits
const emit = defineEmits(['file-loaded', 'file-cleared', 'load-to-map'])

// Refs
const fileInput = ref(null)
const selectedFile = ref(null)
const geoJSONData = ref(null)
const error = ref(null)
const isDragOver = ref(false)
const isProcessing = ref(false)

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

const attributeFields = computed(() => {
  if (!geoJSONData.value || !geoJSONData.value.features || geoJSONData.value.features.length === 0) return []
  const firstFeature = geoJSONData.value.features[0]
  return Object.keys(firstFeature.properties || {})
})

// 方法
const triggerFileUpload = () => {
  if (!selectedFile.value && !isProcessing.value) {
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

const processFile = async (file) => {
  // 检查文件大小
  if (file.size > props.maxFileSize) {
    error.value = `文件大小超过限制 (最大 ${formatFileSize(props.maxFileSize)})`
    return
  }

  // 检查文件类型
  if (!file.name.toLowerCase().endsWith('.zip')) {
    error.value = '只支持ZIP压缩格式的Shapefile文件'
    return
  }

  selectedFile.value = file
  error.value = null
  isProcessing.value = true

  try {
    // 读取ZIP文件
    const zipData = await readFileAsArrayBuffer(file)
    const zip = await JSZip.loadAsync(zipData)
    
    // 检查是否包含必要的Shapefile文件
    const shpFile = findFileByExtension(zip, '.shp')
    const dbfFile = findFileByExtension(zip, '.dbf')
    
    if (!shpFile || !dbfFile) {
      throw new Error('ZIP文件中缺少必要的Shapefile组件 (.shp和.dbf文件)')
    }
    
    // 提取所有Shapefile相关文件
    const shpBuffer = await shpFile.async('arraybuffer')
    
    // 使用shpjs解析Shapefile
    const geojson = await shpjs.parseShp(shpBuffer)
    
    // 如果有DBF文件，解析属性数据
    if (dbfFile) {
      const dbfBuffer = await dbfFile.async('arraybuffer')
      const attributes = await shpjs.parseDbf(dbfBuffer)
      
      // 合并几何和属性数据
      const merged = shpjs.combine([geojson, attributes])
      geoJSONData.value = merged
    } else {
      geoJSONData.value = geojson
    }
    
    // 确保数据是FeatureCollection格式
    if (geoJSONData.value && !geoJSONData.value.type) {
      geoJSONData.value = {
        type: 'FeatureCollection',
        features: Array.isArray(geoJSONData.value) ? geoJSONData.value : [geoJSONData.value]
      }
    }
    
    emit('file-loaded', { file, data: geoJSONData.value })
    
  } catch (err) {
    console.error('处理Shapefile文件失败:', err)
    error.value = `处理Shapefile文件失败: ${err.message}`
    geoJSONData.value = null
  } finally {
    isProcessing.value = false
  }
}

// 查找ZIP中指定扩展名的文件
const findFileByExtension = (zip, extension) => {
  let foundFile = null
  zip.forEach((relativePath, zipEntry) => {
    if (!zipEntry.dir && relativePath.toLowerCase().endsWith(extension)) {
      foundFile = zipEntry
    }
  })
  return foundFile
}

// 将文件读取为ArrayBuffer
const readFileAsArrayBuffer = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result)
    reader.onerror = (e) => reject(new Error('读取文件失败'))
    reader.readAsArrayBuffer(file)
  })
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
      fileName: selectedFile.value.name.replace('.zip', '')
    })
  }
}
</script>

<style scoped>
.shapefile-uploader {
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

.processing-message {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background-color: #e6f7ff;
  border: 1px solid #91d5ff;
  border-radius: 6px;
  color: #1890ff;
  font-size: 14px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(24, 144, 255, 0.3);
  border-radius: 50%;
  border-top-color: #1890ff;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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
  flex: 1;
  word-break: break-all;
}

.preview-actions {
  display: flex;
  gap: 12px;
}

.preview-btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
  background-color: #1890ff;
  color: white;
}

.preview-btn:hover {
  background-color: #40a9ff;
}
</style>
