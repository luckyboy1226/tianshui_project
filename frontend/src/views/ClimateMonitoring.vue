<template>
  <div class="climate-monitoring">
    <div class="main-container">
      <!-- 左侧控制面板 -->
      <div class="left-panel">
        <!-- 标题栏 -->
        <div class="panel-header">
          <RouterLink to="/" class="back-home-link" title="返回主界面">
            <ArrowLeft class="back-home-icon" />
            <span>主界面</span>
          </RouterLink>
          <h1>气候环境监测统计</h1>
          <p>上传表格或气候栅格数据，系统将自动生成统计图表。</p>
        </div>
        
        <!-- 数据文件管理 -->
        <div class="section">
          <div class="section-header">
            <Files class="section-icon" />
            <span>数据文件管理</span>
          </div>
          <div class="section-content">
            <div class="file-upload-area">
              <input
                ref="fileInput"
                type="file"
                accept=".csv,.xlsx,.xls,.tif,.tiff,.zip"
                @change="handleFileSelect"
                style="display: none"
              />
              <div class="upload-zone" @click="fileInput?.click()">
                <div class="upload-icon">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="#1890ff" stroke-width="2" fill="none"/>
                    <path d="M14 2V8H20" stroke="#1890ff" stroke-width="2" fill="none"/>
                    <path d="M12 18V12" stroke="#1890ff" stroke-width="2" stroke-linecap="round"/>
                    <path d="M9 15L12 12L15 15" stroke="#1890ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
                <div class="upload-text">上传气候数据文件</div>
                <div class="upload-hint">拖放文件到此处或点击选择文件</div>
                <div class="upload-types">支持 .csv/.xlsx/.xls 表格，.tif/.tiff 气候栅格，ADF文件夹ZIP，或完整 Shapefile ZIP（含 .shp/.dbf/.shx，系统将自动读取属性表分析）</div>
              </div>
              <div class="file-status">
                {{ selectedFileLabel }}
              </div>
              <div v-if="fileCapabilities" class="capability-card">
                <div class="capability-title">文件识别结果</div>
                <div class="capability-mode">
                  {{ capabilityModeText }}
                </div>
                <div class="capability-tags">
                  <span
                    v-for="metric in climateMetricBadges"
                    :key="metric.key"
                    class="capability-tag"
                    :class="{ active: fileCapabilities.supported_metrics?.includes(metric.key), muted: !fileCapabilities.supported_metrics?.includes(metric.key) }"
                  >
                    {{ metric.label }}
                  </span>
                </div>
                <div v-if="fileCapabilities.reason" class="capability-reason" :class="{ warning: fileCapabilities.unsupported_for_climate }">
                  {{ fileCapabilities.reason }}
                </div>
                <div v-if="showMetricSelector" class="metric-selector">
                  <div class="metric-selector-label">请指定当前栅格变量</div>
                  <div v-if="selectedMetricLabel" class="metric-selector-current">
                    当前已选择：{{ selectedMetricLabel }}
                  </div>
                  <div class="metric-selector-options">
                    <button
                      v-for="metric in climateMetricBadges"
                      :key="`selector-${metric.key}`"
                      type="button"
                      class="metric-option"
                      :class="{ active: selectedMetric === metric.key }"
                      @click="selectedMetric = metric.key"
                    >
                      {{ metric.label }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 分析控制 -->
        <div class="section">
          <div class="section-header">
            <Search class="section-icon" />
            <span>数据分析控制</span>
          </div>
          <div class="section-content">
            <button
              @click="startAnalysis"
              class="analysis-btn"
              :disabled="!selectedFile || isAnalyzing || isClimateAnalysisBlocked"
              :class="{ 'disabled': !selectedFile || isAnalyzing || isClimateAnalysisBlocked }"
            >
              {{ isAnalyzing ? '分析中...' : isClimateAnalysisBlocked ? '当前文件不适用于本模块' : '开始分析' }}
            </button>
          </div>
        </div>

        <div class="section">
          <div class="section-header">
            <Files class="section-icon" />
            <span>最近结果</span>
          </div>
          <div class="section-content">
            <div class="history-toolbar">
              <span>{{ historyItems.length }} 条</span>
              <div class="history-toolbar-actions">
                <button
                  v-if="historyItems.length > 0"
                  type="button"
                  class="history-action-btn"
                  @click="clearHistoryItems"
                >
                  清空
                </button>
                <button
                  type="button"
                  class="history-action-btn primary"
                  @click="historyExpanded = !historyExpanded"
                >
                  {{ historyExpanded ? '收起' : '展开' }}
                </button>
              </div>
            </div>
            <div v-if="historyExpanded && historyItems.length > 0" class="history-list">
              <div
                v-for="item in historyItems"
                :key="item.id"
                class="history-item"
              >
                <button type="button" class="history-item-main" @click="restoreHistoryItem(item)">
                  <div class="history-item-title">{{ item.title }}</div>
                  <div class="history-item-subtitle">{{ item.subtitle }}</div>
                  <div class="history-item-time">{{ formatHistoryTime(item.timestamp) }}</div>
                </button>
                <button type="button" class="history-delete-btn" @click="deleteHistoryItem(item)">删除</button>
              </div>
            </div>
            <div v-else-if="historyExpanded" class="history-empty">
              这里会保留最近几次可直接查看的统计结果
            </div>
            <div v-else class="history-collapsed-tip">
              <span v-if="historyItems.length > 0">点击展开查看历史结果，不会再挤占左侧主操作区域</span>
              <span v-else>这里会保留最近几次可直接查看的统计结果</span>
            </div>
          </div>
        </div>

        <!-- 进度指示器 -->
        <div v-if="isAnalyzing" class="progress-section">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
          </div>
          <div class="progress-text">
            {{ analysisStatus === 'uploading' ? '上传中...' : '分析中...' }} {{ Math.round(uploadProgress) }}%
          </div>
        </div>

        <!-- 成功信息 -->
        <div v-if="successMessage" class="success-message">
          <CircleCheck class="success-icon" />
          <div class="success-content">
            <div class="success-title">操作成功</div>
            <div class="success-details">{{ successMessage }}</div>
            <div class="success-actions">
              <button @click="clearSuccess" class="dismiss-btn">关闭</button>
            </div>
          </div>
        </div>

        <!-- 错误信息 -->
        <div v-if="errorMessage" class="error-message">
          <CircleClose class="error-icon" />
          <div class="error-content">
            <div class="error-title">操作失败</div>
            <div class="error-details">{{ errorMessage }}</div>
            <div class="error-actions">
              <button @click="clearError" class="retry-btn">重试</button>
              <button @click="clearError" class="dismiss-btn">关闭</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧内容区域 -->
      <div class="right-panel">
        <!-- 无数据时的占位符 -->
        <div v-if="!hasData" class="placeholder">
          <div class="placeholder-text">请先上传数据并开始分析</div>
        </div>

        <!-- 有数据时显示分析结果 -->
        <div v-else class="analysis-results">
          <div v-if="analysisNotice" class="analysis-notice">
            <div class="analysis-notice-title">结果说明</div>
            <div class="analysis-notice-text">{{ analysisNotice }}</div>
          </div>

          <!-- 统计概览 -->
          <div class="stats-overview">
            <h3>统计概览</h3>
            <div class="stats-grid">
              <div v-for="stat in statistics" :key="stat.indicator" class="stat-item">
                <div class="stat-label">{{ stat.indicator }}</div>
                <div class="stat-values">
                  <div class="stat-value">
                    <span class="label">平均:</span>
                    <span class="value">{{ stat.average }}</span>
                  </div>
                  <div class="stat-value">
                    <span class="label">最大:</span>
                    <span class="value">{{ stat.max }}</span>
                  </div>
                  <div class="stat-value">
                    <span class="label">最小:</span>
                    <span class="value">{{ stat.min }}</span>
                  </div>
                  <div class="stat-value">
                    <span class="label">标准差:</span>
                    <span class="value">{{ stat.stdDev }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 图表区域 -->
          <div class="charts-section">
            <h3>数据可视化</h3>
            <div class="charts-grid">
              <div class="chart-container">
                <h4>温度趋势图</h4>
                <canvas ref="temperatureChart" width="400" height="200"></canvas>
              </div>
              <div class="chart-container">
                <h4>降水量柱状图</h4>
                <canvas ref="precipitationChart" width="400" height="200"></canvas>
              </div>
              <div class="chart-container">
                <h4>湿度面积图</h4>
                <canvas ref="humidityChart" width="400" height="200"></canvas>
              </div>
              <div class="chart-container">
                <h4>风速雷达图</h4>
                <canvas ref="windSpeedChart" width="400" height="200"></canvas>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { ArrowLeft, CircleCheck, CircleClose, Files, Search } from '@element-plus/icons-vue'
import { climateMonitoringService } from '../services/api.js'
import { clearResultHistory, formatHistoryTime, loadResultHistory, removeResultHistory, saveResultHistory } from '../utils/resultHistory.js'

// 响应式数据
const fileInput = ref(null)
const selectedFile = ref(null)
const restoredFileName = ref('')
const isAnalyzing = ref(false)
const uploadProgress = ref(0)
const analysisStatus = ref('')
const analysisTaskId = ref(null)
const errorMessage = ref('')
const successMessage = ref('')
const hasData = ref(false)
const statistics = ref([])
const analysisNotice = ref('')
const fileCapabilities = ref(null)
const selectedMetric = ref('')
const historyItems = ref([])
const historyExpanded = ref(false)
const chartData = ref({
  temperature: [],
  precipitation: [],
  humidity: [],
  windSpeed: []
})
const chartYearLabels = ref([])

// 图表ref
const temperatureChart = ref(null)
const precipitationChart = ref(null)
const humidityChart = ref(null)
const windSpeedChart = ref(null)

// 状态轮询间隔
let statusCheckInterval = null
const HISTORY_KEY = 'climate_monitoring'
const ACTIVE_TASK_STORAGE_KEY = 'climate_monitoring_active_task'

const saveActiveTask = (taskId, fileName, metric) => {
  localStorage.setItem(ACTIVE_TASK_STORAGE_KEY, JSON.stringify({
    taskId,
    fileName,
    metric,
    timestamp: Date.now()
  }))
}

const clearActiveTask = () => {
  localStorage.removeItem(ACTIVE_TASK_STORAGE_KEY)
}

const restoreActiveTask = () => {
  try {
    const activeTask = JSON.parse(localStorage.getItem(ACTIVE_TASK_STORAGE_KEY) || 'null')
    if (!activeTask?.taskId) {
      return
    }

    analysisTaskId.value = activeTask.taskId
    restoredFileName.value = activeTask.fileName || ''
    selectedMetric.value = activeTask.metric || ''
    analysisStatus.value = 'pending'
    isAnalyzing.value = true
    uploadProgress.value = 0
    successMessage.value = '已恢复后台气候分析任务，正在查询进度。'
    startStatusPolling()
  } catch (error) {
    console.warn('恢复气候分析任务失败:', error)
    clearActiveTask()
  }
}

// 文件选择处理
const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    // 验证文件
    const validationResult = validateClimateDataFile(file)
    if (validationResult.isValid) {
      selectedFile.value = file
      restoredFileName.value = ''
      fileCapabilities.value = null
      selectedMetric.value = ''
      errorMessage.value = ''
      clearAnalysisState()
      successMessage.value = `文件 "${file.name}" 选择成功，可以开始分析`
      // 3秒后自动清除成功消息
      setTimeout(() => {
        successMessage.value = ''
      }, 3000)
    } else {
      errorMessage.value = validationResult.errorMessage
      selectedFile.value = null
      // 清空文件输入
      if (fileInput.value) {
        fileInput.value.value = ''
      }
    }
  }
}

// 验证气候数据文件
const validateClimateDataFile = (file) => {
  // 1. 检查文件是否存在
  if (!file) {
    return {
      isValid: false,
      errorMessage: '请选择一个文件'
    }
  }

  // 2. 检查文件大小（栅格数据可能较大，后端会分块统计）
  const maxSize = 20 * 1024 * 1024 * 1024 // 20GB
  if (file.size > maxSize) {
    return {
      isValid: false,
      errorMessage: '文件大小不能超过20GB；更大的数据建议先裁剪或使用后台分片上传'
    }
  }

  // 3. 检查文件类型
  const allowedTypes = ['.csv', '.xlsx', '.xls', '.tif', '.tiff', '.zip']
  const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
  const shapefileSidecars = ['.shp', '.dbf', '.shx', '.prj', '.cpg', '.sbn', '.sbx']
  if (shapefileSidecars.includes(fileExtension)) {
    return {
      isValid: false,
      errorMessage: '请不要单独上传 .shp/.dbf/.shx 等组件文件；请将完整 Shapefile 打包为一个 ZIP 后上传，系统会自动读取属性表进行气候统计分析。'
    }
  }
  if (!allowedTypes.includes(fileExtension)) {
    return {
      isValid: false,
      errorMessage: '只支持 CSV、Excel、GeoTIFF、ADF 文件夹 ZIP，或完整 Shapefile ZIP'
    }
  }

  // 4. 检查文件名
  if (!file.name || file.name.trim() === '') {
    return {
      isValid: false,
      errorMessage: '文件名不能为空'
    }
  }

  // 5. 检查文件是否为空
  if (file.size === 0) {
    return {
      isValid: false,
      errorMessage: '文件不能为空'
    }
  }

  return {
    isValid: true,
    errorMessage: ''
  }
}

const climateMetricBadges = [
  { key: 'temperature', label: '温度' },
  { key: 'precipitation', label: '降水' },
  { key: 'humidity', label: '湿度' },
  { key: 'wind_speed', label: '风速' }
]

const isClimateAnalysisBlocked = computed(() => !!fileCapabilities.value?.unsupported_for_climate)
const showMetricSelector = computed(() => !!fileCapabilities.value?.manual_selection_required)
const selectedFileLabel = computed(() => {
  if (selectedFile.value?.name) {
    return selectedFile.value.name
  }
  if (restoredFileName.value) {
    return `历史结果: ${restoredFileName.value}`
  }
  return '未选择文件'
})
const selectedMetricLabel = computed(() => {
  const current = climateMetricBadges.find(metric => metric.key === selectedMetric.value)
  return current ? current.label : ''
})

const capabilityModeText = computed(() => {
  if (!fileCapabilities.value) return ''
  if (fileCapabilities.value.unsupported_for_climate) {
    if (fileCapabilities.value.source_type === 'unknown_zip') {
      return '未识别的 ZIP 数据'
    }
    if (fileCapabilities.value.detected_mode === 'vector_attribute_table') {
      return 'Shapefile 属性表'
    }
    return '检测为遥感指数栅格'
  }
  if (fileCapabilities.value.manual_selection_required) {
    return '单变量气候栅格，待手动指定变量'
  }
  if (fileCapabilities.value.detected_mode === 'vector_attribute_table') {
    return 'Shapefile 属性表分析'
  }
  return fileCapabilities.value.detected_mode === 'single_metric_raster' ? '单变量气候栅格' : '综合气候表格'
})

const removeFile = () => {
  selectedFile.value = null
  fileInput.value.value = ''
  restoredFileName.value = ''
  selectedMetric.value = ''
  fileCapabilities.value = null
  clearAnalysisState()
}

const clearAnalysisState = () => {
  clearActiveTask()
  hasData.value = false
  analysisNotice.value = ''
  statistics.value = []
  analysisTaskId.value = null
  chartData.value = {
    temperature: [],
    precipitation: [],
    humidity: [],
    windSpeed: []
  }
  chartYearLabels.value = []
}

const buildHistoryPayload = () => ({
  fileName: selectedFile.value?.name || restoredFileName.value || '气候统计结果',
  fileCapabilities: fileCapabilities.value,
  selectedMetric: selectedMetric.value,
  statistics: statistics.value,
  analysisNotice: analysisNotice.value,
  chartData: chartData.value,
  chartYearLabels: chartYearLabels.value
})

const persistCurrentResult = () => {
  if (statistics.value.length === 0) {
    return
  }

  const payload = buildHistoryPayload()
  historyItems.value = saveResultHistory(HISTORY_KEY, {
    id: `${payload.fileName}_${Date.now()}`,
    title: payload.fileName,
    subtitle: `${statistics.value.length} 组统计结果`,
    timestamp: Date.now(),
    payload
  })
}

const restoreHistoryItem = (item) => {
  const payload = item?.payload
  if (!payload?.statistics || !payload?.chartData) {
    errorMessage.value = '该历史结果已失效，请重新分析'
    return
  }

  selectedFile.value = null
  restoredFileName.value = payload.fileName || item.title || ''
  fileCapabilities.value = payload.fileCapabilities || null
  selectedMetric.value = payload.selectedMetric || ''
  statistics.value = Array.isArray(payload.statistics) ? payload.statistics : []
  analysisNotice.value = payload.analysisNotice || ''
  chartData.value = {
    temperature: Array.isArray(payload.chartData.temperature) ? payload.chartData.temperature : [],
    precipitation: Array.isArray(payload.chartData.precipitation) ? payload.chartData.precipitation : [],
    humidity: Array.isArray(payload.chartData.humidity) ? payload.chartData.humidity : [],
    windSpeed: Array.isArray(payload.chartData.windSpeed) ? payload.chartData.windSpeed : []
  }
  chartYearLabels.value = Array.isArray(payload.chartYearLabels) ? payload.chartYearLabels : []
  hasData.value = true
  errorMessage.value = ''
  successMessage.value = '已恢复历史统计结果'

  setTimeout(() => {
    generateCharts()
  }, 100)
}

const deleteHistoryItem = (item) => {
  historyItems.value = removeResultHistory(HISTORY_KEY, item.id)
  successMessage.value = '历史记录已删除'
}

const clearHistoryItems = () => {
  if (historyItems.value.length === 0) {
    return
  }

  if (!window.confirm('确定要清空当前所有历史记录吗？')) {
    return
  }

  clearResultHistory(HISTORY_KEY)
  historyItems.value = []
  successMessage.value = '历史记录已清空'
}

// 清除错误信息
const clearError = () => {
  errorMessage.value = ''
}

// 清除成功信息
const clearSuccess = () => {
  successMessage.value = ''
}

const startAnalysis = async () => {
  // 1. 检查是否选择了文件
  if (!selectedFile.value) {
    errorMessage.value = '请先选择一个气候数据文件'
    return
  }

  // 2. 再次验证文件（双重检查）
  const validationResult = validateClimateDataFile(selectedFile.value)
  if (!validationResult.isValid) {
    errorMessage.value = validationResult.errorMessage
    return
  }

  // 3. 检查是否正在分析中
  if (isAnalyzing.value) {
    errorMessage.value = '正在分析中，请等待完成'
    return
  }

  if (isClimateAnalysisBlocked.value) {
    errorMessage.value = fileCapabilities.value?.reason || '当前文件不适用于气候环境监测统计，请改用遥感生态指数分析模块'
    return
  }

  if (showMetricSelector.value && !selectedMetric.value) {
    errorMessage.value = '请先指定当前栅格是温度、降水、湿度还是风速'
    return
  }
  
  try {
    isAnalyzing.value = true
    errorMessage.value = ''
    uploadProgress.value = 0
    analysisStatus.value = 'uploading'
    const chosenMetric = selectedMetric.value
    
    // 调用真实的后端API
    try {
      // 1. 上传文件
      console.log('开始上传文件:', selectedFile.value.name)
      
      // 模拟上传进度
      const uploadProgressInterval = setInterval(() => {
        if (uploadProgress.value < 90) {
          uploadProgress.value += Math.random() * 10
        }
      }, 200)
      
      const uploadResponse = await climateMonitoringService.uploadClimateData(selectedFile.value, {
        name: selectedFile.value.name,
        description: '气候监测数据分析'
      })
      
      clearInterval(uploadProgressInterval)
      uploadProgress.value = 100
      
      console.log('上传响应:', uploadResponse)
      
      // 验证上传响应
      if (!uploadResponse) {
        throw new Error('上传响应为空，请检查网络连接')
      }
      
      if (uploadResponse.success) {
        const fileId = uploadResponse.file_id
        fileCapabilities.value = uploadResponse.capabilities || null
        if (uploadResponse.capabilities?.inferred_metric) {
          selectedMetric.value = uploadResponse.capabilities.inferred_metric
        } else if (chosenMetric) {
          selectedMetric.value = chosenMetric
        }

        if (uploadResponse.capabilities?.unsupported_for_climate) {
          throw new Error(uploadResponse.capabilities.reason || '当前文件属于遥感指数栅格，请改用遥感生态指数分析模块')
        }
        
        // 验证文件ID
        if (!fileId) {
          throw new Error('上传成功但未返回文件ID')
        }
        
        analysisStatus.value = 'processing'
        uploadProgress.value = 0
        
        // 2. 开始分析
        console.log('开始分析，文件ID:', fileId)
        
        // 模拟分析进度
        const analysisProgressInterval = setInterval(() => {
          if (uploadProgress.value < 95) {
            uploadProgress.value += Math.random() * 5
          }
        }, 300)
        
        const analysisType = selectedMetric.value || chosenMetric || 'comprehensive'
        const analysisResponse = await climateMonitoringService.analyzeClimateData(fileId, analysisType)
        
        clearInterval(analysisProgressInterval)
        
        console.log('分析响应:', analysisResponse)
        
        // 验证分析响应
        if (!analysisResponse) {
          throw new Error('分析响应为空，请检查后端服务')
        }
        
        if (analysisResponse.success) {
          const taskId = analysisResponse.task_id
          
          // 验证任务ID
          if (!taskId) {
            throw new Error('分析启动成功但未返回任务ID')
          }
          
          analysisTaskId.value = taskId
          saveActiveTask(taskId, selectedFile.value?.name || '', analysisType)
          
          // 3. 开始轮询分析状态
          startStatusPolling()
        } else {
          throw new Error(analysisResponse.message || '分析启动失败')
        }
      } else {
        throw new Error(uploadResponse.message || '文件上传失败')
      }
    } catch (apiError) {
      console.error('API调用失败:', apiError)
      uploadProgress.value = 0
      
      // 根据错误类型提供更具体的错误信息
      let errorMsg = 'API调用失败'
      if (apiError.message) {
        errorMsg = apiError.message
      } else if (apiError.response) {
        errorMsg = `服务器错误: ${apiError.response.status}`
      } else if (apiError.request) {
        errorMsg = '网络连接失败，请检查后端服务是否正常运行'
      }
      
      errorMessage.value = errorMsg
      isAnalyzing.value = false
    }
  } catch (error) {
    console.error('分析过程中出错:', error)
    errorMessage.value = error.message || '分析过程中出现错误'
    isAnalyzing.value = false
    uploadProgress.value = 0
  }
}

// 验证状态响应数据
const validateStatusResponse = (response) => {
  if (!response || typeof response !== 'object') {
    throw new Error('状态响应格式无效')
  }
  
  if (!response.status) {
    throw new Error('状态响应缺少status字段')
  }
  
  const validStatuses = ['pending', 'processing', 'completed', 'failed']
  if (!validStatuses.includes(response.status)) {
    throw new Error(`无效的状态值: ${response.status}`)
  }
  
  // 验证进度值
  if (response.progress !== undefined && response.progress !== null) {
    const progress = Number(response.progress)
    if (isNaN(progress) || progress < 0 || progress > 100) {
      console.warn('进度值无效，使用默认值0')
      response.progress = 0
    }
  }
  
  return true
}

// 开始轮询分析状态
const startStatusPolling = () => {
  cleanup()
  // 验证任务ID
  if (!analysisTaskId.value) {
    console.error('任务ID不存在，无法开始状态轮询')
    errorMessage.value = '任务ID不存在'
    isAnalyzing.value = false
    return
  }
  
  let pollCount = 0
  const maxPolls = 150 // 最多轮询5分钟 (150 * 2秒)
  
  statusCheckInterval = setInterval(async () => {
    try {
      pollCount++
      
      // 防止无限轮询
      if (pollCount > maxPolls) {
        console.warn('状态轮询超时，停止轮询')
        clearInterval(statusCheckInterval)
        errorMessage.value = '分析超时，请重试'
        isAnalyzing.value = false
        uploadProgress.value = 0
        return
      }
      
      const statusResponse = await climateMonitoringService.getAnalysisStatus(analysisTaskId.value)
      
      if (!statusResponse) {
        throw new Error('无法获取状态响应')
      }
      
      // 验证状态响应
      validateStatusResponse(statusResponse)
      
      analysisStatus.value = statusResponse.status
      
              if (statusResponse.status === 'completed') {
          // 分析完成，获取结果
          uploadProgress.value = 100
          const resultsLoaded = await loadAnalysisResults()
          clearInterval(statusCheckInterval)
          statusCheckInterval = null
          isAnalyzing.value = false
          hasData.value = resultsLoaded
          if (!resultsLoaded) {
            return
          }
          clearActiveTask()
          successMessage.value = '气候数据分析完成！'
          // 5秒后自动清除成功消息
          setTimeout(() => {
            successMessage.value = ''
          }, 5000)
      } else if (statusResponse.status === 'failed') {
        // 分析失败
        errorMessage.value = statusResponse.error_message || '分析失败'
        clearInterval(statusCheckInterval)
        statusCheckInterval = null
        isAnalyzing.value = false
        uploadProgress.value = 0
        clearActiveTask()
      } else if (statusResponse.status === 'processing') {
        // 更新进度
        const progress = Number(statusResponse.progress) || 0
        if (progress > 0) {
          uploadProgress.value = Math.max(0, Math.min(100, progress)) // 确保进度在0-100之间
        } else {
          // 如果后端没有返回进度，使用模拟进度
          if (uploadProgress.value < 95) {
            uploadProgress.value += Math.random() * 3
          }
        }
      } else if (statusResponse.status === 'pending') {
        // 任务等待中，缓慢增加进度
        if (uploadProgress.value < 20) {
          uploadProgress.value += Math.random() * 2
        }
      }
      
    } catch (error) {
      console.error('状态检查失败:', error)
      clearInterval(statusCheckInterval)
      statusCheckInterval = null
      isAnalyzing.value = false
      uploadProgress.value = 0
      errorMessage.value = `状态检查失败: ${error.message}`
    }
  }, 2000) // 每2秒检查一次
}

// 验证数据完整性
const validateAnalysisData = (data) => {
  if (!data || typeof data !== 'object') {
    throw new Error('分析数据格式无效')
  }

  // 检查图表数据
  if (data.chart_data && typeof data.chart_data === 'object') {
    const chartFields = ['temperature', 'precipitation', 'humidity', 'wind_speed']
    chartFields.forEach(field => {
      if (!Array.isArray(data.chart_data[field])) {
        console.warn(`图表数据字段 ${field} 不是数组`)
        data.chart_data[field] = []
      }
    })
  }
  
  return true
}

// 安全获取数值
const safeGetValue = (value, defaultValue = '--', precision = 1) => {
  if (value === null || value === undefined || isNaN(value)) {
    return defaultValue
  }
  return Number(value).toFixed(precision)
}

const climateMetricDefinitions = [
  { key: 'temperature', label: '温度(°C)' },
  { key: 'precipitation', label: '降水量(mm)' },
  { key: 'humidity', label: '湿度(%)' },
  { key: 'wind_speed', label: '风速(m/s)' }
]

const buildStatisticItems = (data) => {
  return climateMetricDefinitions
    .map(metric => {
      const avgKey = `${metric.key}_avg`
      const maxKey = `${metric.key}_max`
      const minKey = `${metric.key}_min`
      const stdKey = `${metric.key}_std`
      const hasMetric = [avgKey, maxKey, minKey, stdKey].some(key => data[key] !== null && data[key] !== undefined && !isNaN(data[key]))

      if (!hasMetric) {
        return null
      }

      return {
        indicator: metric.label,
        average: safeGetValue(data[avgKey]),
        max: safeGetValue(data[maxKey]),
        min: safeGetValue(data[minKey]),
        stdDev: safeGetValue(data[stdKey])
      }
    })
    .filter(Boolean)
}

// 加载分析结果
const loadAnalysisResults = async () => {
  try {
    // 验证任务ID
    if (!analysisTaskId.value) {
      throw new Error('任务ID不存在，无法加载分析结果')
    }
    
    const resultsResponse = await climateMonitoringService.getAnalysisResults(analysisTaskId.value)
    
    if (!resultsResponse) {
      throw new Error('无法获取分析结果响应')
    }
    
    if (!resultsResponse.success) {
      throw new Error(resultsResponse.message || '分析结果获取失败')
    }
    
    const data = resultsResponse.data
    if (!data) {
      throw new Error('分析结果数据为空')
    }
    
    // 验证数据完整性
    validateAnalysisData(data)
    
    statistics.value = buildStatisticItems(data)

    const rasterMeta = data.chart_data?.raster_metadata
    if (rasterMeta?.source_type === 'single_metric_raster') {
      const metricMap = {
        temperature: '温度',
        precipitation: '降水量',
        humidity: '湿度',
        wind_speed: '风速'
      }
      analysisNotice.value = `当前上传的是单变量气候栅格，系统识别并计算了“${metricMap[rasterMeta.inferred_metric] || rasterMeta.inferred_metric}”指标；其余指标未包含在该文件中，因此不会显示为计算结果。`
    } else if (data.chart_data?.vector_metadata?.source_type === 'vector_attribute_table') {
      const metricMap = {
        temperature: '温度',
        precipitation: '降水量',
        humidity: '湿度',
        wind_speed: '风速'
      }
      const labels = (data.chart_data.vector_metadata.available_metrics || [])
        .map(key => metricMap[key] || key)
        .join('、')
      const yearRange = data.chart_data.vector_metadata.year_range
      const yearText = Array.isArray(yearRange) && yearRange.length === 2
        ? `，年份范围 ${yearRange[0]}-${yearRange[1]}`
        : ''
      const layoutText = data.chart_data.vector_metadata.table_layout === 'year_wide'
        ? '年份字段宽表'
        : '属性表'
      analysisNotice.value = `当前上传的是 Shapefile ${layoutText}，系统已自动识别并统计其中的 ${labels || '气候'} 数据${yearText}。`
    } else {
      analysisNotice.value = ''
    }
    
    // 更新图表数据 - 添加验证
    if (data.chart_data && typeof data.chart_data === 'object') {
      chartData.value = {
        temperature: Array.isArray(data.chart_data.temperature) ? data.chart_data.temperature : [],
        precipitation: Array.isArray(data.chart_data.precipitation) ? data.chart_data.precipitation : [],
        humidity: Array.isArray(data.chart_data.humidity) ? data.chart_data.humidity : [],
        windSpeed: Array.isArray(data.chart_data.wind_speed) ? data.chart_data.wind_speed : []
      }
      chartYearLabels.value = Array.isArray(data.chart_data.vector_metadata?.year_labels)
        ? data.chart_data.vector_metadata.year_labels
        : []
    } else {
      console.warn('图表数据不存在或格式无效，使用空数据')
      chartData.value = {
        temperature: [],
        precipitation: [],
        humidity: [],
        windSpeed: []
      }
      chartYearLabels.value = []
    }

    if (statistics.value.length === 0) {
      throw new Error('当前文件未解析出可展示的气候指标')
    }

    persistCurrentResult()
    
    // 生成图表
    setTimeout(() => {
      generateCharts()
    }, 100)
    return true
    
  } catch (error) {
    console.error('加载分析结果失败:', error)
    errorMessage.value = error.message || '加载分析结果失败'
    return false
  }
}

// 生成所有图表
const generateCharts = () => {
  console.log('开始生成图表')
  drawTemperatureChart()
  drawPrecipitationChart()
  drawHumidityChart()
  drawWindSpeedChart()
}

const getTimeAxisLabel = (index) => {
  const label = chartYearLabels.value[index]
  return label !== undefined && label !== null ? String(label) : String(index + 1)
}

// 清理函数
const cleanup = () => {
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval)
    statusCheckInterval = null
  }
}

// 组件挂载
onMounted(() => {
  console.log('气候监测组件已挂载')
  historyItems.value = loadResultHistory(HISTORY_KEY)
  restoreActiveTask()
})

// 组件卸载时清理
onUnmounted(() => {
  cleanup()
})

const drawTemperatureChart = () => {
  const canvas = temperatureChart.value
  console.log('绘制温度图表, canvas:', canvas)
  if (!canvas) {
    console.log('温度图表canvas未找到')
    return
  }
  
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // 使用实际数据
  const data = chartData.value.temperature
  if (!data || data.length === 0) {
    console.log('没有温度数据可绘制')
    return
  }
  
  const maxValue = Math.max(...data)
  const minValue = Math.min(...data)
  const range = maxValue - minValue || 1
  
  // 设置边距 - 增加左边距和底部边距
  const margin = { top: 20, right: 20, bottom: 60, left: 80 }
  const chartWidth = canvas.width - margin.left - margin.right
  const chartHeight = canvas.height - margin.top - margin.bottom
  
  // 绘制背景
  ctx.fillStyle = '#fafafa'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  
  // 绘制网格
  ctx.strokeStyle = '#e0e0e0'
  ctx.lineWidth = 1
  ctx.setLineDash([2, 2])
  
  // 水平网格线
  for (let i = 0; i <= 10; i++) {
    const y = margin.top + (chartHeight / 10) * i
    ctx.beginPath()
    ctx.moveTo(margin.left, y)
    ctx.lineTo(canvas.width - margin.right, y)
    ctx.stroke()
  }
  
  // 垂直网格线
  for (let i = 0; i <= 10; i++) {
    const x = margin.left + (chartWidth / 10) * i
    ctx.beginPath()
    ctx.moveTo(x, margin.top)
    ctx.lineTo(x, canvas.height - margin.bottom)
    ctx.stroke()
  }
  
  ctx.setLineDash([])
  
  // 绘制坐标轴
  ctx.strokeStyle = '#333333'
  ctx.lineWidth = 2
  
  // X轴
  ctx.beginPath()
  ctx.moveTo(margin.left, canvas.height - margin.bottom)
  ctx.lineTo(canvas.width - margin.right, canvas.height - margin.bottom)
  ctx.stroke()
  
  // Y轴
  ctx.beginPath()
  ctx.moveTo(margin.left, margin.top)
  ctx.lineTo(margin.left, canvas.height - margin.bottom)
  ctx.stroke()
  
  // 绘制Y轴刻度标签
  ctx.fillStyle = '#666666'
  ctx.font = '11px Arial'
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  
  for (let i = 0; i <= 10; i++) {
    const value = minValue + (range / 10) * (10 - i)
    const y = margin.top + (chartHeight / 10) * i
    ctx.fillText(value.toFixed(1), margin.left - 20, y)
  }
  
  // 绘制X轴刻度标签
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  
  const step = Math.max(1, Math.floor(data.length / 8))
  for (let i = 0; i < data.length; i += step) {
    const x = margin.left + (chartWidth / (data.length - 1)) * i
    ctx.fillText(getTimeAxisLabel(i), x, canvas.height - margin.bottom + 20)
  }
  
  // 绘制轴标签
  ctx.fillStyle = '#333333'
  ctx.font = 'bold 12px Arial'
  ctx.textAlign = 'center'
  
  // Y轴标签 - 垂直显示，放在刻度左侧
  ctx.save()
  ctx.translate(15, margin.top + chartHeight / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.fillText('温度(°C)', 0, 0)
  ctx.restore()
  
  // X轴标签 - 确保完全显示
  ctx.fillText('时间序列', canvas.width / 2, canvas.height - 15)
  
  // 绘制数据线
  ctx.strokeStyle = '#e74c3c'
  ctx.lineWidth = 3
  ctx.beginPath()
  
  data.forEach((value, index) => {
    const x = margin.left + (chartWidth / (data.length - 1)) * index
    const y = margin.top + chartHeight - ((value - minValue) / range) * chartHeight
    
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.stroke()
  
  // 绘制数据点
  ctx.fillStyle = '#e74c3c'
  data.forEach((value, index) => {
    const x = margin.left + (chartWidth / (data.length - 1)) * index
    const y = margin.top + chartHeight - ((value - minValue) / range) * chartHeight
    
    ctx.beginPath()
    ctx.arc(x, y, 4, 0, 2 * Math.PI)
    ctx.fill()
  })
}

const drawPrecipitationChart = () => {
  const canvas = precipitationChart.value
  if (!canvas) return
  
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // 使用实际数据
  const data = chartData.value.precipitation
  if (!data || data.length === 0) {
    console.log('没有降水量数据可绘制')
    return
  }
  
  const maxValue = Math.max(...data)
  const minValue = Math.min(...data)
  const range = maxValue - minValue || 1
  
  // 设置边距 - 增加左边距和底部边距
  const margin = { top: 20, right: 20, bottom: 60, left: 80 }
  const chartWidth = canvas.width - margin.left - margin.right
  const chartHeight = canvas.height - margin.top - margin.bottom
  
  // 绘制背景
  ctx.fillStyle = '#fafafa'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  
  // 绘制网格
  ctx.strokeStyle = '#e0e0e0'
  ctx.lineWidth = 1
  ctx.setLineDash([2, 2])
  
  // 水平网格线
  for (let i = 0; i <= 10; i++) {
    const y = margin.top + (chartHeight / 10) * i
    ctx.beginPath()
    ctx.moveTo(margin.left, y)
    ctx.lineTo(canvas.width - margin.right, y)
    ctx.stroke()
  }
  
  // 垂直网格线
  for (let i = 0; i <= 10; i++) {
    const x = margin.left + (chartWidth / 10) * i
    ctx.beginPath()
    ctx.moveTo(x, margin.top)
    ctx.lineTo(x, canvas.height - margin.bottom)
    ctx.stroke()
  }
  
  ctx.setLineDash([])
  
  // 绘制坐标轴
  ctx.strokeStyle = '#333333'
  ctx.lineWidth = 2
  
  // X轴
  ctx.beginPath()
  ctx.moveTo(margin.left, canvas.height - margin.bottom)
  ctx.lineTo(canvas.width - margin.right, canvas.height - margin.bottom)
  ctx.stroke()
  
  // Y轴
  ctx.beginPath()
  ctx.moveTo(margin.left, margin.top)
  ctx.lineTo(margin.left, canvas.height - margin.bottom)
  ctx.stroke()
  
  // 绘制Y轴刻度标签
  ctx.fillStyle = '#666666'
  ctx.font = '11px Arial'
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  
  for (let i = 0; i <= 10; i++) {
    const value = minValue + (range / 10) * (10 - i)
    const y = margin.top + (chartHeight / 10) * i
    ctx.fillText(value.toFixed(1), margin.left - 20, y)
  }
  
  // 绘制X轴刻度标签
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  
  const step = Math.max(1, Math.floor(data.length / 8))
  for (let i = 0; i < data.length; i += step) {
    const x = margin.left + (chartWidth / data.length) * (i + 0.5)
    ctx.fillText(getTimeAxisLabel(i), x, canvas.height - margin.bottom + 20)
  }
  
  // 绘制轴标签
  ctx.fillStyle = '#333333'
  ctx.font = 'bold 12px Arial'
  ctx.textAlign = 'center'
  
  // Y轴标签 - 垂直显示，放在刻度左侧
  ctx.save()
  ctx.translate(15, margin.top + chartHeight / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.fillText('降水量(mm)', 0, 0)
  ctx.restore()
  
  // X轴标签 - 确保完全显示
  ctx.fillText('时间序列', canvas.width / 2, canvas.height - 15)
  
  // 绘制柱状图
  const barWidth = chartWidth / data.length
  ctx.fillStyle = '#2ecc71'
  
  data.forEach((value, index) => {
    const barHeight = ((value - minValue) / range) * chartHeight
    const x = margin.left + (chartWidth / data.length) * index
    const y = margin.top + chartHeight - barHeight
    
    ctx.fillRect(x, y, barWidth - 2, barHeight)
  })
}

const drawHumidityChart = () => {
  const canvas = humidityChart.value
  if (!canvas) return
  
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // 使用实际数据
  const data = chartData.value.humidity
  if (!data || data.length === 0) {
    console.log('没有湿度数据可绘制')
    return
  }
  
  const maxValue = Math.max(...data)
  const minValue = Math.min(...data)
  const range = maxValue - minValue || 1
  
  // 设置边距 - 增加左边距和底部边距
  const margin = { top: 20, right: 20, bottom: 60, left: 80 }
  const chartWidth = canvas.width - margin.left - margin.right
  const chartHeight = canvas.height - margin.top - margin.bottom
  
  // 绘制背景
  ctx.fillStyle = '#fafafa'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  
  // 绘制网格
  ctx.strokeStyle = '#e0e0e0'
  ctx.lineWidth = 1
  ctx.setLineDash([2, 2])
  
  // 水平网格线
  for (let i = 0; i <= 10; i++) {
    const y = margin.top + (chartHeight / 10) * i
    ctx.beginPath()
    ctx.moveTo(margin.left, y)
    ctx.lineTo(canvas.width - margin.right, y)
    ctx.stroke()
  }
  
  // 垂直网格线
  for (let i = 0; i <= 10; i++) {
    const x = margin.left + (chartWidth / 10) * i
    ctx.beginPath()
    ctx.moveTo(x, margin.top)
    ctx.lineTo(x, canvas.height - margin.bottom)
    ctx.stroke()
  }
  
  ctx.setLineDash([])
  
  // 绘制坐标轴
  ctx.strokeStyle = '#333333'
  ctx.lineWidth = 2
  
  // X轴
  ctx.beginPath()
  ctx.moveTo(margin.left, canvas.height - margin.bottom)
  ctx.lineTo(canvas.width - margin.right, canvas.height - margin.bottom)
  ctx.stroke()
  
  // Y轴
  ctx.beginPath()
  ctx.moveTo(margin.left, margin.top)
  ctx.lineTo(margin.left, canvas.height - margin.bottom)
  ctx.stroke()
  
  // 绘制Y轴刻度标签
  ctx.fillStyle = '#666666'
  ctx.font = '11px Arial'
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  
  for (let i = 0; i <= 10; i++) {
    const value = minValue + (range / 10) * (10 - i)
    const y = margin.top + (chartHeight / 10) * i
    ctx.fillText(value.toFixed(1), margin.left - 20, y)
  }
  
  // 绘制X轴刻度标签
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  
  const step = Math.max(1, Math.floor(data.length / 8))
  for (let i = 0; i < data.length; i += step) {
    const x = margin.left + (chartWidth / (data.length - 1)) * i
    ctx.fillText(getTimeAxisLabel(i), x, canvas.height - margin.bottom + 20)
  }
  
  // 绘制轴标签
  ctx.fillStyle = '#333333'
  ctx.font = 'bold 12px Arial'
  ctx.textAlign = 'center'
  
  // Y轴标签 - 垂直显示，放在刻度左侧
  ctx.save()
  ctx.translate(15, margin.top + chartHeight / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.fillText('湿度(%)', 0, 0)
  ctx.restore()
  
  // X轴标签 - 确保完全显示
  ctx.fillText('时间序列', canvas.width / 2, canvas.height - 15)
  
  // 绘制面积图
  ctx.fillStyle = 'rgba(52, 152, 219, 0.3)'
  ctx.strokeStyle = '#3498db'
  ctx.lineWidth = 2
  
  ctx.beginPath()
  ctx.moveTo(margin.left, canvas.height - margin.bottom)
  
  data.forEach((value, index) => {
    const x = margin.left + (chartWidth / (data.length - 1)) * index
    const y = margin.top + chartHeight - ((value - minValue) / range) * chartHeight
    ctx.lineTo(x, y)
  })
  
  ctx.lineTo(canvas.width - margin.right, canvas.height - margin.bottom)
  ctx.closePath()
  ctx.fill()
  ctx.stroke()
}

const drawWindSpeedChart = () => {
  const canvas = windSpeedChart.value
  if (!canvas) return
  
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // 使用实际数据
  const data = chartData.value.windSpeed
  if (!data || data.length === 0) {
    console.log('没有风速数据可绘制')
    return
  }
  
  const maxValue = Math.max(...data)
  const minValue = Math.min(...data)
  const range = maxValue - minValue || 1
  
  // 雷达图居中显示，使用较小的边距
  const margin = { top: 40, right: 40, bottom: 40, left: 40 }
  const chartWidth = canvas.width - margin.left - margin.right
  const chartHeight = canvas.height - margin.top - margin.bottom
  
  // 绘制背景
  ctx.fillStyle = '#fafafa'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  
  // 计算中心点和半径 - 完全居中
  const centerX = canvas.width / 2
  const centerY = canvas.height / 2
  const radius = Math.min(chartWidth, chartHeight) / 2 - 30
  
  // 绘制网格圆
  ctx.strokeStyle = '#e0e0e0'
  ctx.lineWidth = 1
  ctx.setLineDash([2, 2])
  
  for (let i = 1; i <= 5; i++) {
    const r = (radius / 5) * i
    ctx.beginPath()
    ctx.arc(centerX, centerY, r, 0, 2 * Math.PI)
    ctx.stroke()
  }
  
  // 绘制径向线
  for (let i = 0; i < 8; i++) {
    const angle = (i / 8) * 2 * Math.PI
    const x = centerX + Math.cos(angle) * radius
    const y = centerY + Math.sin(angle) * radius
    
    ctx.beginPath()
    ctx.moveTo(centerX, centerY)
    ctx.lineTo(x, y)
    ctx.stroke()
  }
  
  ctx.setLineDash([])
  
  // 绘制坐标轴标签
  ctx.fillStyle = '#666666'
  ctx.font = '11px Arial'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  
  // 绘制刻度标签
  for (let i = 1; i <= 5; i++) {
    const value = minValue + (range / 5) * i
    const y = centerY - (radius / 5) * i
    ctx.fillText(value.toFixed(1), centerX + radius + 15, y)
  }
  
  // 绘制方向标签
  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
  for (let i = 0; i < 8; i++) {
    const angle = (i / 8) * 2 * Math.PI
    const x = centerX + Math.cos(angle) * (radius + 20)
    const y = centerY + Math.sin(angle) * (radius + 20)
    ctx.fillText(directions[i], x, y)
  }
  
  // 绘制标题
  ctx.fillStyle = '#333333'
  ctx.font = 'bold 12px Arial'
  ctx.fillText('风速分布(m/s)', centerX, 20)
  
  // 绘制雷达图
  ctx.fillStyle = 'rgba(231, 76, 60, 0.3)'
  ctx.strokeStyle = '#e74c3c'
  ctx.lineWidth = 2
  ctx.beginPath()
  
  data.forEach((value, index) => {
    const angle = (index / data.length) * 2 * Math.PI - Math.PI / 2
    const normalizedValue = (value - minValue) / range
    const r = normalizedValue * radius
    const x = centerX + Math.cos(angle) * r
    const y = centerY + Math.sin(angle) * r
    
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.closePath()
  ctx.fill()
  ctx.stroke()
  
  // 绘制数据点
  ctx.fillStyle = '#e74c3c'
  data.forEach((value, index) => {
    const angle = (index / data.length) * 2 * Math.PI - Math.PI / 2
    const normalizedValue = (value - minValue) / range
    const r = normalizedValue * radius
    const x = centerX + Math.cos(angle) * r
    const y = centerY + Math.sin(angle) * r
    
    ctx.beginPath()
    ctx.arc(x, y, 3, 0, 2 * Math.PI)
    ctx.fill()
  })
}
</script>

<style scoped>
.climate-monitoring {
  min-height: 100vh;
  background: #f4f7fa;
  padding: 0;
  margin: 0;
  overflow-x: auto;
  overflow-y: auto;
}

/* 自定义滚动条样式 */
.climate-monitoring::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.climate-monitoring::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.climate-monitoring::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.climate-monitoring::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.main-container {
  display: flex;
  min-height: 100vh;
  min-width: 1200px; /* 确保最小宽度，避免内容被压缩 */
  background: #f4f7fa;
}

.left-panel {
  width: 360px;
  background: #ffffff;
  border-right: 1px solid #dbe6f0;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 12px rgba(15, 23, 42, 0.06);
  overflow-y: auto;
}

/* 左侧面板滚动条样式 */
.left-panel::-webkit-scrollbar {
  width: 6px;
}

.left-panel::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.left-panel::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.left-panel::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.panel-header {
  background: linear-gradient(135deg, #1f78d1 0%, #4a9ae6 100%);
  color: white;
  padding: 22px 18px;
  text-align: left;
  box-shadow: 0 2px 10px rgba(31, 120, 209, 0.18);
}

.back-home-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 14px;
  padding: 6px 10px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.92);
  background: rgba(255, 255, 255, 0.14);
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
  transition: background 0.2s ease, transform 0.2s ease;
}

.back-home-link:hover {
  background: rgba(255, 255, 255, 0.22);
  transform: translateY(-1px);
}

.back-home-icon {
  width: 14px;
  height: 14px;
}

.panel-header h1 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
}

.panel-header p {
  margin: 10px 0 0 0;
  font-size: 12px;
  opacity: 0.92;
  line-height: 1.6;
}

/* 功能区块 */
.section {
  padding: 18px 16px;
  border-bottom: 1px solid #edf2f7;
}

.section:last-child {
  border-bottom: none;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  font-weight: 600;
  color: #2f455c;
  font-size: 15px;
}

.section-icon {
  font-size: 16px;
}

.section-content {
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 文件上传区域 */
.file-upload-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.upload-zone {
  width: 100%;
  background: #f8fbfd;
  border: 1px dashed #cfddea;
  border-radius: 10px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-zone:hover {
  border-color: #4a9ae6;
  background: #f2f8fd;
}

.upload-icon {
  font-size: 24px;
  color: #1890ff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.upload-icon svg {
  width: 48px;
  height: 48px;
}

.upload-text {
  font-size: 14px;
  font-weight: 600;
  color: #2f455c;
}

.upload-hint {
  font-size: 12px;
  color: #667789;
}

.upload-types {
  font-size: 11px;
  color: #8a98a8;
}

.file-status {
  font-size: 12px;
  color: #5f7184;
  text-align: center;
  padding: 8px 12px;
  background: #f7fafc;
  border-radius: 8px;
  border: 1px solid #dbe6f0;
}

.capability-card {
  background: linear-gradient(180deg, #f7fbff 0%, #ffffff 100%);
  border: 1px solid #d7e7f6;
  border-radius: 10px;
  padding: 12px;
  box-shadow: 0 8px 20px rgba(31, 120, 209, 0.06);
}

.capability-title {
  font-size: 13px;
  font-weight: 700;
  color: #24405f;
  margin-bottom: 6px;
}

.capability-mode {
  font-size: 12px;
  color: #5d7488;
  margin-bottom: 10px;
}

.capability-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.capability-reason {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.6;
  color: #5d7488;
}

.capability-reason.warning {
  color: #b54708;
}

.metric-selector {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5eef6;
}

.metric-selector-label {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #36516b;
}

.metric-selector-current {
  margin-bottom: 10px;
  font-size: 12px;
  color: #1f78d1;
  font-weight: 700;
}

.metric-selector-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.metric-option {
  height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid #cfe0ee;
  background: #f8fbfd;
  color: #587085;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.metric-option:hover {
  border-color: #8dbce8;
  color: #1f78d1;
  background: #eef6fd;
}

.metric-option.active {
  border-color: #9fc8f1;
  color: #1f78d1;
  background: #e8f4ff;
  box-shadow: inset 0 0 0 1px rgba(31, 120, 209, 0.08);
}

.capability-tag {
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
}

.capability-tag.active {
  background: #e8f4ff;
  color: #1f78d1;
  border-color: #b7d8fb;
}

.capability-tag.muted {
  background: #f4f6f8;
  color: #99a7b5;
  border-color: #e1e7ed;
}

.analysis-btn {
  width: 100%;
  height: 42px;
  background: #1f78d1;
  color: white;
  border: none;
  padding: 0 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 10px rgba(31, 120, 209, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.analysis-btn:hover:not(.disabled) {
  background: #3389dd;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(31, 120, 209, 0.2);
}

.analysis-btn.disabled {
  cursor: not-allowed;
  background: #f5f5f5;
  color: #999;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 240px;
  overflow-y: auto;
}

.history-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: #6f8192;
}

.history-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.history-action-btn {
  padding: 0;
  border: none;
  background: transparent;
  color: #4a7db2;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.history-action-btn.primary {
  color: #1f78d1;
}

.history-item {
  width: 100%;
  display: flex;
  align-items: stretch;
  gap: 10px;
  padding: 10px;
  border: 1px solid #dbe6f0;
  border-radius: 10px;
  background: #f8fbfd;
}

.history-item:hover {
  border-color: #bfd5e8;
  background: #eef5fb;
}

.history-item-main {
  flex: 1;
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.history-item-main:hover {
  transform: translateY(-1px);
}

.history-delete-btn {
  align-self: center;
  min-width: 44px;
  padding: 6px 0;
  border: none;
  background: transparent;
  color: #d95c5c;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.history-item-title {
  font-size: 13px;
  font-weight: 700;
  color: #2f455c;
  line-height: 1.5;
  word-break: break-all;
}

.history-item-subtitle,
.history-item-time {
  margin-top: 4px;
  font-size: 12px;
  color: #6f8192;
}

.history-empty {
  margin-top: 10px;
  padding: 16px 12px;
  border: 1px dashed #dbe6f0;
  border-radius: 10px;
  background: #f8fbfd;
  color: #8a98a8;
  font-size: 13px;
  text-align: center;
}

.history-collapsed-tip {
  margin-top: 10px;
  font-size: 12px;
  color: #7b8a99;
  line-height: 1.6;
}

/* 进度指示器样式 */
.progress-section {
  margin: 16px;
  padding: 16px;
  background: #f7fafc;
  border-radius: 10px;
  border: 1px solid #dbe6f0;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #1890ff 0%, #40a9ff 100%);
  transition: width 0.5s ease-in-out;
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-text {
  font-size: 13px;
  color: #667789;
  text-align: center;
  font-weight: 600;
}

.error-message {
  background: #fff7f7;
  color: #b42318;
  padding: 16px;
  border-radius: 10px;
  margin: 0 16px 16px;
  border: 1px solid #f3d2cf;
  font-size: 14px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  box-shadow: 0 8px 20px rgba(180, 35, 24, 0.06);
}

.error-icon {
  font-size: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

.error-content {
  flex: 1;
}

.error-title {
  font-weight: 600;
  margin-bottom: 5px;
  font-size: 15px;
}

.error-details {
  margin-bottom: 10px;
  line-height: 1.4;
}

.error-actions {
  display: flex;
  gap: 8px;
}

.retry-btn, .dismiss-btn {
  height: 34px;
  padding: 0 16px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-btn {
  background: #1f78d1;
  color: white;
  box-shadow: 0 4px 10px rgba(31, 120, 209, 0.18);
}

.retry-btn:hover {
  background: #3389dd;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(31, 120, 209, 0.2);
}

.dismiss-btn {
  background: #f7fafc;
  color: #5f7184;
  border: 1px solid #dbe6f0;
}

.dismiss-btn:hover {
  background: #eef5fb;
  border-color: #bfd5e8;
  color: #315f8c;
}

.success-message {
  background: #f4fbf7;
  color: #1f7a4f;
  padding: 16px;
  border-radius: 10px;
  margin: 0 16px 16px;
  border: 1px solid #cde7d7;
  font-size: 14px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  box-shadow: 0 8px 20px rgba(31, 122, 79, 0.06);
}

.success-icon {
  font-size: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

.success-content {
  flex: 1;
}

.success-title {
  font-weight: 600;
  margin-bottom: 5px;
  font-size: 15px;
}

.success-details {
  margin-bottom: 10px;
  line-height: 1.4;
}

.success-actions {
  display: flex;
  gap: 8px;
}

.right-panel {
  flex: 1;
  background: #f4f7fa;
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow-y: auto;
  overflow-x: auto;
  max-height: 100vh;
}

/* 右侧面板滚动条样式 */
.right-panel::-webkit-scrollbar {
  width: 6px;
}

.right-panel::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.right-panel::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.right-panel::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-text {
  padding: 28px 32px;
  border: 1px dashed #dbe6f0;
  border-radius: 12px;
  background: #ffffff;
  color: #8a98a8;
  font-size: 14px;
  text-align: center;
  box-shadow: 0 8px 20px rgba(30, 50, 70, 0.05);
}

.placeholder p {
  font-size: 14px;
  color: #8a98a8;
  margin: 0;
}

.analysis-results {
  animation: fadeIn 0.5s ease-in;
  width: 100%;
  height: 100%;
  display: block;
  max-width: 1320px;
  margin: 0 auto;
  padding: 0;
}

.analysis-notice {
  margin-bottom: 20px;
  padding: 16px 18px;
  border-radius: 12px;
  border: 1px solid #d7e7f6;
  background: linear-gradient(180deg, #f7fbff 0%, #ffffff 100%);
  box-shadow: 0 10px 24px rgba(31, 120, 209, 0.08);
}

.analysis-notice-title {
  font-size: 15px;
  font-weight: 700;
  color: #22405f;
  margin-bottom: 6px;
}

.analysis-notice-text {
  font-size: 13px;
  line-height: 1.7;
  color: #5b7185;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.stats-overview {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #dbe6f0;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(30, 50, 70, 0.06);
}

.stats-overview h3 {
  color: #26384a;
  margin-bottom: 18px;
  font-size: 18px;
  font-weight: 700;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.stat-item {
  background: #f8fbfd;
  padding: 20px;
  border-radius: 10px;
  border: 1px solid #dbe6f0;
}

.stat-label {
  font-weight: 700;
  color: #2f455c;
  margin-bottom: 15px;
  font-size: 14px;
}

.stat-values {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stat-value {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e9ecef;
}

.stat-value:last-child {
  border-bottom: none;
}

.stat-value .label {
  color: #6f8192;
  font-size: 12px;
}

.stat-value .value {
  color: #26384a;
  font-weight: 600;
  font-size: 14px;
}

.charts-section {
  padding: 20px;
  border: 1px solid #dbe6f0;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(30, 50, 70, 0.06);
}

.charts-section h3 {
  color: #26384a;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 700;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 25px;
  width: 100%;
  min-width: 800px; /* 确保图表网格最小宽度 */
}

.chart-container {
  background: #f8fbfd;
  padding: 20px;
  border-radius: 10px;
  border: 1px solid #dbe6f0;
  min-width: 400px; /* 确保图表容器最小宽度 */
  overflow: hidden; /* 防止内容溢出 */
}

.chart-container h4 {
  color: #2f455c;
  margin-bottom: 15px;
  font-size: 14px;
  text-align: center;
  font-weight: 700;
}

.chart-container canvas {
  width: 100%;
  height: 200px;
  border-radius: 6px;
  background: white;
  max-width: 100%;
  display: block;
}


/* 响应式设计 */
@media (max-width: 1200px) {
  .main-container {
    flex-direction: column;
  }
  
  .left-panel {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #dbe6f0;
  }
  
  .right-panel {
    min-height: 400px;
  }
}

@media (max-width: 768px) {
  .main-container {
    flex-direction: column;
    min-width: 100%;
  }
  
  .left-panel {
    width: 100%;
  }
  
  .right-panel {
    padding: 20px;
    min-height: 300px;
    max-height: none;
  }
  
  .charts-grid {
    grid-template-columns: 1fr;
    min-width: 100%;
  }
  
  .chart-container {
    min-width: 100%;
  }
  
  .chart-container canvas {
    height: 150px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
