<template>
  <div class="analysis-sidebar">
    <!-- 页面标题 -->
    <div class="panel-header">
      <RouterLink to="/" class="back-home-link" title="返回主界面">
        <ArrowLeft class="back-home-icon" />
        <span>主界面</span>
      </RouterLink>
      <h1>遥感生态指数分析</h1>
      <p class="panel-subtitle">上传遥感影像数据，系统将自动提取多种生态指数并进行可视化。</p>
    </div>

    <!-- 数据文件管理 -->
    <div class="section">
      <div class="section-title">
        <Files class="section-icon" />
        <span>数据文件管理</span>
      </div>

      <!-- 文件上传区域 -->
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
          <div class="upload-text">上传遥感影像文件</div>
          <div class="upload-hint">拖放文件到此处或点击选择文件</div>
          <div class="upload-types">支持 .tif/.tiff 多波段影像或成果栅格；ADF请上传完整文件夹ZIP</div>
        </div>
        <input 
          ref="fileInput" 
          type="file" 
          accept=".tif,.tiff,.jpg,.jpeg,.png,.zip" 
          style="display: none"
          @change="handleFileChange"
        >
        <div v-if="fileName" class="file-status">{{ fileName }}</div>
      </div>
    </div>

    <!-- 数据分析控制 -->
    <div class="section">
      <div class="section-title">
        <Search class="section-icon" />
        <span>数据分析控制</span>
      </div>

      <button
        class="analysis-btn"
        :disabled="!fileName || uploading"
        @click="$emit('start-analysis')"
      >
        {{ uploading ? '分析中...' : '开始分析' }}
      </button>
    </div>

    <!-- 指数选择 -->
    <div class="section">
      <div class="section-title">
        <TrendCharts class="section-icon" />
        <span>指数选择</span>
      </div>

      <div class="index-group">
        <div class="group-title">生态指数类型</div>
        <div class="index-buttons">
          <button
            v-for="option in indexOptions"
            :key="option.key"
            class="index-btn"
            :class="{ active: localIndex === option.key }"
            :disabled="disabledIndices.includes(option.key)"
            @click="onIndexChange(option.key)"
          >
            <span class="btn-text">{{ option.label }}</span>
            <el-tag v-if="cachedIndices.includes(option.key)" size="small" type="success" class="cache-tag">已缓存</el-tag>
          </button>
        </div>
        <div v-if="capabilitiesKnown" class="supported-hint">
          {{ supportedIndexLabels.length > 0 ? `当前影像支持：${supportedIndexLabels.join('、')}` : '当前影像暂不支持多波段生态指数计算，请确认上传的是原始多波段遥感影像。' }}
        </div>
      </div>
    </div>

    <!-- 缓存管理 -->
    <div class="section">
      <div class="history-card">
        <div class="history-card__title-row">
          <FolderOpened class="history-card__icon" />
          <div class="history-card__title">最近结果</div>
        </div>
        <div class="history-card__summary-row">
          <span class="history-card__count">{{ historyItems.length }} 条</span>
          <div class="history-card__actions">
            <button
              v-if="historyExpanded && historyItems.length > 0"
              type="button"
              class="history-text-btn"
              @click="$emit('clear-history')"
            >
              清空
            </button>
            <button
              type="button"
              class="history-toggle-btn"
              @click="$emit('toggle-history')"
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
            :key="`${item.imageId}_${item.indexType}_${item.timestamp}`"
            class="history-item"
          >
            <button
              type="button"
              class="history-item__main"
              @click="$emit('restore-history', item)"
            >
              <div class="history-item__title">{{ item.fileName || '未命名影像' }}</div>
              <div class="history-item__meta">
                <span>{{ getIndexLabel(item.indexType) }}</span>
                <span>{{ formatHistoryTime(item.timestamp) }}</span>
              </div>
            </button>
            <button
              type="button"
              class="history-delete-btn"
              @click="$emit('delete-history', item)"
            >
              删除
            </button>
          </div>
        </div>
        <div v-else-if="historyExpanded" class="history-empty">
          当前还没有可恢复的分析结果
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { ArrowLeft, FolderOpened, Files, Search, TrendCharts } from '@element-plus/icons-vue';
import { formatHistoryTime } from '../../utils/resultHistory.js';

const props = defineProps({
  selectedIndex: String,
  fileName: String,
  uploading: Boolean,
  indexOptions: {
    type: Array,
    default: () => []
  },
  cachedIndices: {
    type: Array,
    default: () => []
  },
  disabledIndices: {
    type: Array,
    default: () => []
  },
  supportedIndexLabels: {
    type: Array,
    default: () => []
  },
  capabilitiesKnown: {
    type: Boolean,
    default: false
  },
  historyItems: {
    type: Array,
    default: () => []
  },
  historyExpanded: {
    type: Boolean,
    default: false
  }
});
const emit = defineEmits([
  'file-change',
  'start-analysis',
  'index-change',
  'clear-cache',
  'toggle-history',
  'clear-history',
  'delete-history',
  'restore-history'
]);

const localIndex = ref(props.selectedIndex || 'rsei');
watch(() => props.selectedIndex, (val) => {
  localIndex.value = val;
});

const fileInput = ref(null);

function triggerFileUpload() {
  fileInput.value.click();
}

function handleFileChange(event) {
  const file = event.target.files[0];
  if (file) {
    emit('file-change', file);
  }
}

function onIndexChange(val) {
  if (props.disabledIndices.includes(val)) {
    return;
  }
  emit('index-change', val);
}

function getIndexLabel(indexType) {
  const map = {
    rsei: '遥感生态指数 (RSEI)',
    ndvi: '绿化指数 (NDVI)',
    ndwi: '湿度指数 (NDWI)',
    dryness: '干度指数 (NDBSI)',
    heat: '热度指数 (LST)'
  };
  return map[String(indexType || '').toLowerCase()] || indexType || '未知指数';
}
</script>

<style scoped>
.analysis-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

/* 自定义滚动条样式 */
.analysis-sidebar::-webkit-scrollbar {
  width: 6px;
}

.analysis-sidebar::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.analysis-sidebar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.analysis-sidebar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.panel-header {
  background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
  color: white;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
}

.panel-header h1 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
}

.panel-subtitle {
  margin: 0;
  font-size: 12px;
  opacity: 0.9;
  line-height: 1.4;
}

/* 功能区块 */
.section {
  padding: 20px;
  border-bottom: 1px solid #f0f0f0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.section-icon {
  font-size: 16px;
}

/* 文件上传区域 */
.file-upload-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.upload-zone {
  width: 100%;
  background: #f8f9fa;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
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
  border-color: #1890ff;
  background: #f0f8ff;
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

.file-status {
  font-size: 12px;
  color: #666;
  text-align: center;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 4px;
  border-left: 3px solid #1890ff;
}

/* 分析按钮 */
.analysis-btn {
  width: 100%;
  background: #1890ff;
  color: white;
  border: none;
  padding: 14px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(24, 144, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.analysis-btn:hover:not(.disabled) {
  background: #40a9ff;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(24, 144, 255, 0.3);
}

.analysis-btn.disabled {
  cursor: not-allowed;
  background: #d9d9d9;
  color: #999;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

/* 指数选择区域 */
.index-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.index-group:last-child {
  margin-bottom: 0;
}

.group-title {
  font-size: 14px;
  font-weight: 500;
  color: #555;
  margin: 0 0 8px 0;
}

.index-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.supported-hint {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f6fbff;
  border: 1px solid #d6e9f8;
  color: #4b6580;
  font-size: 12px;
  line-height: 1.6;
}

.index-btn {
  width: 100% !important;
  min-width: 100% !important;
  max-width: 100% !important;
  height: 40px !important;
  padding: 0 16px !important;
  border-radius: 6px;
  transition: all 0.2s ease;
  background: #f8f9fa !important;
  border: 1px solid #e9ecef !important;
  color: #333 !important;
  margin: 0 !important;
  box-sizing: border-box !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  cursor: pointer;
  position: relative;
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
  font-variant-numeric: tabular-nums;
}

.index-btn .btn-text {
  flex: 1;
  text-align: center;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.cache-tag {
  margin-left: 8px;
  flex-shrink: 0;
}

.index-btn:hover:not(:disabled) {
  transform: translateX(4px);
  background: #e6f7ff !important;
  border-color: #1890ff !important;
  color: #1890ff !important;
}

.index-btn.active {
  background: #1890ff !important;
  border-color: #1890ff !important;
  color: white !important;
}

.index-btn:disabled {
  background: #f5f5f5 !important;
  color: #999 !important;
  cursor: not-allowed;
  transform: none;
}


/* 缓存管理 */
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

.history-card__summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 18px;
}

.history-card__title {
  font-size: 20px;
  font-weight: 700;
  color: #1f3c63;
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

.history-text-btn,
.history-toggle-btn,
.history-delete-btn,
.history-item__main {
  font: inherit;
}

.history-text-btn,
.history-toggle-btn {
  padding: 0;
  border: none;
  background: transparent;
  color: #4a7db2;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.history-toggle-btn {
  color: #1f78d1;
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

.history-item {
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

.history-item__main {
  flex: 1;
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.history-item__main:hover {
  transform: translateY(-1px);
}

.history-item__title {
  font-size: 13px;
  font-weight: 700;
  color: #2f455c;
  line-height: 1.5;
  word-break: break-all;
}

.history-item__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 6px;
  font-size: 12px;
  color: #6f8192;
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
</style> 
