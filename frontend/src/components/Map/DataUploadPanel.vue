<template>
  <div class="data-upload-panel" :class="{ 'embedded': embedded }">
    <div class="panel-header" v-if="!embedded">
      <h3>数据上传管理</h3>
      <button class="close-btn" @click="$emit('close')">×</button>
    </div>
    
    <div class="panel-content">
      <!-- 数据类型选择器 -->
      <div class="data-type-selector">
        <div 
          v-for="type in dataTypes" 
          :key="type.value"
          class="type-tab"
          :class="{ 'active': selectedType === type.value }"
          @click="selectDataType(type.value)"
        >
          <span class="type-icon">{{ type.icon }}</span>
          <span class="type-label">{{ type.tabLabel || type.label }}</span>
        </div>
      </div>

      <!-- 统一的上传区域 -->
      <div class="upload-section">
        <template v-if="selectedType === 'ecology'">
          <div class="auto-sync-card">
            <div class="auto-sync-copy">
              <div class="auto-sync-title">挂接系统 RSEI 结果</div>
              <div class="auto-sync-hint">
                可以直接使用最近一次成功计算的 RSEI，也可以指定某张遥感影像对应的 RSEI 结果。
              </div>
            </div>
            <div class="source-selector">
              <label class="description-label" for="rsei-source-select">RSEI 来源影像</label>
              <select
                id="rsei-source-select"
                v-model="selectedEcologySource"
                class="source-select"
              >
                <option value="">最近一次成功结果</option>
                <option
                  v-for="item in availableRSEISources"
                  :key="item.result_id"
                  :value="item.remote_sensing_image_id"
                >
                  {{ formatRSEISourceLabel(item) }}
                </option>
              </select>
            </div>
            <RouterLink
              to="/remote-sensing-analysis"
              class="goto-remote-link"
            >
              前往遥感生态指数分析
            </RouterLink>
            <div class="rsei-action-row">
              <button
                class="rsei-action-btn sync-btn"
                :disabled="uploading.ecology || clearingRSEICache"
                @click="syncLatestRSEI"
              >
                {{ uploading.ecology ? '同步中...' : '同步 RSEI' }}
              </button>
              <button
                class="rsei-action-btn clear-cache-btn"
                :disabled="clearingRSEICache || uploading.ecology || !canClearRSEICache"
                @click="clearRSEICache"
              >
                {{ clearingRSEICache ? '清除中...' : '清除缓存' }}
              </button>
            </div>
          </div>

          <div class="manual-ecology-upload">
            <div class="manual-upload-title">直接上传生态栅格</div>
            <div class="upload-zone ecology-upload-zone" @click="triggerFileInput('ecology')">
              <input
                ref="ecologyInput"
                type="file"
                accept=".tif,.tiff"
                @change="handleFileSelect($event, 'ecology')"
                style="display: none"
              />
              <div v-if="!files.ecology">
                <div class="upload-icon ecology-upload-icon">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="#1890ff" stroke-width="2" fill="none"/>
                    <path d="M14 2V8H20" stroke="#1890ff" stroke-width="2" fill="none"/>
                    <path d="M12 18V12" stroke="#1890ff" stroke-width="2" stroke-linecap="round"/>
                    <path d="M9 15L12 12L15 15" stroke="#1890ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
                <div class="upload-text">{{ currentDataType.uploadText }}</div>
                <div class="upload-hint">拖放文件到此处或点击选择文件</div>
                <div class="upload-types">{{ currentDataType.fileTypes }}</div>
              </div>
              <div v-else class="file-info">
                <div class="file-name">{{ files.ecology.name }}</div>
                <div class="file-size">{{ formatFileSize(files.ecology.size) }}</div>
                <button class="remove-btn" @click.stop="removeFile('ecology')">移除</button>
              </div>
            </div>
            <div class="description-field">
              <label class="description-label" for="description-ecology">描述信息</label>
              <textarea
                id="description-ecology"
                v-model="descriptions.ecology"
                class="description-input ecology-description-input"
                rows="2"
                placeholder="可选，填写生态栅格来源、时间或说明"
              ></textarea>
            </div>
            <button
              class="upload-btn ecology-upload-btn"
              :disabled="!files.ecology || uploading.ecology"
              @click="uploadFile('ecology')"
            >
              {{ uploading.ecology ? '上传中...' : currentDataType.buttonText }}
            </button>
          </div>
          <div v-if="publishedLayers.ecologySynced" class="published-row auto-sync-published">
            <div>
              <strong>系统RSEI结果</strong>
              <span>已发布到地图</span>
              <span v-if="publishedLayers.ecologySynced.sourceImageName" class="published-meta">
                来源影像：{{ publishedLayers.ecologySynced.sourceImageName }}
              </span>
              <span v-if="publishedLayers.ecologySynced.fileName" class="published-meta">
                结果文件：{{ publishedLayers.ecologySynced.fileName }}
              </span>
              <span v-if="publishedLayers.ecologySynced.description" class="published-meta published-description">
                说明：{{ publishedLayers.ecologySynced.description }}
              </span>
            </div>
            <button
              class="delete-layer-btn"
              :disabled="deleting.ecology"
              @click="deleteUploadedLayer('ecology_synced')"
            >
              {{ deleting.ecology ? '删除中...' : '移除图层' }}
            </button>
          </div>
          <div v-if="publishedLayers.ecologyUploaded" class="published-row auto-sync-published">
            <div>
              <strong>上传生态栅格</strong>
              <span>已发布到地图</span>
              <span v-if="publishedLayers.ecologyUploaded.fileName" class="published-meta">
                文件：{{ publishedLayers.ecologyUploaded.fileName }}
              </span>
              <span v-if="publishedLayers.ecologyUploaded.description" class="published-meta published-description">
                说明：{{ publishedLayers.ecologyUploaded.description }}
              </span>
            </div>
            <button
              class="delete-layer-btn"
              :disabled="deleting.ecology"
              @click="deleteUploadedLayer('ecology_uploaded')"
            >
              {{ deleting.ecology ? '删除中...' : '移除图层' }}
            </button>
          </div>
        </template>

        <div v-else class="upload-zone" @click="triggerFileInput(selectedType)">
          <input 
            ref="economyInput"
            v-if="selectedType === 'economy'"
            type="file" 
            accept=".zip"
            @change="handleFileSelect($event, 'economy')"
            style="display: none"
          />
          <input 
            ref="engineeringInput"
            v-if="selectedType === 'engineering'"
            type="file" 
            accept=".zip"
            @change="handleFileSelect($event, 'engineering')"
            style="display: none"
          />
          <div v-if="!files[selectedType]">
            <div class="upload-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="#1890ff" stroke-width="2" fill="none"/>
                <path d="M14 2V8H20" stroke="#1890ff" stroke-width="2" fill="none"/>
                <path d="M12 18V12" stroke="#1890ff" stroke-width="2" stroke-linecap="round"/>
                <path d="M9 15L12 12L15 15" stroke="#1890ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="upload-text">{{ currentDataType.uploadText }}</div>
            <div class="upload-hint">拖放文件到此处或点击选择文件</div>
            <div class="upload-types">{{ currentDataType.fileTypes }}</div>
          </div>
          <div v-else class="file-info">
            <div class="file-name">{{ files[selectedType].name }}</div>
            <div class="file-size">{{ formatFileSize(files[selectedType].size) }}</div>
            <button class="remove-btn" @click.stop="removeFile(selectedType)">移除</button>
          </div>
        </div>
        <div v-if="selectedType !== 'ecology'" class="description-field">
          <label class="description-label" :for="`description-${selectedType}`">描述信息</label>
          <textarea
            :id="`description-${selectedType}`"
            v-model="descriptions[selectedType]"
            class="description-input"
            rows="3"
            :placeholder="`可选，填写${currentDataType.label}的来源、用途或补充说明`"
          ></textarea>
        </div>
        <button 
          v-if="selectedType !== 'ecology'"
          class="upload-btn" 
          :disabled="!files[selectedType] || uploading[selectedType]"
          @click="uploadFile(selectedType)"
        >
          {{ uploading[selectedType] ? '上传中...' : currentDataType.buttonText }}
        </button>
        <div v-if="uploadProgress[selectedType] > 0" class="progress-bar">
          <div class="progress-fill" :style="{ width: uploadProgress[selectedType] + '%' }"></div>
          <span class="progress-text">{{ uploadProgress[selectedType] }}%</span>
        </div>
        <div v-if="uploadStatus[selectedType]" :class="['status-message', uploadStatus[selectedType].type]">
          {{ uploadStatus[selectedType].message }}
        </div>
        <div v-if="selectedType !== 'ecology' && publishedLayers[selectedType]" class="published-row">
          <div>
            <strong>{{ currentDataType.label }}</strong>
            <span>已发布到地图</span>
            <span v-if="publishedLayers[selectedType].fileName" class="published-meta">
              文件：{{ publishedLayers[selectedType].fileName }}
            </span>
            <span v-if="publishedLayers[selectedType].description" class="published-meta published-description">
              描述：{{ publishedLayers[selectedType].description }}
            </span>
          </div>
          <button
            class="delete-layer-btn"
            :disabled="deleting[selectedType]"
            @click="deleteUploadedLayer(selectedType)"
          >
            {{ deleting[selectedType] ? '删除中...' : '删除图层' }}
          </button>
        </div>
      </div>

      <!-- 数据说明 -->
      <div class="data-requirements">
        <h4>数据要求说明</h4>
        <ul>
          <li><strong>生态指数栅格：</strong>可手动同步系统最近一次成功计算的 RSEI 结果，也可直接上传自己的生态栅格；如暂无结果，请先到“遥感生态指数分析”模块完成 RSEI 计算</li>
          <li><strong>经济数据矢量：</strong>建议包含区域名称、经济指标、人口、面积等字段；系统现会自动识别常见字段名并尽量适配</li>
          <li><strong>工程项目矢量：</strong>需包含字段：proj_name（项目名称）、proj_type（类型）、status（状态）、start_date、end_date、area_km2</li>
          <li><strong>字符编码：</strong>所有矢量数据请使用UTF-8编码，确保中文正常显示</li>
          <li><strong>坐标系统：</strong>建议使用 EPSG:4326 (WGS84) 坐标系</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import request from '../../utils/http.js'
import { API_ENDPOINTS, buildApiUrl } from '../../config/api.js'

const OVERLAY_RSEI_REFRESH_KEY = 'overlay_rsei_refresh_signal'

// Props
defineProps({
  embedded: {
    type: Boolean,
    default: false
  }
})

// 数据类型配置
const dataTypes = [
  {
    value: 'ecology',
    label: '生态指数栅格',
    tabLabel: '生态栅格',
    
    accept: '.tif,.tiff',
    uploadText: '上传生态指数栅格文件',
    fileTypes: '支持的文件类型: .tif, .tiff',
    buttonText: '上传生态栅格'
  },
  {
    value: 'economy',
    label: '经济数据矢量',
    tabLabel: '经济矢量',
    
    accept: '.zip',
    uploadText: '上传经济数据矢量文件',
    fileTypes: '支持的文件类型: .zip (包含 .shp/.shx/.dbf/.prj)',
    buttonText: '上传经济矢量'
  },
  {
    value: 'engineering',
    label: '工程项目矢量',
    tabLabel: '工程矢量',
    
    accept: '.zip',
    uploadText: '上传工程项目矢量文件',
    fileTypes: '支持的文件类型: .zip (包含 .shp/.shx/.dbf/.prj)',
    buttonText: '上传工程矢量'
  }
]

// 当前选择的数据类型
const selectedType = ref('ecology')

// 计算当前数据类型配置
const currentDataType = computed(() => {
  return dataTypes.find(type => type.value === selectedType.value) || dataTypes[0]
})

// 文件输入引用
const ecologyInput = ref(null)
const economyInput = ref(null)
const engineeringInput = ref(null)
const maxUploadSize = 1024 * 1024 * 1024

const getRequestErrorMessage = (error, fallback = '上传失败') => {
  const data = error?.response?.data
  if (Array.isArray(data?.details) && data.details.length > 0) {
    return data.details.join('；')
  }
  return data?.message || data?.error || data?.detail || error?.message || fallback
}

// 选择数据类型
const selectDataType = (type) => {
  selectedType.value = type
}

// 文件选择
const files = reactive({
  ecology: null,
  economy: null,
  engineering: null
})

const descriptions = reactive({
  ecology: '',
  economy: '',
  engineering: ''
})

const availableRSEISources = ref([])
const selectedEcologySource = ref('')
const clearingRSEICache = ref(false)
const overlayMetadataKeyMap = {
  ecologySynced: 'ecology_synced',
  ecologyUploaded: 'ecology_uploaded',
  economy: 'economy',
  engineering: 'engineering'
}

// 上传状态
const uploading = reactive({
  ecology: false,
  economy: false,
  engineering: false
})

// 上传进度
const uploadProgress = reactive({
  ecology: 0,
  economy: 0,
  engineering: 0
})

// 上传结果状态
const uploadStatus = reactive({
  ecology: null,
  economy: null,
  engineering: null
})

const publishedLayers = reactive({
  ecologySynced: null,
  ecologyUploaded: null,
  economy: null,
  engineering: null
})

const deleting = reactive({
  ecology: false,
  economy: false,
  engineering: false
})

let removeWindowFocusListener = null

const canClearRSEICache = computed(() => {
  return Boolean(
    publishedLayers.ecologySynced ||
    selectedEcologySource.value ||
    availableRSEISources.value.length > 0
  )
})

// 触发文件选择
const triggerFileInput = (type) => {
  if (type === 'ecology' && ecologyInput.value) {
    ecologyInput.value.click()
  } else if (type === 'economy' && economyInput.value) {
    economyInput.value.click()
  } else if (type === 'engineering' && engineeringInput.value) {
    engineeringInput.value.click()
  }
}

// 处理文件选择
const handleFileSelect = (event, type) => {
  const file = event.target.files[0]
  if (file) {
    if (file.size > maxUploadSize) {
      uploadStatus[type] = {
        type: 'error',
        message: '文件大小超过1GB限制'
      }
      return
    }
    
    files[type] = file
    uploadStatus[type] = null
    uploadProgress[type] = 0
  }
}

// 移除文件
const removeFile = (type) => {
  files[type] = null
  uploadStatus[type] = null
  uploadProgress[type] = 0
}

const normalizePublishedLayer = (type, payload = {}) => {
  return {
    type,
    fileName: payload.file_name || payload.fileName || '',
    description: payload.description || '',
    layerName: payload.layer_name || payload.layerName || '',
    updatedAt: payload.updated_at || payload.updatedAt || null,
    sourceType: payload.source_type || payload.sourceType || '',
    sourceImageId: payload.source_image_id || payload.sourceImageId || '',
    sourceImageName: payload.source_image_name || payload.sourceImageName || '',
    sourceResultId: payload.source_result_id || payload.sourceResultId || '',
    sourceResultCreatedAt: payload.source_result_created_at || payload.sourceResultCreatedAt || null
  }
}

const loadUploadedLayerMetadata = async () => {
  try {
    const endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.UPLOADED_LAYER_METADATA)
    const response = await request.get(endpoint, {}, { skipAuth: true, silentError: true })
    const metadata = response?.data || {}

    Object.entries(overlayMetadataKeyMap).forEach(([stateKey, metadataKey]) => {
      const item = metadata[metadataKey]
      if (item?.published) {
        publishedLayers[stateKey] = normalizePublishedLayer(metadataKey, item)
        if (stateKey === 'ecologyUploaded') {
          descriptions.ecology = item.description || descriptions.ecology
        } else if (stateKey === 'economy' || stateKey === 'engineering') {
          descriptions[stateKey] = item.description || descriptions[stateKey]
        }
      } else {
        publishedLayers[stateKey] = null
      }
    })
  } catch (error) {
    console.warn('加载已上传图层描述失败:', error)
  }
}

const loadAvailableRSEISources = async () => {
  try {
    const endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.AVAILABLE_RSEI_SOURCES)
    const response = await request.get(endpoint, {}, { skipAuth: true, silentError: true })
    availableRSEISources.value = Array.isArray(response?.data) ? response.data : []
  } catch (error) {
    console.warn('加载RSEI来源列表失败:', error)
    availableRSEISources.value = []
  }
}

const tryConsumeOverlayRefreshSignal = async () => {
  let signal = null
  try {
    const rawSignal = localStorage.getItem(OVERLAY_RSEI_REFRESH_KEY)
    if (!rawSignal) {
      return
    }
    signal = JSON.parse(rawSignal)
  } catch (error) {
    console.warn('读取叠加分析刷新信号失败:', error)
  } finally {
    try {
      localStorage.removeItem(OVERLAY_RSEI_REFRESH_KEY)
    } catch (error) {
      console.warn('清理叠加分析刷新信号失败:', error)
    }
  }

  await loadAvailableRSEISources()

  if (signal?.remote_sensing_image_id) {
    const matchedSource = availableRSEISources.value.find(
      item => item.remote_sensing_image_id === signal.remote_sensing_image_id
    )
    if (matchedSource) {
      selectedEcologySource.value = matchedSource.remote_sensing_image_id
      return
    }
  }
}

const formatRSEISourceLabel = (item) => {
  const parts = [item?.remote_sensing_image_name || '未命名影像']
  if (item?.acquisition_date) {
    parts.push(item.acquisition_date)
  }
  return parts.join(' / ')
}

const syncLatestRSEI = async (silent = false) => {
  uploading.ecology = true
  if (!silent) {
    uploadStatus.ecology = { type: 'info', message: '正在同步最近一次 RSEI 结果...' }
  }

  try {
    const endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.SYNC_LATEST_RSEI)
    const payload = selectedEcologySource.value
      ? { remote_sensing_image_id: selectedEcologySource.value }
      : {}
    const response = await request.post(endpoint, payload, { skipAuth: true, silentError: silent })

    if (response.success) {
      publishedLayers.ecologySynced = normalizePublishedLayer('ecology_synced', response.metadata || {})
      descriptions.ecology = response.metadata?.description || descriptions.ecology
      if (response.metadata?.source_image_id) {
        selectedEcologySource.value = response.metadata.source_image_id
      }
      uploadStatus.ecology = {
        type: 'success',
        message: response.message || '最近一次 RSEI 结果已同步'
      }
      emitRefreshMap('ecology_synced', 'updated')
      return true
    }

    if (response.reason === 'no_rsei_result') {
      if (!silent && !publishedLayers.ecologySynced) {
        uploadStatus.ecology = {
          type: 'info',
          message: response.message || '当前还没有可用的 RSEI 结果，请先去遥感生态指数分析模块计算。'
        }
      }
      return false
    }

    if (!silent) {
      uploadStatus.ecology = {
        type: 'error',
        message: response.message || '同步最近一次 RSEI 结果失败'
      }
    }
    return false
  } catch (error) {
    if (!silent) {
      uploadStatus.ecology = {
        type: 'error',
        message: getRequestErrorMessage(error, '同步最近一次 RSEI 结果失败')
      }
    }
    return false
  } finally {
    uploading.ecology = false
  }
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// 上传文件
const uploadFile = async (type) => {
  if (!files[type]) return
  
  uploading[type] = true
  uploadStatus[type] = { type: 'info', message: '正在上传...' }
  uploadProgress[type] = 0
  
  try {
    const formData = new FormData()
    formData.append('file', files[type])
    formData.append('data_type', type)
    formData.append('description', descriptions[type] || '')
    
    // 根据类型确定上传端点（注意：URL必须以斜杠结尾）
    let endpoint = ''
    if (type === 'ecology') {
      endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.UPLOAD_ECOLOGY_RASTER)
    } else if (type === 'economy') {
      endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.UPLOAD_ECONOMY_VECTOR)
    } else if (type === 'engineering') {
      endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.UPLOAD_ENGINEERING_VECTOR)
    }
    
    const response = await request.upload(endpoint, formData, {
      skipAuth: true,
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        uploadProgress[type] = percentCompleted
      }
    })
    
    if (response.success) {
      const publishedStateKey = type === 'ecology' ? 'ecologyUploaded' : type
      publishedLayers[publishedStateKey] = normalizePublishedLayer(type === 'ecology' ? 'ecology_uploaded' : type, response.metadata || {
        file_name: response.file_name || files[type]?.name,
        description: response.description || descriptions[type],
        layer_name: response.layer_name
      })
      uploadStatus[type] = {
        type: 'success',
        message: response.message || '上传成功！数据已发布到GeoServer'
      }
      
      // 3秒后清空文件选择
      setTimeout(() => {
        files[type] = null
        uploadProgress[type] = 0
      }, 3000)
      
      // 触发地图刷新事件
      emitRefreshMap(type === 'ecology' ? 'ecology_uploaded' : type, 'updated')
    } else {
      const publishedStateKey = type === 'ecology' ? 'ecologyUploaded' : type
      publishedLayers[publishedStateKey] = null
      uploadStatus[type] = {
        type: 'error',
        message: response.message || '上传失败'
      }
    }
  } catch (error) {
    console.error('上传失败:', error)
    console.error('错误详情:', error.response?.data)
    
    // 提取错误信息
    let errorMessage = '上传失败'
    if (error.response) {
      errorMessage = `${getRequestErrorMessage(error)} (HTTP ${error.response.status})`
    } else if (error.message) {
      errorMessage = `上传失败: ${error.message}`
    }
    
    uploadStatus[type] = {
      type: 'error',
      message: errorMessage
    }
    const publishedStateKey = type === 'ecology' ? 'ecologyUploaded' : type
    publishedLayers[publishedStateKey] = null
  } finally {
    uploading[type] = false
  }
}

const deleteUploadedLayer = async (type) => {
  const stateKey = type === 'ecology_synced'
    ? 'ecologySynced'
    : type === 'ecology_uploaded'
      ? 'ecologyUploaded'
      : type
  const deletingKey = type.startsWith('ecology_') ? 'ecology' : type
  deleting[deletingKey] = true
  uploadStatus[deletingKey] = { type: 'info', message: '正在删除图层...' }
  try {
    const endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.DELETE_UPLOADED_LAYER)
    const response = await request.delete(endpoint, {
      skipAuth: true,
      params: { data_type: type }
    })

    publishedLayers[stateKey] = null
    if (type === 'ecology_uploaded') {
      files.ecology = null
      uploadProgress.ecology = 0
      descriptions.ecology = ''
      uploadStatus.ecology = {
        type: response.success ? 'success' : 'error',
        message: response.message || '图层已删除'
      }
    } else if (type === 'ecology_synced') {
      uploadStatus.ecology = {
        type: response.success ? 'success' : 'error',
        message: response.message || '图层已删除'
      }
    } else {
      files[type] = null
      uploadProgress[type] = 0
      descriptions[type] = ''
      uploadStatus[type] = {
        type: response.success ? 'success' : 'error',
        message: response.message || '图层已删除'
      }
    }
    emitRefreshMap(type, 'deleted')
  } catch (error) {
    console.error('删除图层失败:', error)
    uploadStatus.ecology = type.startsWith('ecology_')
      ? {
          type: 'error',
          message: getRequestErrorMessage(error, '删除图层失败')
        }
      : uploadStatus.ecology
    if (!type.startsWith('ecology_')) {
      uploadStatus[type] = {
        type: 'error',
        message: getRequestErrorMessage(error, '删除图层失败')
      }
    }
  } finally {
    deleting[deletingKey] = false
  }
}

const clearRSEICache = async () => {
  if (!window.confirm('确定要清除系统同步的 RSEI 缓存吗？这不会删除你手动上传的生态栅格。')) {
    return
  }

  clearingRSEICache.value = true
  uploadStatus.ecology = { type: 'info', message: '正在清除RSEI缓存...' }

  try {
    const endpoint = buildApiUrl(API_ENDPOINTS.OVERLAY_ANALYSIS.CLEAR_RSEI_CACHE)
    const response = await request.delete(endpoint, { skipAuth: true })

    publishedLayers.ecologySynced = null
    selectedEcologySource.value = ''
    availableRSEISources.value = []
    uploadStatus.ecology = {
      type: response.success ? 'success' : 'error',
      message: response.message || 'RSEI缓存已清除'
    }
    emitRefreshMap('ecology_synced', 'deleted')
  } catch (error) {
    console.error('清除RSEI缓存失败:', error)
    uploadStatus.ecology = {
      type: 'error',
      message: getRequestErrorMessage(error, '清除RSEI缓存失败')
    }
  } finally {
    clearingRSEICache.value = false
  }
}

// 定义事件
const emit = defineEmits(['close', 'refresh-map'])

// 触发地图刷新
const emitRefreshMap = (type = selectedType.value, action = 'updated') => {
  emit('refresh-map', { type, action })
}

onMounted(() => {
  loadUploadedLayerMetadata()
  loadAvailableRSEISources()

  const handleWindowFocus = () => {
    tryConsumeOverlayRefreshSignal()
  }

  window.addEventListener('focus', handleWindowFocus)
  removeWindowFocusListener = () => window.removeEventListener('focus', handleWindowFocus)
  tryConsumeOverlayRefreshSignal()
})

onBeforeUnmount(() => {
  if (removeWindowFocusListener) {
    removeWindowFocusListener()
    removeWindowFocusListener = null
  }
})
</script>

<style scoped>
.data-upload-panel {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  z-index: 2000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.data-upload-panel.embedded {
  position: relative;
  top: auto;
  left: auto;
  transform: none;
  width: 100%;
  max-width: 100%;
  max-height: none;
  box-shadow: none;
  border-radius: 0;
  z-index: auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 2px solid #f0f0f0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.panel-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.upload-section {
  margin-bottom: 20px;
}

.auto-sync-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  margin-bottom: 12px;
  border-radius: 12px;
  border: 1px solid #d8e6f3;
  background:
    radial-gradient(circle at top right, rgba(24, 144, 255, 0.08), transparent 30%),
    linear-gradient(180deg, #f8fbfe 0%, #f3f8fc 100%);
}

.auto-sync-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-select {
  width: 100%;
  min-height: 40px;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid #cfe0ee;
  background: #fff;
  color: #31485d;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.source-select:focus {
  border-color: #4aa3ea;
  box-shadow: 0 0 0 3px rgba(74, 163, 234, 0.14);
}

.goto-remote-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid #cfe0ee;
  background: rgba(255, 255, 255, 0.92);
  color: #2a6fb0;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.45;
  text-align: center;
  text-decoration: none;
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.goto-remote-link:hover {
  border-color: #79b5ec;
  box-shadow: 0 8px 18px rgba(42, 111, 176, 0.12);
  transform: translateY(-1px);
}

.auto-sync-title {
  font-size: 15px;
  font-weight: 700;
  color: #24415c;
}

.auto-sync-hint {
  font-size: 13px;
  line-height: 1.7;
  color: #61768a;
}

.rsei-action-btn {
  flex: 1 1 0;
  min-width: 0;
  height: 40px;
  margin-bottom: 0;
  padding: 0 12px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.35;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}

.sync-btn {
  border: 1px solid #4aa3ea;
  background: #2f97ea;
  color: #fff;
  box-shadow: none;
}

.rsei-action-row {
  display: flex;
  gap: 10px;
  align-items: stretch;
}

.clear-cache-btn {
  border: 1px solid #ffccc7;
  background: #fff7f6;
  color: #cf1322;
  box-shadow: none;
}

.sync-btn:hover:not(:disabled) {
  background: #2388d8;
  border-color: #2388d8;
}

.clear-cache-btn:hover:not(:disabled) {
  background: #fff1f0;
  border-color: #ff9c96;
}

.rsei-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.auto-sync-published {
  margin-top: 0;
}

.manual-ecology-upload {
  margin-bottom: 12px;
  padding: 14px;
  border: 1px solid #dbe8f3;
  border-radius: 12px;
  background: #fbfdff;
}

.manual-upload-title {
  margin-bottom: 10px;
  color: #24415c;
  font-size: 14px;
  font-weight: 700;
}

.ecology-upload-zone {
  padding: 16px 12px;
}

.ecology-upload-icon {
  margin-bottom: 4px;
}

.ecology-upload-icon svg {
  width: 40px;
  height: 40px;
}

.ecology-description-input {
  min-height: 62px;
}

.ecology-upload-btn {
  min-height: 40px;
  padding: 9px 12px;
  margin-bottom: 0;
}

.icon {
  font-size: 20px;
}

/* 数据类型选择器 */
.data-type-selector {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 1px solid #f0f0f0;
  padding: 0 0 16px;
}

.type-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: 48px;
  padding: 0 8px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s;
  background: #f7f9fb;
  color: #5c6b7a;
  font-size: 12px;
  line-height: 1.35;
  text-align: center;
  user-select: none;
  border: 1px solid #e1e9f0;
}

.type-tab:hover {
  background: linear-gradient(135deg, rgba(24, 144, 255, 0.1) 0%, rgba(64, 169, 255, 0.1) 100%);
  color: #1890ff;
  border: 1px solid rgba(24, 144, 255, 0.2);
}

.type-tab.active {
  background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
  color: white;
  font-weight: 500;
  box-shadow: 0 2px 6px rgba(24, 144, 255, 0.3);
}

.type-icon {
  display: none;
}

.type-label {
  display: block;
  width: 100%;
  font-size: 12px;
  line-height: 1.35;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.upload-zone {
  width: 100%;
  background: #f8f9fa;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.upload-zone:hover {
  border-color: #1890ff;
  background: linear-gradient(135deg, rgba(24, 144, 255, 0.05) 0%, rgba(64, 169, 255, 0.05) 100%);
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
}

.upload-icon {
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
  font-weight: 500;
  color: #333;
}

.upload-hint {
  font-size: 12px;
  color: #666;
}

.upload-types {
  font-size: 11px;
  color: #999;
}

.file-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  text-align: left;
  width: 100%;
  gap: 12px;
}

.file-name {
  font-weight: 500;
  color: #333;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  color: #999;
  font-size: 13px;
  margin-right: 12px;
}

.remove-btn {
  padding: 4px 12px;
  border: 1px solid #ff4d4f;
  background: white;
  color: #ff4d4f;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.remove-btn:hover {
  background: #ff4d4f;
  color: white;
}

.upload-btn {
  width: 100%;
  padding: 12px;
  border: none;
  background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
  color: white;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.3);
}

.upload-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.4);
  opacity: 0.95;
}

.upload-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.progress-bar {
  position: relative;
  height: 24px;
  background: #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #1890ff 0%, #40a9ff 100%);
  transition: width 0.3s;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 12px;
  font-weight: 600;
}

.status-message {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.status-message.success {
  background: #f0f9ff;
  color: #0066cc;
  border: 1px solid #b3d9ff;
}

.status-message.error {
  background: #fff1f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
}

.status-message.info {
  background: #f0f5ff;
  color: #1890ff;
  border: 1px solid #adc6ff;
}

.description-field {
  margin-bottom: 12px;
}

.description-label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: #4b5b6a;
  font-weight: 500;
}

.description-input {
  width: 100%;
  resize: vertical;
  min-height: 78px;
  padding: 10px 12px;
  border: 1px solid #d9e3ec;
  border-radius: 8px;
  font-size: 13px;
  color: #24384d;
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.description-input:focus {
  outline: none;
  border-color: #40a9ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.12);
}

.description-input::placeholder {
  color: #9aa8b5;
}

.published-row {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid #d6e8fa;
  border-radius: 7px;
  background: #f7fbff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: #315f8c;
  font-size: 13px;
}

.published-row div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.published-row span {
  color: #6b7f93;
  font-size: 12px;
}

.published-meta {
  margin-top: 2px;
}

.published-description {
  white-space: pre-wrap;
  line-height: 1.5;
}

.delete-layer-btn {
  flex-shrink: 0;
  height: 30px;
  padding: 0 12px;
  border: 1px solid #ffccc7;
  border-radius: 5px;
  background: #fff;
  color: #cf1322;
  cursor: pointer;
  font-size: 12px;
}

.delete-layer-btn:hover:not(:disabled) {
  background: #fff1f0;
}

.delete-layer-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.data-requirements {
  margin-top: 32px;
  padding: 20px;
  background: #fff9e6;
  border-radius: 8px;
  border: 1px solid #ffe58f;
}

.data-requirements h4 {
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: #fa8c16;
}

.data-requirements ul {
  margin: 0;
  padding-left: 20px;
}

.data-requirements li {
  margin-bottom: 8px;
  color: #666;
  font-size: 13px;
  line-height: 1.6;
}

.data-requirements strong {
  color: #333;
}
</style>

