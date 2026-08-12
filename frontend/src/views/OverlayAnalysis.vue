<template>
  <div class="overlay-analysis">
    <div class="main-container">
      <!-- 左侧控制面板 -->
      <div class="left-panel">
        <!-- 标题栏 -->
        <div class="panel-header">
          <RouterLink to="/" class="back-home-link" title="返回主界面">
            <ArrowLeft class="back-home-icon" />
            <span>主界面</span>
          </RouterLink>
          <h1>重大工程叠加分析</h1>
          <p>系统支持挂接最近一次或指定影像的 RSEI 结果，并叠加经济数据与工程项目数据进行风险分析。</p>
        </div>
        
        <!-- 图层控制 -->
        <div class="section">
          <div class="section-header">
            <MapLocation class="section-icon" />
            <span>图层控制</span>
          </div>
          <div class="section-content">
            <div class="layer-control">
              <div class="layer-item layer-item--stacked">
                <div class="layer-item-main">
                  <div class="layer-info">
                    <span>遥感影像底图</span>
                  </div>
                  <div class="layer-controls">
                    <label class="toggle-switch">
                      <input
                        type="checkbox"
                        v-model="layerVisibility.referenceImagery"
                        @change="handleLayerToggle('referenceImagery')"
                      />
                      <span class="slider"></span>
                    </label>
                  </div>
                </div>
                <div class="layer-item-extra">
                  <label class="mini-opacity-control">
                    <span>透明度</span>
                    <input v-model="layerOpacity.referenceImagery" type="range" min="35" max="100" step="5" />
                    <strong>{{ layerOpacity.referenceImagery }}%</strong>
                  </label>
                </div>
              </div>
              <div class="layer-item">
                <div class="layer-info">
                  <span>生态指数栅格</span>
                </div>
                <div class="layer-controls">
                  <label class="toggle-switch">
                    <input 
                      type="checkbox" 
                      v-model="layerVisibility.ecology" 
                      @change="handleLayerToggle('ecology')" 
                    />
                    <span class="slider"></span>
                  </label>
                </div>
              </div>
              <div class="layer-item layer-item--stacked">
                <div class="layer-item-main">
                  <div class="layer-info">
                    <span>生态栅格来源</span>
                  </div>
                  <div class="layer-controls">
                    <select
                      v-model="activeEcologyLayerKey"
                      class="layer-source-select"
                      @change="handleEcologySourceChange"
                    >
                      <option value="ecology_synced">系统RSEI结果</option>
                      <option value="ecology_uploaded">上传生态栅格</option>
                    </select>
                  </div>
                </div>
              </div>
              <div class="layer-item">
                <div class="layer-info">
                  <span>经济数据矢量</span>
                </div>
                <div class="layer-controls">
                  <label class="toggle-switch">
                    <input 
                      type="checkbox" 
                      v-model="layerVisibility.economy" 
                      @change="handleLayerToggle('economy')" 
                    />
                    <span class="slider"></span>
                  </label>
                </div>
              </div>
              <div class="layer-item">
                <div class="layer-info">
                  <span>工程项目矢量</span>
                </div>
                <div class="layer-controls">
                  <label class="toggle-switch">
                    <input 
                      type="checkbox" 
                      v-model="layerVisibility.engineering" 
                      @change="handleLayerToggle('engineering')" 
                    />
                    <span class="slider"></span>
                  </label>
                </div>
              </div>
            </div>
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
                打开或关闭图层后，这里会保留你最近一次的叠加视图
              </div>
            </div>
          </div>
        </div>

        <!-- 数据上传管理 -->
        <div class="section">
          <div class="section-header">
            <Upload class="section-icon" />
            <span>数据上传管理</span>
          </div>
          <div class="section-content">
            <DataUploadPanel
              :embedded="true"
              @refresh-map="handleRefreshMap"
            />
          </div>
        </div>

        <!-- 使用说明 -->
        <div class="section">
          <div class="section-header">
            <InfoFilled class="section-icon" />
            <span>使用说明</span>
          </div>
          <div class="section-content">
            <div class="usage-info">
              <p>1. 先在遥感生态指数分析模块完成一次 RSEI 计算</p>
              <p>2. 进入本页后，可直接同步最近一次 RSEI，或选择指定影像对应的 RSEI</p>
              <p>3. 上传经济数据矢量和工程项目矢量后，系统自动叠加显示</p>
              <p>4. 点击地图任意位置获取叠加分析信息、风险判断和决策建议</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧地图区域 -->
        <div class="map-area">
          <OverlayMapContainer
          ref="mapContainerRef"
          :layer-visibility="layerVisibility"
          :layer-opacity="layerOpacity"
          :active-ecology-layer-key="activeEcologyLayerKey"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ArrowLeft, FolderOpened, InfoFilled, MapLocation, Upload } from '@element-plus/icons-vue'
import OverlayMapContainer from '../components/Map/OverlayMapContainer.vue'
import DataUploadPanel from '../components/Map/DataUploadPanel.vue'
import { clearResultHistory, formatHistoryTime, loadResultHistory, removeResultHistory, saveResultHistory } from '../utils/resultHistory.js'

const mapContainerRef = ref(null)
const historyItems = ref([])
const historyExpanded = ref(false)
const HISTORY_KEY = 'overlay_analysis_view'
const activeEcologyLayerKey = ref('ecology_synced')

// 图层可见性控制
const layerVisibility = reactive({
  referenceImagery: false,
  ecology: false,
  economy: true,
  engineering: true
})

const layerOpacity = reactive({
  referenceImagery: 100,
  ecology: 88,
  economy: 60,
  engineering: 80
})

const persistCurrentView = () => {
  historyItems.value = saveResultHistory(HISTORY_KEY, {
    id: 'latest_overlay_view',
    title: '上次叠加视图',
    subtitle: buildHistorySubtitle(),
    timestamp: Date.now(),
    payload: {
      layerVisibility: { ...layerVisibility },
      layerOpacity: { ...layerOpacity },
      activeEcologyLayerKey: activeEcologyLayerKey.value
    }
  }, { maxItems: 1 })
}

const restoreHistoryItem = (item) => {
  const visibility = item?.payload?.layerVisibility
  if (!visibility) {
    return
  }
  const opacity = item?.payload?.layerOpacity || {}

  Object.assign(layerVisibility, {
    referenceImagery: !!visibility.referenceImagery,
    ecology: !!visibility.ecology,
    economy: !!visibility.economy,
    engineering: !!visibility.engineering
  })

  Object.assign(layerOpacity, {
    referenceImagery: Number(opacity.referenceImagery) || 100,
    ecology: Number(opacity.ecology) || 70,
    economy: Number(opacity.economy) || 60,
    engineering: Number(opacity.engineering) || 80
  })
  activeEcologyLayerKey.value = item?.payload?.activeEcologyLayerKey || 'ecology_synced'

  if (mapContainerRef.value) {
    mapContainerRef.value.refreshMap()
  }
}

const deleteHistoryItem = (item) => {
  historyItems.value = removeResultHistory(HISTORY_KEY, item.id)
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
}

const buildHistorySubtitle = () => {
  const labels = []
  if (layerVisibility.referenceImagery) labels.push('遥感影像底图')
  if (layerVisibility.ecology) {
    labels.push(activeEcologyLayerKey.value === 'ecology_uploaded' ? '上传生态栅格' : '系统RSEI结果')
  }
  if (layerVisibility.economy) labels.push('经济数据矢量')
  if (layerVisibility.engineering) labels.push('工程项目矢量')
  return labels.length > 0 ? labels.join('、') : '当前未开启任何业务图层'
}

const handleEcologySourceChange = () => {
  if (mapContainerRef.value) {
    mapContainerRef.value.refreshMap()
  }
  persistCurrentView()
}

// 处理图层切换
const handleLayerToggle = (layerType) => {
  if (mapContainerRef.value) {
    mapContainerRef.value.toggleLayer(layerType)
  }
  persistCurrentView()
}

// 处理地图刷新
const handleRefreshMap = (payload = {}) => {
  if (payload.type === 'ecology_synced' || payload.type === 'ecology_uploaded') {
    if (payload.action === 'updated') {
      layerVisibility.ecology = true
      activeEcologyLayerKey.value = payload.type
    } else if (payload.action === 'deleted' && activeEcologyLayerKey.value === payload.type) {
      layerVisibility.ecology = false
    }
  } else if (payload.action === 'deleted' && payload.type && layerVisibility[payload.type] !== undefined) {
    layerVisibility[payload.type] = false
  }
  if (payload.action === 'updated' && payload.type && layerVisibility[payload.type] !== undefined) {
    layerVisibility[payload.type] = true
  }
  if (mapContainerRef.value) {
    mapContainerRef.value.refreshMap()
  }
  persistCurrentView()
}

onMounted(() => {
  historyItems.value = loadResultHistory(HISTORY_KEY)
})

watch(layerOpacity, () => {
  persistCurrentView()
}, { deep: true })
</script>

<style scoped>
.overlay-analysis {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #f4f7fa;
}

.main-container {
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
  box-shadow: 2px 0 12px rgba(15, 23, 42, 0.06);
  overflow-y: auto;
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

/* 图层控制 */
.layer-control {
  display: flex;
  flex-direction: column;
  border: 1px solid #dbe6f0;
  border-radius: 10px;
  background: #f8fbfd;
  padding: 0 12px;
}

.layer-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid #edf2f7;
  gap: 8px;
}

.layer-item:last-child {
  border-bottom: none;
}

.layer-item--stacked {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}

.layer-item-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.layer-item-extra {
  display: flex;
  justify-content: flex-end;
}

.layer-source-select {
  min-width: 170px;
  min-height: 34px;
  padding: 0 10px;
  border: 1px solid #d5e1ed;
  border-radius: 8px;
  background: #fff;
  color: #44515f;
  font-size: 12px;
  outline: none;
}

.layer-source-select:focus {
  border-color: #1f78d1;
  box-shadow: 0 0 0 3px rgba(31, 120, 209, 0.12);
}

.layer-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #44515f;
  flex: 1;
  min-width: 0;
}

.layer-controls {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 20px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
  border-radius: 20px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #1f78d1;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

.mini-opacity-control {
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid #d5e1ed;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #556779;
  background: #fff;
  font-size: 12px;
}

.mini-opacity-control input {
  width: 90px;
}

.mini-opacity-control strong {
  min-width: 34px;
  text-align: right;
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
  max-height: 220px;
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
}

.history-item-subtitle,
.history-item-time {
  margin-top: 4px;
  font-size: 12px;
  color: #6f8192;
  line-height: 1.5;
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

/* 使用说明 */
.usage-info {
  font-size: 13px;
  color: #667789;
  line-height: 1.75;
  padding: 14px 14px 14px 16px;
  border: 1px solid #dbe6f0;
  border-radius: 10px;
  background: #f8fbfd;
}

.usage-info p {
  margin: 8px 0;
  padding-left: 8px;
  position: relative;
}

.usage-info p::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #1890ff;
  font-weight: bold;
}

/* 右侧地图区域 */
.map-area {
  flex: 1;
  position: relative;
  background: #f4f7fa;
  min-width: 0;
  overflow: hidden;
}
</style>
