<template>
  <div class="ecological-indices-uploader">
    <div class="upload-container" @click="triggerFileUpload" @dragover.prevent="onDragOver" @dragleave.prevent="onDragLeave" @drop.prevent="onDrop" :class="{ 'drag-over': isDragOver }">
      <div class="upload-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
      </div>
      <div class="upload-text">
        <h3>上传生态指数文件</h3>
        <p>拖放生态指数JSON文件到此处或点击选择文件</p>
        <p class="file-types">支持的文件类型: .json</p>
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

    <div v-if="indicesData && !error" class="preview-container">
      <div class="preview-header">
        <h4>生态指数数据预览</h4>
        <div class="timestamp">{{ formatDate(indicesData.timestamp) }}</div>
      </div>
      <div class="preview-content">
        <div class="preview-info">
          <div class="info-item">
            <span class="info-label">文件名:</span>
            <span class="info-value">{{ indicesData.filename }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">计算时间:</span>
            <span class="info-value">{{ indicesData.summary?.calculated_time || formatDate(indicesData.timestamp) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">指数数量:</span>
            <span class="info-value">{{ indicesData.summary?.total_indices || Object.keys(indicesData.results || {}).length }}</span>
          </div>
        </div>
        
        <div class="indices-list">
          <h5>生态指数列表</h5>
          <div class="indices-table">
            <div class="table-row header">
              <div class="table-cell">指数名称</div>
              <div class="table-cell">数值</div>
              <div class="table-cell">等级</div>
            </div>
            <div v-for="(value, key) in indicesData.results" :key="key" class="table-row">
              <div class="table-cell">{{ formatIndexName(key) }}</div>
              <div class="table-cell">{{ formatIndexValue(value) }}</div>
              <div class="table-cell">
                <div class="index-level" :class="getIndexLevel(key, value)">
                  {{ getIndexLevelText(key, value) }}
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="preview-actions">
          <button class="preview-btn" @click="visualizeOnMap">在地图上可视化</button>
          <button class="analysis-btn" @click="analyzeWithOtherLayers">与其他图层叠加分析</button>
        </div>
      </div>
    </div>

    <input 
      ref="fileInput" 
      type="file" 
      accept=".json" 
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
    default: 5 * 1024 * 1024 // 5MB
  }
})

// Emits
const emit = defineEmits(['file-loaded', 'file-cleared', 'visualize-on-map', 'analyze-with-layers'])

// Refs
const fileInput = ref(null)
const selectedFile = ref(null)
const indicesData = ref(null)
const error = ref(null)
const isDragOver = ref(false)

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
  if (!file.name.toLowerCase().endsWith('.json')) {
    error.value = '只支持JSON文件格式'
    return
  }

  selectedFile.value = file
  error.value = null

  // 读取文件内容
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result)
      
      // 验证是否为有效的生态指数数据
      if (!isValidIndicesData(data)) {
        error.value = '无效的生态指数数据格式'
        return
      }

      indicesData.value = data
      emit('file-loaded', { file, data })
    } catch (err) {
      console.error('解析JSON失败:', err)
      error.value = '解析文件失败，请确保文件是有效的JSON格式'
      indicesData.value = null
    }
  }

  reader.onerror = () => {
    error.value = '读取文件失败'
    indicesData.value = null
  }

  reader.readAsText(file)
}

// 验证生态指数数据格式
const isValidIndicesData = (data) => {
  // 基本验证
  if (!data || typeof data !== 'object') return false
  
  // 检查必要字段
  if (!data.results || typeof data.results !== 'object') return false
  
  // 检查是否有至少一个指数
  if (Object.keys(data.results).length === 0) return false
  
  return true
}

const clearFile = () => {
  selectedFile.value = null
  indicesData.value = null
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

const formatDate = (dateString) => {
  if (!dateString) return '未知时间'
  try {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN')
  } catch (e) {
    return dateString
  }
}

// 格式化指数名称
const formatIndexName = (key) => {
  const nameMap = {
    'fragmentation_index': '破碎化指数',
    'shannon_diversity': '多样性指数',
    'cohesion_index': '内聚力指数',
    'fragility_index': '脆弱性指数',
    'soil_erosion_index': '土壤侵蚀指数',
    'unused_land_proportion': '未利用土地比例(%)',
    'cultivated_construction_proportion': '耕地与建设用地比例(%)',
    'land_degradation_index': '土地退化指数'
  }
  
  return nameMap[key] || key.replace(/_/g, ' ')
}

// 格式化指数值
const formatIndexValue = (value) => {
  if (typeof value === 'number') {
    return value.toFixed(4)
  }
  return value
}

// 获取指数等级 - 与生态环境评估界面保持一致的标准
const getIndexLevel = (key, value) => {
  if (typeof value !== 'number') return 'level-unknown'
  
  // 不同指数有不同的等级划分标准
  switch (key) {
    case 'fragmentation_index':
      // 破碎化指数：0表示完全未破碎，1表示极度破碎
      if (value === 0) return 'level-excellent' // 优：完全未破碎
      if (value < 0.3) return 'level-good'      // 良：轻微破碎
      if (value < 0.5) return 'level-moderate'  // 中：中度破碎
      if (value < 0.7) return 'level-poor'      // 差：严重破碎
      return 'level-bad'                        // 劣：极度破碎
    
    case 'shannon_diversity':
      // 多样性指数：值越高表示多样性越丰富
      if (value > 2.0) return 'level-excellent' // 优：非常丰富的多样性
      if (value > 1.5) return 'level-good'      // 良：较好的多样性
      if (value > 1.0) return 'level-moderate'  // 中：中等多样性
      if (value > 0.5) return 'level-poor'      // 差：较低多样性
      return 'level-bad'                        // 劣：极低多样性
      
    case 'cohesion_index':
      // 内聚力指数：值越高表示连接性越好
      if (value === 0) return 'level-bad'       // 劣：无连接性
      if (value < 0.3) return 'level-poor'      // 差：低连接性
      if (value < 0.5) return 'level-moderate'  // 中：中等连接性
      if (value < 0.8) return 'level-good'      // 良：良好连接性
      return 'level-excellent'                  // 优：极佳连接性
      
    case 'fragility_index':
      // 脆弱性指数：值越低表示抵抗力越强
      if (value < 0.2) return 'level-excellent' // 优：极低脆弱性
      if (value < 0.3) return 'level-good'      // 良：低脆弱性
      if (value < 0.5) return 'level-moderate'  // 中：中等脆弱性
      if (value < 0.7) return 'level-poor'      // 差：高脆弱性
      return 'level-bad'                        // 劣：极高脆弱性
      
    case 'soil_erosion_index':
      // 土壤侵蚀指数：值越低表示侵蚀程度越轻
      if (value < 0.2) return 'level-excellent' // 优：微度侵蚀
      if (value < 0.3) return 'level-good'      // 良：轻度侵蚀
      if (value < 0.5) return 'level-moderate'  // 中：中度侵蚀
      if (value < 0.7) return 'level-poor'      // 差：重度侵蚀
      return 'level-bad'                        // 劣：极重度侵蚀
      
    case 'land_degradation_index':
      // 土地退化指数：值越低表示退化程度越轻
      if (value < 0.2) return 'level-excellent' // 优：微度退化
      if (value < 0.3) return 'level-good'      // 良：轻度退化
      if (value < 0.5) return 'level-moderate'  // 中：中度退化
      if (value < 0.7) return 'level-poor'      // 差：重度退化
      return 'level-bad'                        // 劣：极重度退化
      
    case 'unused_land_proportion':
      // 未利用土地比例：按照生态环境评估界面标准
      if (value < 5) return 'level-excellent'   // 优：极低比例
      if (value < 10) return 'level-good'       // 良：低比例
      if (value < 15) return 'level-moderate'   // 中：中等比例
      if (value < 20) return 'level-poor'       // 差：高比例
      return 'level-bad'                        // 劣：极高比例
      
    case 'cultivated_construction_proportion':
      // 耕地与建设用地比例：按照生态环境评估界面标准
      if (value >= 35 && value <= 45) return 'level-excellent' // 优：最佳平衡
      if (value >= 30 && value < 35 || value > 45 && value <= 50) return 'level-good' // 良：良好平衡
      if (value >= 25 && value < 30 || value > 50 && value <= 55) return 'level-moderate' // 中：一般平衡
      if (value >= 20 && value < 25 || value > 55 && value <= 60) return 'level-poor' // 差：较差平衡
      return 'level-bad' // 劣：严重失衡
      
    default:
      return 'level-unknown'
  }
}

// 获取指数等级文本
const getIndexLevelText = (key, value) => {
  const level = getIndexLevel(key, value)
  
  const levelMap = {
    'level-excellent': '优',
    'level-good': '良',
    'level-moderate': '中',
    'level-poor': '差',
    'level-bad': '劣',
    'level-unknown': '未知'
  }
  
  return levelMap[level] || '未知'
}

// 在地图上可视化
const visualizeOnMap = () => {
  if (indicesData.value) {
    emit('visualize-on-map', {
      data: indicesData.value,
      fileName: selectedFile.value.name
    })
  }
}

// 与其他图层叠加分析
const analyzeWithOtherLayers = () => {
  if (indicesData.value) {
    emit('analyze-with-layers', {
      data: indicesData.value,
      fileName: selectedFile.value.name
    })
  }
}
</script>

<style scoped>
.ecological-indices-uploader {
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

.timestamp {
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
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 12px;
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

.indices-list {
  margin-bottom: 20px;
}

.indices-list h5 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #333;
}

.indices-table {
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.table-row {
  display: flex;
  border-bottom: 1px solid #f0f0f0;
}

.table-row:last-child {
  border-bottom: none;
}

.table-row.header {
  background-color: #fafafa;
  font-weight: 500;
}

.table-cell {
  flex: 1;
  padding: 8px 12px;
  font-size: 13px;
  display: flex;
  align-items: center;
}

.table-cell:not(:last-child) {
  border-right: 1px solid #f0f0f0;
}

.index-level {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  text-align: center;
}

.level-excellent {
  background-color: #f6ffed;
  color: #52c41a;
}

.level-good {
  background-color: #e6f7ff;
  color: #1890ff;
}

.level-moderate {
  background-color: #fffbe6;
  color: #faad14;
}

.level-poor {
  background-color: #fff7e6;
  color: #fa8c16;
}

.level-bad {
  background-color: #fff1f0;
  color: #f5222d;
}

.level-unknown {
  background-color: #f5f5f5;
  color: #999;
}

.preview-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.preview-btn, .analysis-btn {
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

.analysis-btn {
  background-color: #52c41a;
  color: white;
}

.analysis-btn:hover {
  background-color: #73d13d;
}
</style>
