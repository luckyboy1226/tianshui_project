<template>
  <div class="ecological-analysis" v-loading="globalLoading" 
       element-loading-text="正在分析数据，请稍候..."
       element-loading-background="rgba(255, 255, 255, 0.8)">
    <div class="ecological-container">
      <!-- 左侧控制面板 -->
      <div class="left-panel">
        <!-- 标题栏 -->
        <div class="panel-header">
          <RouterLink to="/" class="back-home-link" title="返回主界面">
            <ArrowLeft class="back-home-icon" />
            <span>主界面</span>
          </RouterLink>
          <h1>生态环境指数计算</h1>
          <p>上传土地利用数据，系统将自动计算多种生态指数并进行可视化。</p>
        </div>
        
        <!-- 数据文件管理 -->
        <div class="section">
          <div class="section-header">
            <Files class="section-icon" />
            <span>数据文件管理</span>
          </div>
          <div class="section-content">
            <div class="file-upload-area">
              <div class="upload-zone" @click="triggerFileUpload">
                <div class="upload-icon">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="#1890ff" stroke-width="2" fill="none"/>
                    <path d="M14 2V8H20" stroke="#1890ff" stroke-width="2" fill="none"/>
                    <path d="M12 18V12" stroke="#1890ff" stroke-width="2" stroke-linecap="round"/>
                    <path d="M9 15L12 12L15 15" stroke="#1890ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
                <div class="upload-text">上传土地利用数据文件</div>
                <div class="upload-hint">拖放文件到此处或点击选择文件</div>
                <div class="upload-types">支持 .tif/.tiff 土地利用分类栅格或 Shapefile ZIP；ADF需先转GeoTIFF</div>
              </div>
              <div class="file-status">
                {{ currentFileLabel }}
              </div>
              <el-button 
                v-if="fileList.length > 0 || restoredFileName"
                class="re-upload-btn" 
                @click="clearFile"
                size="small"
                type="info"
              >
                重新选择
              </el-button>
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
            <el-button 
              class="start-analysis-btn" 
              @click="startAnalysis"
              :disabled="fileList.length === 0"
              :loading="globalLoading"
            >
              开始分析
            </el-button>
          </div>
        </div>

        <div class="section">
          <div class="section-content">
            <div class="history-card">
              <div class="history-card__title-row">
                <FolderOpened class="history-card__icon" />
                <span class="history-card__title">最近结果</span>
              </div>
              <div class="history-card__summary-row">
                <span class="history-card__count">{{ historyItems.length }} 条</span>
                <div class="history-card__actions">
                  <button
                    v-if="historyExpanded && historyItems.length > 0"
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
              <div class="history-card__description">
                这里会保留最近几次可直接回看的结果
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
                这里会保留最近几次可直接回看的结果
              </div>
            </div>
          </div>
        </div>
        
        <!-- 指数选择区域 -->
        <div class="section">
          <div class="section-header">
            <Histogram class="section-icon" />
            <span>指数选择</span>
          </div>
          <div class="section-content">
            <!-- 生态环境结构指数 -->
            <div class="index-group">
              <div class="group-title">生态环境结构指数</div>
              <div class="index-buttons">
                <el-button 
                  v-for="index in structureIndices" 
                  :key="index.key"
                  :type="index.calculated ? 'success' : 'default'"
                  :loading="index.loading"
                  @click="calculateIndex(index.key)"
                  class="index-btn"
                  :disabled="fileList.length === 0"
                >
                  {{ index.name }}
                  <el-tag v-if="index.calculated" size="small" type="success">已计算</el-tag>
                </el-button>
              </div>
            </div>
            
            <!-- 生态环境胁迫指数 -->
            <div class="index-group">
              <div class="group-title">生态环境胁迫指数</div>
              <div class="index-buttons">
                <el-button 
                  v-for="index in stressIndices" 
                  :key="index.key"
                  :type="index.calculated ? 'success' : 'default'"
                  :loading="index.loading"
                  @click="calculateIndex(index.key)"
                  class="index-btn"
                  :disabled="fileList.length === 0"
                >
                  {{ index.name }}
                  <el-tag v-if="index.calculated" size="small" type="success">已计算</el-tag>
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧结果展示区域 -->
      <div class="right-panel">
        <div class="results-area">
          <!-- 有结果时显示 -->
          <div v-if="hasResults" class="results-content">
            <div v-if="landuseVisualizationUrl" class="visualization-card">
              <div class="values-title">土地利用分布与面积比例</div>
              <img :src="landuseVisualizationUrl" alt="土地利用分布图" class="landuse-visualization" />
            </div>

            <ResultCompareMap
              v-if="compareOverlay"
              title="上方土地利用图叠加对比"
              description="这里对比的就是上方那张土地利用分布图，打开遥感影像底图后可直接叠加查看。"
              :compare-overlay="compareOverlay"
            />

            <!-- 指数值展示 -->
            <div class="index-values">
              <div class="values-title">计算结果</div>
              <div class="values-grid">
                <div 
                  v-for="(value, key) in indexResults" 
                  :key="key"
                  class="value-item"
                >
                  <div class="value-name">{{ getIndexName(key) }}</div>
                  <div class="value-number">{{ formatIndexValue(key, value) }}</div>
                  <div class="value-status" :class="getStatusClass(key, value)">
                    {{ getStatusText(key, value) }}
                  </div>
                  <div class="value-unit">{{ getIndexUnit(key) }}</div>
                  <div class="value-scale">{{ getScaleHint(key) }}</div>
                </div>
              </div>
            </div>

            <div v-if="analysisMeta" class="analysis-meta-card">
              <div class="chart-title">计算说明</div>
              <div class="meta-row">
                <span class="meta-label">计算引擎</span>
                <span class="meta-value">{{ analysisMeta.analysis_engine_label || analysisMeta.analysis_engine }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-label">计算精度</span>
                <span class="meta-value">{{ getPrecisionLabel(analysisMeta.analysis_precision) }}</span>
              </div>
              <div class="meta-notes">
                <div v-for="(note, index) in analysisMeta.analysis_notes || []" :key="index" class="meta-note">
                  {{ note }}
                </div>
              </div>
            </div>

            <div v-if="landuseClasses.length > 0" class="landuse-table-card">
              <div class="chart-title">土地利用分类统计</div>
              <div class="landuse-table">
                <div class="table-row table-head">
                  <span>类型</span>
                  <span>面积(km²)</span>
                  <span>比例</span>
                  <span>像元数</span>
                </div>
                <div v-for="item in landuseClasses" :key="item.id" class="table-row">
                  <span>{{ item.name }}</span>
                  <span>{{ item.area_km2.toFixed(3) }}</span>
                  <span>{{ item.ratio_percent.toFixed(2) }}%</span>
                  <span>{{ item.pixels }}</span>
                </div>
              </div>
            </div>
            
            <!-- 图表展示 -->
            <div class="charts-section">
              <div class="chart-container">
                <div class="chart-title">指数分布雷达图</div>
                <div ref="radarChart" class="chart"></div>
              </div>
              
              <div class="chart-container">
                <div class="chart-title">指数对比柱状图</div>
                <div ref="barChart" class="chart"></div>
              </div>
            </div>
            
            <!-- 下载按钮 -->
            <div class="download-section">
              <el-button 
                type="success" 
                @click="downloadResults"
                class="download-btn"
              >
                <el-icon><Download /></el-icon>
                下载计算结果
              </el-button>
            </div>
          </div>
          
          <!-- 无结果时显示占位符 -->
          <div v-else class="placeholder">
            <div class="placeholder-text">
              请先上传数据并开始分析
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 移除自定义loading容器，使用Element Plus的内置loading -->
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Download, Files, FolderOpened, Histogram, Search } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { API_ENDPOINTS, buildApiUrl } from '../config/api.js'
import http from '../utils/http.js'
import ResultCompareMap from '../components/Map/ResultCompareMap.vue'
import { clearResultHistory, formatHistoryTime, loadResultHistory, removeResultHistory, saveResultHistory } from '../utils/resultHistory.js'

export default {
  name: 'EcologicalIndex',
  components: {
    ResultCompareMap
  },
  setup() {
    const HISTORY_KEY = 'ecological_index'
    const getRequestErrorMessage = (error, fallback = '服务器错误') => {
      const data = error?.response?.data
      if (Array.isArray(data?.details) && data.details.length > 0) {
        return data.details.join('；')
      }
      return data?.error || data?.message || data?.detail || error?.message || fallback
    }

    // 响应式数据
    const fileList = ref([])
    const globalLoading = ref(false)
    const uploadLoading = ref(false)
    const restoredFileName = ref('')
    const landuseVisualizationUrl = ref('')
    const landuseStatistics = ref(null)
    const analysisMeta = ref(null)
    const compareOverlay = ref(null)
    const historyItems = ref([])
    const historyExpanded = ref(false)
    
    // 监听 globalLoading 的变化
    watch(globalLoading, (newVal, oldVal) => {
      // globalLoading 状态变化监听
    })
    
    // 指数定义
    const structureIndices = reactive([
      { key: 'fragmentation', name: '破碎度指数', calculated: false, loading: false, apiKey: 'fragmentation_index' },
      { key: 'cohesion', name: '内聚力指数', calculated: false, loading: false, apiKey: 'cohesion_index' },
      { key: 'diversity', name: '多样性指数', calculated: false, loading: false, apiKey: 'shannon_diversity' },
      { key: 'fragility', name: '脆弱度指数', calculated: false, loading: false, apiKey: 'fragility_index' }
    ])
    
    const stressIndices = reactive([
      { key: 'soil_erosion', name: '土壤侵蚀指数', calculated: false, loading: false, apiKey: 'soil_erosion_index' },
      { key: 'unused_land', name: '未利用地面积比例', calculated: false, loading: false, apiKey: 'unused_land_proportion' },
      { key: 'cultivated_construction', name: '耕地建设用地面积比例', calculated: false, loading: false, apiKey: 'cultivated_construction_proportion' },
      { key: 'land_degradation', name: '土地退化指数', calculated: false, loading: false, apiKey: 'land_degradation_index' }
    ])
    
    // 计算结果
    const indexResults = reactive({})
    
    // 图表引用
    const radarChart = ref(null)
    const barChart = ref(null)
    // 移除 uploadRef，因为我们使用自定义的文件上传逻辑
    
    // 计算属性
    const hasResults = computed(() => Object.keys(indexResults).length > 0)
    const currentFileLabel = computed(() => {
      if (fileList.value.length > 0) {
        return `已选择: ${fileList.value[0].name}`
      }
      if (restoredFileName.value) {
        return `历史结果: ${restoredFileName.value}`
      }
      return '未选择文件'
    })
    const landuseClasses = computed(() => {
      const classes = landuseStatistics.value?.classes || {}
      return Object.entries(classes)
        .map(([id, item]) => ({ id, ...item }))
        .filter(item => item.pixels > 0)
        .sort((a, b) => b.area_km2 - a.area_km2)
    })
    
    // 方法
    const triggerFileUpload = () => {
      uploadLoading.value = true
      ElMessage.info('正在打开文件选择器...') // 用户反馈
      
      try {
        const input = document.createElement('input')
        input.type = 'file'
        input.accept = '.tif,.tiff,.zip'
        input.multiple = false
        input.style.display = 'none' // 隐藏input元素
        
        input.onchange = (e) => {
          const file = e.target.files[0]
          if (file) {
            if (beforeUpload(file)) {
              handleUploadSuccess({}, file)
            }
          }
        }
        
        // 添加到DOM中
        document.body.appendChild(input)
        input.click()
        
        // 清理DOM
        setTimeout(() => {
          if (document.body.contains(input)) {
            document.body.removeChild(input)
          }
        }, 1000)
      } catch (error) {
        console.error('文件上传错误:', error)
        ElMessage.error('文件上传失败，请重试')
      } finally {
        uploadLoading.value = false
      }
    }
    
    const beforeUpload = (file) => {
      const isValidFormat = /\.(tif|tiff|zip)$/i.test(file.name)
      if (!isValidFormat) {
        ElMessage.error('只支持 GeoTIFF(.tif/.tiff) 或 Shapefile 压缩包(.zip)，ADF请先转为GeoTIFF')
        return false
      }

      const maxSize = 10 * 1024 * 1024 * 1024
      if (file.size > maxSize) {
        ElMessage.error('当前演示上传限制为10GB；更大的栅格请先裁剪或走后台分块处理')
        return false
      }
      
      // 检查ZIP文件
      if (file.name.toLowerCase().endsWith('.zip')) {
        // 基本大小检查 (避免空文件)
        if (file.size < 100) {
          ElMessage.error('ZIP文件过小，请确保包含完整的Shapefile组件(.shp/.shx/.dbf/.prj)')
          return false
        }
        ElMessage.info('检测到Shapefile压缩包，请确保：1) 是真正的ZIP格式（不是RAR）2) 包含.shp/.shx/.dbf/.prj四个文件')
      }
      
      return true
    }
    
    const handleUploadSuccess = (response, file) => {
      ElMessage.success(`${file.name} 上传成功`)
      fileList.value = [file]
      restoredFileName.value = ''
    }
    
    // 移除 handleFileChange 函数，因为不再需要
    
    const testButtonClick = () => {
      ElMessage.success('测试按钮工作正常！')
      
      // 强制重置 globalLoading
      if (globalLoading.value) {
        globalLoading.value = false
        ElMessage.info('已重置加载状态')
      }
    }
    
    const clearFile = () => {
      fileList.value = []
      restoredFileName.value = ''
      // 清除计算结果
      Object.keys(indexResults).forEach(key => {
        delete indexResults[key]
      })
      landuseVisualizationUrl.value = ''
      landuseStatistics.value = null
      analysisMeta.value = null
      compareOverlay.value = null
      // 重置指数状态
      structureIndices.forEach(index => {
        index.calculated = false
        index.loading = false
      })
      stressIndices.forEach(index => {
        index.calculated = false
        index.loading = false
      })
      // 清除图表
      if (radarChart.value) {
        const radar = echarts.getInstanceByDom(radarChart.value)
        if (radar) radar.dispose()
      }
      if (barChart.value) {
        const bar = echarts.getInstanceByDom(barChart.value)
        if (bar) bar.dispose()
      }
      ElMessage.info('已清除文件，请重新选择')
    }

    const syncCalculatedStates = () => {
      const allIndices = [...structureIndices, ...stressIndices]
      allIndices.forEach(index => {
        index.calculated = indexResults[index.apiKey] !== undefined
        index.loading = false
      })
    }

    const buildHistoryPayload = () => ({
      fileName: fileList.value[0]?.name || restoredFileName.value || '生态环境指数结果',
      indexResults: { ...indexResults },
      landuseVisualizationUrl: landuseVisualizationUrl.value,
      landuseStatistics: landuseStatistics.value,
      analysisMeta: analysisMeta.value,
      compareOverlay: compareOverlay.value
    })

    const persistCurrentResult = () => {
      if (Object.keys(indexResults).length === 0) {
        return
      }

      const payload = buildHistoryPayload()
      historyItems.value = saveResultHistory(HISTORY_KEY, {
        id: `${payload.fileName}_${Date.now()}`,
        title: payload.fileName,
        subtitle: `${Object.keys(payload.indexResults).length} 项指标`,
        timestamp: Date.now(),
        payload
      })
    }

    const restoreHistoryItem = (item) => {
      const payload = item?.payload
      if (!payload?.indexResults) {
        ElMessage.warning('该历史结果已失效，请重新分析')
        return
      }

      fileList.value = []
      restoredFileName.value = payload.fileName || item.title || ''
      Object.keys(indexResults).forEach(key => {
        delete indexResults[key]
      })
      Object.assign(indexResults, payload.indexResults || {})
      landuseVisualizationUrl.value = payload.landuseVisualizationUrl || ''
      landuseStatistics.value = payload.landuseStatistics || null
      analysisMeta.value = payload.analysisMeta || null
      compareOverlay.value = payload.compareOverlay || null
      syncCalculatedStates()

      nextTick(() => {
        updateCharts()
      })
      ElMessage.success('已恢复历史结果，当前为只读查看状态')
    }

    const deleteHistoryItem = (item) => {
      historyItems.value = removeResultHistory(HISTORY_KEY, item.id)
      ElMessage.success('历史记录已删除')
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
      ElMessage.success('历史记录已清空')
    }
    
    const startAnalysis = async () => {
      if (fileList.value.length === 0) {
        ElMessage.warning('请先选择文件')
        return
      }
      
      globalLoading.value = true
      try {
        const file = fileList.value[0]
        const formData = new FormData()
        formData.append('landuse_file', file)
        
        ElMessage.info('正在计算生态环境指数...')
        const analysisResponse = await http.post(buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.LANDUSE_INDICES), formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          skipAuth: true
        })
        
        // 处理结果
        if (analysisResponse.summary) {
          // 合并所有指数结果
          Object.assign(indexResults, analysisResponse.summary)
          const visualization = analysisResponse.visualization
          landuseVisualizationUrl.value = visualization?.visualization_file_url || ''
          landuseStatistics.value = visualization?.landuse_statistics || null
          compareOverlay.value = visualization?.compare_overlay || null
          analysisMeta.value = analysisResponse.meta || null
          
          // 更新指数状态
          const allIndices = [...structureIndices, ...stressIndices]
          allIndices.forEach(index => {
            if (indexResults[index.apiKey] !== undefined) {
              index.calculated = true
            }
          })

          persistCurrentResult()
          
          ElMessage.success('分析完成！')
          
          // 更新图表
          nextTick(() => {
            updateCharts()
          })
        } else {
          throw new Error('API返回结果格式错误')
        }
      } catch (error) {
        console.error('分析失败:', error)
        
        // 详细的错误信息处理
        let errorMessage = '分析失败'
        if (error.response) {
          // 服务器响应了错误状态码
          const { status } = error.response
          errorMessage = `分析失败 (${status}): ${getRequestErrorMessage(error)}`
        } else if (error.request) {
          // 请求已发出但没有收到响应
          errorMessage = '分析失败: 无法连接到服务器，请检查网络连接'
        } else if (error.message) {
          // 其他错误
          errorMessage = `分析失败: ${error.message}`
        }
        
        ElMessage.error(errorMessage)
      } finally {
        globalLoading.value = false
      }
    }
    
    const calculateIndex = async (indexKey) => {
      const index = [...structureIndices, ...stressIndices].find(i => i.key === indexKey)
      if (!index) return
      
      if (fileList.value.length === 0) {
        ElMessage.warning('请先选择文件')
        return
      }
      
      index.loading = true
      try {
        const file = fileList.value[0]
        const formData = new FormData()
        formData.append('landuse_file', file)
        
        let response
        let apiEndpoint
        
        // 根据指数类型选择对应的API端点
        if (structureIndices.find(i => i.key === indexKey)) {
          apiEndpoint = buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.STRUCTURE_INDICES)
        } else {
          apiEndpoint = buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.STRESS_INDICES)
        }
        
        // 调用API
        response = await http.post(apiEndpoint, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          skipAuth: true
        })
        
        // 处理结果
        if (response.summary && response.summary[index.apiKey] !== undefined) {
          indexResults[index.apiKey] = response.summary[index.apiKey]
          if (response.visualization) {
            landuseVisualizationUrl.value = response.visualization.visualization_file_url || landuseVisualizationUrl.value
            landuseStatistics.value = response.visualization.landuse_statistics || landuseStatistics.value
            compareOverlay.value = response.visualization.compare_overlay || compareOverlay.value
          }
          if (response.meta) {
            analysisMeta.value = response.meta
          }
          index.calculated = true
          persistCurrentResult()
          
          ElMessage.success(`${index.name} 计算完成`)
          
          // 更新图表
          nextTick(() => {
            updateCharts()
          })
        } else {
          throw new Error('API返回结果中未找到对应指数')
        }
      } catch (error) {
        console.error(`${index.name} 计算失败:`, error)
        
        // 详细的错误信息处理
        let errorMessage = `${index.name} 计算失败`
        if (error.response) {
          // 服务器响应了错误状态码
          const { status } = error.response
          errorMessage = `${index.name} 计算失败 (${status}): ${getRequestErrorMessage(error)}`
        } else if (error.request) {
          // 请求已发出但没有收到响应
          errorMessage = `${index.name} 计算失败: 无法连接到服务器，请检查网络连接`
        } else if (error.message) {
          // 其他错误
          errorMessage = `${index.name} 计算失败: ${error.message}`
        }
        
        ElMessage.error(errorMessage)
      } finally {
        index.loading = false
      }
    }
    
    const getIndexName = (key) => {
      const allIndices = [...structureIndices, ...stressIndices]
      const index = allIndices.find(i => i.apiKey === key)
      return index ? index.name : key
    }
    
    const getStatusClass = (key, value) => {
      // 根据不同指数类型和值返回对应的状态类
      switch (key) {
        case 'fragmentation_index':
          // 破碎化指数：0表示完全未破碎，1表示极度破碎
          if (value === 0) return 'status-excellent' // 优：完全未破碎
          if (value < 0.3) return 'status-good'      // 良：轻微破碎
          if (value < 0.5) return 'status-moderate'  // 中：中度破碎
          if (value < 0.7) return 'status-poor'      // 差：严重破碎
          return 'status-bad'                        // 劣：极度破碎
        
        case 'shannon_diversity':
          // 多样性指数：值越高表示多样性越丰富
          if (value > 2.0) return 'status-excellent' // 优：非常丰富的多样性
          if (value > 1.5) return 'status-good'      // 良：较好的多样性
          if (value > 1.0) return 'status-moderate'  // 中：中等多样性
          if (value > 0.5) return 'status-poor'      // 差：较低多样性
          return 'status-bad'                        // 劣：极低多样性
          
        case 'cohesion_index':
          // 内聚力指数：后端返回百分制
          if (value === 0) return 'status-bad'
          if (value < 30) return 'status-poor'
          if (value < 50) return 'status-moderate'
          if (value < 80) return 'status-good'
          return 'status-excellent'
          
        case 'fragility_index':
          // 脆弱性指数：值越低表示抵抗力越强
          if (value < 0.2) return 'status-excellent' // 优：极低脆弱性
          if (value < 0.3) return 'status-good'      // 良：低脆弱性
          if (value < 0.5) return 'status-moderate'  // 中：中等脆弱性
          if (value < 0.7) return 'status-poor'      // 差：高脆弱性
          return 'status-bad'                        // 劣：极高脆弱性
          
        case 'soil_erosion_index':
          // 土壤侵蚀指数：值越低表示侵蚀程度越轻
          if (value < 0.2) return 'status-excellent' // 优：微度侵蚀
          if (value < 0.3) return 'status-good'      // 良：轻度侵蚀
          if (value < 0.5) return 'status-moderate'  // 中：中度侵蚀
          if (value < 0.7) return 'status-poor'      // 差：重度侵蚀
          return 'status-bad'                        // 劣：极重度侵蚀
          
        case 'land_degradation_index':
          // 土地退化指数：值越低表示退化程度越轻
          if (value < 0.2) return 'status-excellent' // 优：微度退化
          if (value < 0.3) return 'status-good'      // 良：轻度退化
          if (value < 0.5) return 'status-moderate'  // 中：中度退化
          if (value < 0.7) return 'status-poor'      // 差：重度退化
          return 'status-bad'                        // 劣：极重度退化
          
        case 'unused_land_proportion':
          // 未利用土地比例：按照生态环境评估界面标准
          if (value < 5) return 'status-excellent'   // 优：极低比例
          if (value < 10) return 'status-good'       // 良：低比例
          if (value < 15) return 'status-moderate'   // 中：中等比例
          if (value < 20) return 'status-poor'       // 差：高比例
          return 'status-bad'                        // 劣：极高比例
          
        case 'cultivated_construction_proportion':
          // 耕地与建设用地比例：按照生态环境评估界面标准
          if (value >= 35 && value <= 45) return 'status-excellent' // 优：最佳平衡
          if (value >= 30 && value < 35 || value > 45 && value <= 50) return 'status-good' // 良：良好平衡
          if (value >= 25 && value < 30 || value > 50 && value <= 55) return 'status-moderate' // 中：一般平衡
          if (value >= 20 && value < 25 || value > 55 && value <= 60) return 'status-poor' // 差：较差平衡
          return 'status-bad' // 劣：严重失衡
          
        default:
          // 默认情况
          return 'status-unknown'
      }
    }
    
    const getStatusText = (key, value) => {
      // 根据不同指数类型和值返回对应的状态文本
      switch (key) {
        case 'fragmentation_index':
          if (value === 0) return '优' 
          if (value < 0.3) return '良'
          if (value < 0.5) return '中'
          if (value < 0.7) return '差'
          return '劣'
        
        case 'shannon_diversity':
          if (value > 2.0) return '优'
          if (value > 1.5) return '良'
          if (value > 1.0) return '中'
          if (value > 0.5) return '差'
          return '劣'
          
        case 'cohesion_index':
          if (value === 0) return '劣'
          if (value < 30) return '差'
          if (value < 50) return '中'
          if (value < 80) return '良'
          return '优'
          
        case 'fragility_index':
          if (value < 0.2) return '优'
          if (value < 0.3) return '良'
          if (value < 0.5) return '中'
          if (value < 0.7) return '差'
          return '劣'
          
        case 'soil_erosion_index':
          if (value < 0.2) return '优'
          if (value < 0.3) return '良'
          if (value < 0.5) return '中'
          if (value < 0.7) return '差'
          return '劣'
          
        case 'land_degradation_index':
          if (value < 0.2) return '优'
          if (value < 0.3) return '良'
          if (value < 0.5) return '中'
          if (value < 0.7) return '差'
          return '劣'
          
        case 'unused_land_proportion':
          if (value < 5) return '优'
          if (value < 10) return '良'
          if (value < 15) return '中'
          if (value < 20) return '差'
          return '劣'
          
        case 'cultivated_construction_proportion':
          if (value >= 35 && value <= 45) return '优'
          if (value >= 30 && value < 35 || value > 45 && value <= 50) return '良'
          if (value >= 25 && value < 30 || value > 50 && value <= 55) return '中'
          if (value >= 20 && value < 25 || value > 55 && value <= 60) return '差'
          return '劣'
          
        default:
          return '未知'
      }
    }
    
    const getIndexUnit = (key) => {
      // 根据指数类型返回对应的单位
      const unitMap = {
        'fragmentation_index': '无单位',
        'cohesion_index': '%',
        'shannon_diversity': '无单位',
        'fragility_index': '无单位',
        'soil_erosion_index': '无单位',
        'unused_land_proportion': '%',
        'cultivated_construction_proportion': '%',
        'land_degradation_index': '无单位'
      }
      return unitMap[key] || '无单位'
    }

    const getScaleHint = (key) => {
      const hintMap = {
        'fragmentation_index': '理论范围 0-1，越低越完整',
        'cohesion_index': '百分制，越高越连通',
        'shannon_diversity': '通常 0-3，越高越多样',
        'fragility_index': '理论范围 0-1，越低越稳定',
        'soil_erosion_index': '理论范围 0-1，越低越安全',
        'unused_land_proportion': '面积占比，单位 %',
        'cultivated_construction_proportion': '面积占比，单位 %',
        'land_degradation_index': '理论范围 0-1，越低越安全'
      }
      return hintMap[key] || '请结合指标定义解读'
    }

    const formatIndexValue = (key, value) => {
      if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return '--'
      }
      const numericValue = Number(value)
      if (key === 'cohesion_index' || key === 'unused_land_proportion' || key === 'cultivated_construction_proportion') {
        return numericValue.toFixed(2)
      }
      return numericValue.toFixed(4)
    }

    const getPrecisionLabel = (precision) => {
      const labelMap = {
        full_resolution: '全分辨率统计',
        mixed_resolution: '全量统计 + 预览估算'
      }
      return labelMap[precision] || precision || '未知'
    }
    
    const downloadResults = () => {
      try {
        // 准备下载数据
        const downloadData = {
          timestamp: new Date().toISOString(),
          filename: fileList.value[0]?.name || 'unknown',
          results: indexResults,
          summary: {
            total_indices: Object.keys(indexResults).length,
            calculated_time: new Date().toLocaleString('zh-CN')
          }
        }
        
        // 创建Blob对象
        const blob = new Blob([JSON.stringify(downloadData, null, 2)], {
          type: 'application/json'
        })
        
        // 创建下载链接
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `ecological_indices_${new Date().getTime()}.json`
        document.body.appendChild(a)
        a.click()
        
        // 清理
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        
        ElMessage.success('计算结果已下载')
      } catch (error) {
        console.error('下载失败:', error)
        ElMessage.error('下载失败')
      }
    }
    
    const updateCharts = () => {
      if (Object.keys(indexResults).length === 0) return
      
      // 更新雷达图
      if (radarChart.value) {
        const radar = echarts.init(radarChart.value)
        const radarKeys = Object.keys(indexResults).filter(key => getIndexUnit(key) !== '%')
        const radarValues = radarKeys.map(key => Number(indexResults[key]) || 0)
        const maxValue = radarValues.length ? Math.max(...radarValues) : 1
        const chartMax = Math.max(1, Math.ceil(maxValue * 1.2 * 1000) / 1000)
        
        const radarOption = {
          title: { 
            text: '生态环境指数雷达图（非百分比项）',
            textStyle: { fontSize: 16, fontWeight: 'bold' }
          },
          radar: {
            indicator: radarKeys.map(key => ({
              name: getIndexName(key),
              max: chartMax
            })),
            radius: '60%',
            center: ['50%', '55%']
          },
          series: [{
            type: 'radar',
            data: [{
              value: radarValues,
              name: '指数值',
              areaStyle: { 
                opacity: 0.3,
                color: '#3b82f6'
              },
              lineStyle: {
                color: '#3b82f6',
                width: 2
              },
              itemStyle: {
                color: '#3b82f6'
              }
            }]
          }]
        }
        radar.setOption(radarOption)
      }
      
      // 更新柱状图
      if (barChart.value) {
        const bar = echarts.init(barChart.value)
        const orderedKeys = Object.keys(indexResults)
        
        // 为不同类型的指数设置不同的颜色
        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316']
        
        const barOption = {
          title: { 
            text: '生态环境指数对比',
            textStyle: { fontSize: 16, fontWeight: 'bold' }
          },
          tooltip: {
            trigger: 'axis',
            formatter: function(params) {
              const data = params[0]
              const key = orderedKeys[data.dataIndex]
              return `${data.name}<br/>${formatIndexValue(key, data.value)} ${getIndexUnit(key)}`
            }
          },
          xAxis: {
            type: 'category',
            data: orderedKeys.map(key => getIndexName(key)),
            axisLabel: { 
              rotate: 45,
              fontSize: 12
            }
          },
          yAxis: { 
            type: 'value',
            name: '混合量纲，请结合卡片单位查看'
          },
          series: [{
            type: 'bar',
            data: orderedKeys.map((key, index) => ({
              value: Number(indexResults[key]) || 0,
              itemStyle: { 
                color: colors[index % colors.length]
              }
            })),
            barWidth: '60%'
          }]
        }
        bar.setOption(barOption)
      }
    }
    

    
    // 生命周期
    onMounted(() => {
      historyItems.value = loadResultHistory(HISTORY_KEY)
      // 初始化图表
      nextTick(() => {
        updateCharts()
      })
    })
    
    return {
      fileList,
      globalLoading,
      uploadLoading,
      restoredFileName,
      historyItems,
      historyExpanded,
      structureIndices,
      stressIndices,
      indexResults,
      hasResults,
      currentFileLabel,
      compareOverlay,
      landuseVisualizationUrl,
      landuseClasses,
      analysisMeta,
      radarChart,
      barChart,
      triggerFileUpload,
      beforeUpload,
      testButtonClick,
      clearFile,
      clearHistoryItems,
      deleteHistoryItem,
      restoreHistoryItem,
      formatHistoryTime,
      startAnalysis,
      calculateIndex,
      getIndexName,
      getStatusClass,
      getStatusText,
      getIndexUnit,
      getScaleHint,
      formatIndexValue,
      getPrecisionLabel,
      downloadResults
    }
  }
}
</script>

<style scoped>
.ecological-analysis {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #f4f7fa;
}

.ecological-container {
  display: flex;
  width: 100%;
  height: 100%;
  min-width: 1200px;
}

/* 左侧控制面板 */
.left-panel {
  width: 360px;
  background: #ffffff;
  border-right: 1px solid #dbe6f0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  box-shadow: 2px 0 12px rgba(15, 23, 42, 0.06);
}

/* 自定义滚动条样式 */
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

/* 自定义滚动条样式 */
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

.re-upload-btn {
  width: 100%;
  height: 34px;
  background: #f7fafc;
  border: 1px solid #dbe6f0;
  color: #5f7184;
  font-weight: 600;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.re-upload-btn:hover {
  background: #eef5fb;
  border-color: #bfd5e8;
  color: #315f8c;
  transform: translateY(-1px);
}

.upload-btn {
  width: 100%;
  height: 48px;
  background: #3b82f6 !important;
  border: none !important;
  color: white !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  transition: all 0.2s ease !important;
  position: relative !important;
  z-index: 100 !important;
  cursor: pointer !important;
  font-size: 16px !important;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
}

.upload-btn:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

.test-btn {
  width: 100%;
  height: 32px;
  background: #f59e0b;
  border: none;
  color: white;
  font-weight: 500;
  border-radius: 6px;
  transition: all 0.2s ease;
  margin-top: 8px;
}

.test-btn:hover {
  background: #d97706;
  transform: translateY(-1px);
}

.debug-info {
  text-align: center;
  padding: 8px;
  background: #f3f4f6;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #6b7280;
}

.upload-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
}

.file-status {
  font-size: 12px;
  color: #5f7184;
  text-align: center;
  padding: 9px 12px;
  background: #f7fafc;
  border-radius: 8px;
  border: 1px solid #dbe6f0;
}

.start-analysis-btn {
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

.start-analysis-btn:hover:not(:disabled) {
  background: #3389dd;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(31, 120, 209, 0.2);
}

.start-analysis-btn:disabled {
  background: #f5f5f5;
  color: #999;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
  cursor: not-allowed;
}

.history-card {
  padding: 14px;
  border: 1px solid #dbe6f0;
  border-radius: 12px;
  background: #ffffff;
}

.history-card__title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.history-card__icon {
  width: 18px;
  height: 18px;
  color: #4f79b5;
}

.history-card__title {
  font-size: 20px;
  font-weight: 700;
  color: #1f3c63;
}

.history-card__summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 18px;
}

.history-card__count,
.history-card__actions {
  font-size: 14px;
  color: #6f8192;
}

.history-card__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.history-card__description {
  margin-top: 12px;
  font-size: 14px;
  line-height: 1.7;
  color: #7a8fa5;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 240px;
  margin-top: 16px;
  overflow-y: auto;
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
  background: #ffffff;
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
  margin-top: 16px;
  padding: 16px 12px;
  border: 1px dashed #dbe6f0;
  border-radius: 10px;
  background: #ffffff;
  color: #8a98a8;
  font-size: 13px;
  text-align: center;
}

/* 指数选择区域 */
.index-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
  width: 100%;
  box-sizing: border-box;
}

.index-group:last-child {
  margin-bottom: 0;
}

.group-title {
  font-size: 13px;
  font-weight: 700;
  color: #4c6278;
  margin: 0 0 8px 0;
}

.index-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  margin: 0;
  padding: 0;
}

.index-btn {
  width: 100% !important;
  min-width: 100% !important;
  max-width: 100% !important;
  height: 42px !important;
  text-align: center !important;
  padding: 0 16px !important;
  border-radius: 8px;
  transition: all 0.2s ease;
  background: #f8fbfd !important;
  border: 1px solid #dbe6f0 !important;
  color: #2f455c !important;
  margin: 0 !important;
  box-sizing: border-box !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.index-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  background: #eef5fb !important;
  border-color: #bfd5e8 !important;
  color: #315f8c !important;
  box-shadow: 0 6px 16px rgba(49, 95, 140, 0.08);
}

.index-btn:disabled {
  background: #f5f5f5 !important;
  color: #999 !important;
  cursor: not-allowed;
  transform: none;
}

/* 确保所有按钮完全对齐 */
.index-buttons .el-button {
  width: 100% !important;
  min-width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 16px !important;
  box-sizing: border-box !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

/* 右侧结果展示区域 */
.right-panel {
  flex: 1;
  position: relative;
  background: #f4f7fa;
  min-height: 500px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
  min-width: 0;
  overflow-y: auto;
  padding: 20px;
}

/* 右侧结果区域滚动条样式 */
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

.results-area {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.results-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
}

/* 右侧结果区域滚动条样式 */
.results-content::-webkit-scrollbar {
  width: 6px;
}

.results-content::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.results-content::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.results-content::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.placeholder {
  height: 100%;
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
  box-shadow: 0 8px 20px rgba(30, 50, 70, 0.05);
}

/* 结果展示样式 */
.index-values {
  margin-bottom: 32px;
  width: 100%;
}

.visualization-card,
.landuse-table-card {
  margin-bottom: 24px;
  padding: 20px;
  border: 1px solid #dbe6f0;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(30, 50, 70, 0.06);
}

.landuse-visualization {
  display: block;
  width: 100%;
  max-height: 520px;
  object-fit: contain;
  border-radius: 6px;
  background: #fff;
}

.landuse-table {
  display: flex;
  flex-direction: column;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
}

.table-row {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr 1fr;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid #eef2f7;
  color: #374151;
  font-size: 13px;
}

.table-row:last-child {
  border-bottom: none;
}

.table-head {
  color: #26384a;
  font-weight: 700;
  background: #f3f8fc;
}

.values-title {
  font-size: 18px;
  font-weight: 700;
  color: #26384a;
  margin-bottom: 18px;
}

.values-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.value-item {
  background: #ffffff;
  padding: 20px;
  border-radius: 10px;
  border: 1px solid #dbe6f0;
  text-align: center;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-shadow: 0 8px 20px rgba(30, 50, 70, 0.05);
}

.value-name {
  font-size: 14px;
  color: #667789;
  margin-bottom: 12px;
  font-weight: 600;
  line-height: 1.3;
}

.value-number {
  font-size: 32px;
  font-weight: 700;
  color: #26384a;
  margin-bottom: 12px;
  line-height: 1.2;
}

.value-status {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 600;
  display: inline-block;
  margin-bottom: 8px;
  min-width: 50px;
}

.value-unit {
  font-size: 12px;
  color: #8a98a8;
  font-weight: 500;
}

.value-scale {
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.4;
  color: #8fa1b3;
}

.analysis-meta-card {
  background: linear-gradient(180deg, #f7fbff 0%, #ffffff 100%);
  border: 1px solid #d7e7f6;
  border-radius: 12px;
  padding: 20px 22px;
  margin-bottom: 24px;
  box-shadow: 0 10px 24px rgba(31, 120, 209, 0.08);
}

.meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(148, 184, 216, 0.18);
}

.meta-row:last-of-type {
  border-bottom: none;
}

.meta-label {
  font-size: 13px;
  color: #5d7286;
  font-weight: 600;
}

.meta-value {
  font-size: 14px;
  color: #22405f;
  font-weight: 700;
}

.meta-notes {
  margin-top: 14px;
  display: grid;
  gap: 8px;
}

.meta-note {
  font-size: 13px;
  line-height: 1.6;
  color: #4f6478;
  background: rgba(224, 239, 252, 0.65);
  border-radius: 10px;
  padding: 10px 12px;
}

.status-excellent {
  background: #dcfce7;
  color: #166534;
}

.status-good {
  background: #e6f7ff;
  color: #1890ff;
}

.status-moderate {
  background: #fffbe6;
  color: #faad14;
}

.status-poor {
  background: #fff7e6;
  color: #fa8c16;
}

.status-bad {
  background: #fff1f0;
  color: #f5222d;
}

.status-unknown {
  background: #f5f5f5;
  color: #999;
}

/* 图表区域 */
.charts-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.chart-container {
  background: #ffffff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #dbe6f0;
  box-shadow: 0 10px 24px rgba(30, 50, 70, 0.06);
}

.chart-title {
  font-size: 16px;
  font-weight: 700;
  color: #26384a;
  margin-bottom: 16px;
  text-align: center;
}

.chart {
  height: 300px;
  width: 100%;
}

/* 下载区域 */
.download-section {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #dbe6f0;
}

/* 移除不再需要的loading-container样式 */

.download-btn {
  height: 42px;
  padding: 0 24px;
  background: #1f78d1;
  border: none;
  color: white;
  font-weight: 600;
  border-radius: 8px;
  transition: all 0.2s ease;
  box-shadow: 0 4px 10px rgba(31, 120, 209, 0.18);
}

.download-btn:hover {
  background: #3389dd;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(31, 120, 209, 0.2);
}

/* 响应式设计 */
@media (max-width: 1000px) {
  .ecological-analysis {
    flex-direction: column;
  }
  
  .left-panel {
    width: 100%;
    height: auto;
    max-height: 50vh;
    order: 2;
  }
  
  .right-panel {
    order: 1;
    height: 50vh;
    min-height: 50vh;
  }
  
  .values-grid {
    grid-template-columns: repeat(3, 1fr);
    max-width: 100%;
    gap: 16px;
  }
}

@media (max-width: 1200px) {
  .values-grid {
    grid-template-columns: repeat(2, 1fr);
    max-width: 100%;
    gap: 18px;
  }
}

@media (max-width: 900px) {
  .values-grid {
    grid-template-columns: 1fr;
    max-width: 100%;
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .left-panel {
    max-height: 40vh;
  }
  
  .right-panel {
    height: 60vh;
    min-height: 60vh;
  }
  
  .values-grid {
    grid-template-columns: 1fr;
    max-width: 100%;
  }
  
  .chart {
    height: 250px;
  }
}
</style>

