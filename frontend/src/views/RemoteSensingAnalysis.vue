<template>
  <ErrorBoundary>
    <div class="remote-sensing-analysis">
      <!-- 全局加载遮罩 -->
      <LoadingSpinner 
        v-if="globalLoading" 
        type="default" 
        :overlay="true" 
        text="系统处理中，请稍候..."
      />
      
      <!-- 左侧控制面板 -->
      <div class="control-panel">
        <AnalysisSidebar
          :selected-index="selectedIndex"
          :file-name="fileName"
          :uploading="uploading"
          :index-options="indexOptions"
          :cached-indices="cachedIndices"
          :disabled-indices="disabledIndices"
          :supported-index-labels="supportedIndexLabels"
          :capabilities-known="capabilitiesKnown"
          :history-items="historyItems"
          :history-expanded="historyExpanded"
          @file-change="handleFileChange"
          @start-analysis="handleStartAnalysis"
          @index-change="handleIndexChange"
          @clear-cache="clearCache"
          @toggle-history="historyExpanded = !historyExpanded"
          @clear-history="clearHistoryItems"
          @delete-history="deleteHistoryItem"
          @restore-history="restoreHistoryItem"
        />
      </div>
      
      <!-- 右侧结果区域 -->
      <div class="result-area">
        <!-- 分析进度 -->
        <div v-if="status === 'analyzing'" class="analysis-progress">
          <h3 class="progress-title">正在分析遥感影像...</h3>
          <ProgressBar
            :value="analysisProgress"
            title="分析进度"
            type="primary"
            :show-info="true"
            :current="`${Math.round(analysisProgress)}%`"
            :total="100"
            :speed="analysisSpeed"
            :eta="analysisEta"
            :show-actions="true"
            :can-pause="true"
            :can-cancel="true"
            @pause="pauseAnalysis"
            @resume="resumeAnalysis"
            @cancel="cancelAnalysis"
          />
          
          <div class="analysis-status">
            <p class="status-text">{{ currentStep }}</p>
            <p class="status-detail">{{ stepDetail }}</p>
          </div>
        </div>
        
        <!-- 分析结果 -->
        <AnalysisResult
          v-else
          :status="status"
          :result-data="resultData"
          :selected-index="selectedIndex"
          :task-id="currentTaskId"
        />
      </div>
    </div>
  </ErrorBoundary>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import AnalysisSidebar from '../components/RemoteSensing/AnalysisSidebar.vue';
import AnalysisResult from '../components/RemoteSensing/AnalysisResult.vue';
import LoadingSpinner from '../components/Common/LoadingSpinner.vue';
import ProgressBar from '../components/Common/ProgressBar.vue';
import ErrorBoundary from '../components/Common/ErrorBoundary.vue';
import { remoteSensingService, processingTaskService } from '../services/api.js';
import { useLoadingStore } from '../store/loading.js';
import { useMessageStore } from '../store/message.js';

const OVERLAY_RSEI_REFRESH_KEY = 'overlay_rsei_refresh_signal';
const ACTIVE_TASK_STORAGE_KEY = 'remote_sensing_active_task';
const CACHE_MAX_AGE_MS = 24 * 60 * 60 * 1000;
const INDEX_OPTIONS = [
  { key: 'rsei', label: '遥感生态指数 (RSEI)' },
  { key: 'ndvi', label: '绿化指数 (NDVI)' },
  { key: 'ndwi', label: '湿度指数 (NDWI)' },
  { key: 'dryness', label: '干度指数 (NDBSI)' },
  { key: 'heat', label: '热度指数 (LST)' }
];
const INDEX_LABEL_MAP = Object.fromEntries(INDEX_OPTIONS.map((item) => [item.key, item.label]));

// 状态管理
const loadingStore = useLoadingStore();
const messageStore = useMessageStore();

// 组件状态
const selectedIndex = ref('rsei');
const fileName = ref('');
const uploading = ref(false);
const status = ref('waiting'); // waiting | analyzing | done | error
const resultData = ref(null);
const currentTaskId = ref(null);
const currentFile = ref(null);
const currentImageId = ref(null); // 存储当前影像ID
const historyExpanded = ref(false);

// 结果缓存管理
const analysisResultsCache = ref(new Map()); // 存储不同指数类型的分析结果
const cacheKey = computed(() => {
  if (!currentImageId.value || !selectedIndex.value) return null;
  return `${currentImageId.value}_${selectedIndex.value.toLowerCase()}`;
});

// 分析进度相关
const analysisProgress = ref(0);
const analysisSpeed = ref('');
const analysisEta = ref('');
const currentStep = ref('准备分析环境...');
const stepDetail = ref('正在初始化分析参数');
const isPaused = ref(false);
const capabilitiesResolvedFromBackend = ref(false);
const supportedIndicesFromBackend = ref([]);
const supportedIndexLabelsFromBackend = ref([]);
const backendIndexMap = {
  ndvi: 'ndvi',
  ndwi: 'ndwi',
  ndbi: 'ndbi',
  heat: 'heat',
  dryness: 'dryness',
  wetness: 'wetness',
  greenness: 'greenness',
  rsei: 'rsei'
};
const indexOptions = INDEX_OPTIONS;
const allIndexKeys = INDEX_OPTIONS.map((item) => item.key);
const capabilitiesKnown = computed(() => capabilitiesResolvedFromBackend.value);
const supportedIndexLabels = computed(() => {
  if (supportedIndexLabelsFromBackend.value.length > 0) {
    return supportedIndexLabelsFromBackend.value;
  }
  return supportedIndicesFromBackend.value.map((key) => INDEX_LABEL_MAP[key] || key.toUpperCase());
});

const disabledIndices = computed(() => {
  if (!capabilitiesKnown.value) {
    return [];
  }

  const supported = new Set(supportedIndicesFromBackend.value);
  return allIndexKeys.filter((key) => !supported.has(key));
});

const cachedIndices = computed(() => {
  if (!currentImageId.value) {
    return [];
  }

  const now = Date.now();
  return allIndexKeys.filter((key) => {
    const cached = analysisResultsCache.value.get(`${currentImageId.value}_${key}`);
    return cached && now - cached.timestamp <= 24 * 60 * 60 * 1000;
  });
});
const historyItems = computed(() => {
  return Array.from(analysisResultsCache.value.values())
    .filter((item) => item?.resultData)
    .sort((a, b) => Number(b.timestamp || 0) - Number(a.timestamp || 0));
});

// 计算属性
const globalLoading = computed(() => loadingStore.globalLoading);

// 组件挂载时检查用户登录状态
onMounted(async () => {
  loadCacheFromStorage();
  await validateHistoryCacheInBackground();
  resumeActiveTask();
  
  // 调试信息
  console.log('组件挂载，当前状态:', {
    selectedIndex: selectedIndex.value,
    currentImageId: currentImageId.value,
    hasFile: !!currentFile.value
  });
});

function saveActiveTask(taskId, imageId, indexType, uploadedFileName) {
  localStorage.setItem(ACTIVE_TASK_STORAGE_KEY, JSON.stringify({
    taskId,
    imageId,
    indexType,
    uploadedFileName,
    timestamp: Date.now()
  }));
}

function clearActiveTask(taskId) {
  try {
    const activeTask = JSON.parse(localStorage.getItem(ACTIVE_TASK_STORAGE_KEY) || 'null');
    if (!taskId || activeTask?.taskId === taskId) {
      localStorage.removeItem(ACTIVE_TASK_STORAGE_KEY);
    }
  } catch (error) {
    localStorage.removeItem(ACTIVE_TASK_STORAGE_KEY);
  }
}

function resumeActiveTask() {
  try {
    const activeTask = JSON.parse(localStorage.getItem(ACTIVE_TASK_STORAGE_KEY) || 'null');
    if (!activeTask?.taskId || !activeTask?.imageId || !activeTask?.indexType) {
      return;
    }

    currentTaskId.value = activeTask.taskId;
    currentImageId.value = activeTask.imageId;
    selectedIndex.value = activeTask.indexType;
    fileName.value = activeTask.uploadedFileName || '';
    status.value = 'analyzing';
    currentStep.value = '正在恢复任务状态';
    stepDetail.value = '正在查询后台计算进度。';
    pollTaskStatus(activeTask.taskId, activeTask.imageId);
  } catch (error) {
    console.warn('Unable to restore background task:', error);
    localStorage.removeItem(ACTIVE_TASK_STORAGE_KEY);
  }
}

// 检查认证状态
function checkAuthStatus() {
  const token = localStorage.getItem('access_token');
  return !!token;
}

function notifyOverlayRSEIUpdate(payload = {}) {
  try {
    localStorage.setItem(OVERLAY_RSEI_REFRESH_KEY, JSON.stringify({
      timestamp: Date.now(),
      remote_sensing_image_id: payload.remote_sensing_image_id || '',
      remote_sensing_image_name: payload.remote_sensing_image_name || '',
      index_type: selectedIndex.value || '',
    }));
  } catch (error) {
    console.warn('写入叠加分析刷新信号失败:', error);
  }
}

function resetRemoteCapabilities() {
  capabilitiesResolvedFromBackend.value = false;
  supportedIndicesFromBackend.value = [];
  supportedIndexLabelsFromBackend.value = [];
}

function normalizeSupportedIndices(payload) {
  const rawIndices = payload?.supported_indices ?? payload?.source?.supported_indices ?? [];
  if (!Array.isArray(rawIndices)) {
    return [];
  }

  return [...new Set(
    rawIndices
      .map((item) => String(item || '').toLowerCase().trim())
      .filter((item) => allIndexKeys.includes(item))
  )];
}

function syncRemoteCapabilities(payload) {
  const hasIndices = Array.isArray(payload?.supported_indices) || Array.isArray(payload?.source?.supported_indices);
  const hasLabels = Array.isArray(payload?.supported_index_labels) || Array.isArray(payload?.source?.supported_index_labels);
  const normalizedIndices = normalizeSupportedIndices(payload);
  capabilitiesResolvedFromBackend.value = hasIndices || hasLabels;
  supportedIndicesFromBackend.value = normalizedIndices;

  const rawLabels = payload?.supported_index_labels ?? payload?.source?.supported_index_labels;
  if (Array.isArray(rawLabels) && rawLabels.length > 0) {
    supportedIndexLabelsFromBackend.value = rawLabels;
    return normalizedIndices;
  }

  supportedIndexLabelsFromBackend.value = normalizedIndices.map((key) => INDEX_LABEL_MAP[key] || key.toUpperCase());
  return normalizedIndices;
}

// 缓存管理函数
function saveAnalysisResult(resultData, imageId, indexType) {
  if (!resultData || !imageId || !indexType) {
    console.warn('保存缓存失败：缺少必要参数', { resultData: !!resultData, imageId, indexType });
    return;
  }
  
  const key = `${imageId}_${indexType.toLowerCase()}`;
  console.log(`保存缓存，键: ${key}, 影像ID: ${imageId}, 指数类型: ${indexType}`);
  
  // 检查是否已经有相同的缓存
  const existingCache = analysisResultsCache.value.get(key);
  if (existingCache && JSON.stringify(existingCache.resultData) === JSON.stringify(resultData)) {
    console.log(`缓存已存在且内容相同，跳过保存: ${key}`);
    return;
  }
  
  const cacheData = {
    resultData,
    imageId,
    indexType,
    timestamp: Date.now(),
    fileName: fileName.value
  };
  analysisResultsCache.value.set(key, cacheData);
  
  // 同时保存到localStorage作为持久化存储，使用单独的键以避免覆盖
  try {
    // 为每个指数类型使用单独的localStorage键
    const storageKey = `analysis_result_${imageId}_${indexType.toLowerCase()}`;
    
    // 直接保存当前指数的结果，不影响其他指数的缓存
    localStorage.setItem(storageKey, JSON.stringify(cacheData));
    
    console.log(`成功保存到localStorage，键: ${storageKey}`);
    
    // 同时维护一个索引，记录所有缓存的键
    let cacheIndex = [];
    try {
      const existingIndex = localStorage.getItem('analysis_cache_index');
      if (existingIndex) {
        cacheIndex = JSON.parse(existingIndex);
      }
    } catch (e) {
      console.warn('读取缓存索引失败，创建新索引');
    }
    
    // 添加当前键到索引（如果不存在）
    if (!cacheIndex.includes(storageKey)) {
      cacheIndex.push(storageKey);
      localStorage.setItem('analysis_cache_index', JSON.stringify(cacheIndex));
    }
    
    console.log('当前缓存索引:', cacheIndex);
  } catch (error) {
    console.warn('保存缓存到localStorage失败:', error);
  }
  
  console.log(`已保存${indexType}分析结果到缓存，键: ${key}`);
  console.log('当前缓存内容:', Array.from(analysisResultsCache.value.keys()));
  
  // 验证保存的缓存数据
  const savedCache = analysisResultsCache.value.get(key);
  if (savedCache) {
    console.log('验证保存的缓存数据:', {
      key,
      imageId: savedCache.imageId,
      indexType: savedCache.indexType,
      timestamp: new Date(savedCache.timestamp).toLocaleString(),
      hasResultData: !!savedCache.resultData,
      resultDataType: typeof savedCache.resultData,
      resultDataKeys: savedCache.resultData ? Object.keys(savedCache.resultData) : []
    });
  }
  
  // 立即测试读取缓存
  setTimeout(() => {
    const testResult = getCachedResult(imageId, indexType);
    console.log(`立即测试读取${indexType}缓存:`, testResult ? '成功' : '失败');
    if (testResult) {
      console.log('测试读取的缓存数据:', {
        imageId: testResult.imageId,
        indexType: testResult.indexType,
        hasResultData: !!testResult.resultData
      });
    }
  }, 100);
}

function normalizeCacheIndexType(indexType) {
  return String(indexType || '').toLowerCase();
}

function buildCacheMapKey(imageId, indexType) {
  return `${imageId}_${normalizeCacheIndexType(indexType)}`;
}

function buildCacheStorageKey(imageId, indexType) {
  return `analysis_result_${imageId}_${normalizeCacheIndexType(indexType)}`;
}

function removeStorageCacheKey(storageKey) {
  if (!storageKey) {
    return;
  }

  try {
    localStorage.removeItem(storageKey);
    const cacheIndex = JSON.parse(localStorage.getItem('analysis_cache_index') || '[]');
    const nextCacheIndex = Array.isArray(cacheIndex)
      ? cacheIndex.filter((key) => key !== storageKey)
      : [];
    localStorage.setItem('analysis_cache_index', JSON.stringify(nextCacheIndex));
  } catch (error) {
    console.warn('移除本地缓存键失败:', storageKey, error);
  }
}

function removeCachedEntry(imageId, indexType, options = {}) {
  if (!imageId || !indexType) {
    return;
  }

  const { notify = false, message = '历史记录已删除' } = options;
  const cacheMapKey = buildCacheMapKey(imageId, indexType);
  const storageKey = buildCacheStorageKey(imageId, indexType);

  analysisResultsCache.value.delete(cacheMapKey);
  removeStorageCacheKey(storageKey);

  if (notify) {
    messageStore.success(message);
  }
}

async function checkMediaFileAccessible(url) {
  const normalizedUrl = String(url || '').trim();
  if (!normalizedUrl) {
    return false;
  }

  try {
    const resolvedUrl = new URL(normalizedUrl, window.location.origin).toString();
    const headResponse = await fetch(resolvedUrl, {
      method: 'HEAD',
      cache: 'no-store'
    });

    if (headResponse.ok) {
      return true;
    }

    if (headResponse.status !== 405) {
      return false;
    }
  } catch (error) {
    console.warn('HEAD 校验媒体文件失败，尝试 GET:', normalizedUrl, error);
  }

  try {
    const resolvedUrl = new URL(normalizedUrl, window.location.origin).toString();
    const getResponse = await fetch(resolvedUrl, {
      method: 'GET',
      cache: 'no-store'
    });
    return getResponse.ok;
  } catch (error) {
    console.warn('GET 校验媒体文件失败:', normalizedUrl, error);
    return false;
  }
}

async function validateCachedResult(cacheItem, options = {}) {
  const { showMessage = false } = options;

  if (!cacheItem?.imageId || !cacheItem?.indexType || !cacheItem?.resultData) {
    removeCachedEntry(cacheItem?.imageId, cacheItem?.indexType);
    if (showMessage) {
      messageStore.warning('该历史结果已失效，请重新分析');
    }
    return null;
  }

  const normalizedIndex = normalizeCacheIndexType(cacheItem.indexType);
  const isExpired = Date.now() - Number(cacheItem.timestamp || 0) > CACHE_MAX_AGE_MS;
  if (isExpired) {
    removeCachedEntry(cacheItem.imageId, normalizedIndex);
    if (showMessage) {
      messageStore.warning('该历史结果缓存已过期，请重新分析');
    }
    return null;
  }

  try {
    const response = await remoteSensingService.getIndices(cacheItem.imageId);
    const remoteIndices = Array.isArray(response?.indices) ? response.indices : [];
    const matchedIndex = remoteIndices.find(
      (item) => normalizeCacheIndexType(item?.index_type) === normalizedIndex
    );

    if (!matchedIndex) {
      removeCachedEntry(cacheItem.imageId, normalizedIndex);
      if (showMessage) {
        messageStore.warning('该历史结果对应的后台数据已被清理，请重新分析');
      }
      return null;
    }

    const visualizationUrl = matchedIndex.visualization_file_url || matchedIndex.visualization_file || '';
    if (visualizationUrl) {
      const canLoadVisualization = await checkMediaFileAccessible(visualizationUrl);
      if (!canLoadVisualization) {
        removeCachedEntry(cacheItem.imageId, normalizedIndex);
        if (showMessage) {
          messageStore.warning('该历史结果图片文件已不存在，请重新分析');
        }
        return null;
      }
    }

    const refreshedResultData = {
      ...cacheItem.resultData,
      remote_sensing_image_id: cacheItem.imageId,
      indices: remoteIndices
    };
    const refreshedCacheItem = {
      ...cacheItem,
      indexType: normalizedIndex,
      resultData: refreshedResultData
    };

    const cacheMapKey = buildCacheMapKey(cacheItem.imageId, normalizedIndex);
    const storageKey = buildCacheStorageKey(cacheItem.imageId, normalizedIndex);
    analysisResultsCache.value.set(cacheMapKey, refreshedCacheItem);
    localStorage.setItem(storageKey, JSON.stringify(refreshedCacheItem));
    return refreshedCacheItem;
  } catch (error) {
    console.warn('校验历史缓存失败:', cacheItem.imageId, normalizedIndex, error);

    if (error?.response?.status === 404) {
      removeCachedEntry(cacheItem.imageId, normalizedIndex);
      if (showMessage) {
        messageStore.warning('该历史结果对应的后台记录已不存在，请重新分析');
      }
      return null;
    }

    if (showMessage) {
      messageStore.warning('暂时无法校验历史结果，请确认后端服务正常后重试');
    }
    return cacheItem;
  }
}

async function validateHistoryCacheInBackground() {
  const cacheItems = Array.from(analysisResultsCache.value.values());
  if (cacheItems.length === 0) {
    return;
  }

  for (const cacheItem of cacheItems) {
    await validateCachedResult(cacheItem, { showMessage: false });
  }
}

function getCachedResult(imageId, indexType) {
  const key = buildCacheMapKey(imageId, indexType);
  console.log(`查找缓存，键: ${key}, 影像ID: ${imageId}, 指数类型: ${indexType}`);
  
  // 记录当前所有缓存键
  const allCacheKeys = Array.from(analysisResultsCache.value.keys());
  console.log('当前内存缓存键列表:', allCacheKeys);
  
  // 尝试多种键格式
  const possibleKeys = [
    key,
    `${imageId}_${indexType}`, // 原始大小写
    `${imageId}_${indexType.toUpperCase()}`, // 大写
    `${imageId}_${indexType.toLowerCase()}` // 小写
  ];
  
  console.log('尝试的内存缓存键格式:', possibleKeys);
  
  let cached = null;
  let matchedKey = null;
  
  // 1. 首先尝试从内存缓存中获取
  for (const testKey of possibleKeys) {
    cached = analysisResultsCache.value.get(testKey);
    if (cached) {
      console.log(`在内存缓存中找到结果，使用键: ${testKey}`);
      matchedKey = testKey;
      break;
    }
  }
  
  // 2. 如果内存中没有，尝试从localStorage直接获取
  if (!cached) {
    console.log('内存缓存中未找到，尝试从localStorage读取');
    
    const storageKeys = [
      `analysis_result_${imageId}_${indexType.toLowerCase()}`,
      `analysis_result_${imageId}_${indexType}`,
      `analysis_result_${imageId}_${indexType.toUpperCase()}`
    ];
    
    for (const storageKey of storageKeys) {
      try {
        const storedData = localStorage.getItem(storageKey);
        if (storedData) {
          console.log(`在localStorage中找到结果，使用键: ${storageKey}`);
          const parsedData = JSON.parse(storedData);
          
          if (parsedData && parsedData.resultData) {
            // 将结果保存到内存缓存中
            const memKey = `${imageId}_${indexType.toLowerCase()}`;
            analysisResultsCache.value.set(memKey, parsedData);
            
            cached = parsedData;
            matchedKey = memKey;
            console.log(`已将localStorage数据加载到内存缓存，键: ${memKey}`);
            break;
          }
        }
      } catch (e) {
        console.warn(`读取localStorage键 ${storageKey} 失败:`, e);
      }
    }
  }
  
  // 3. 处理找到的缓存
  if (cached) {
    // 检查缓存是否过期（24小时）
    const isExpired = Date.now() - cached.timestamp > CACHE_MAX_AGE_MS;
    if (isExpired) {
      console.log(`缓存已过期，删除键: ${matchedKey}`);
      removeCachedEntry(imageId, indexType);
      return null;
    }
    
    console.log(`找到${indexType}缓存结果，键: ${matchedKey}`);
    console.log('缓存数据详情:', {
      imageId: cached.imageId,
      indexType: cached.indexType,
      timestamp: new Date(cached.timestamp).toLocaleString(),
      hasResultData: !!cached.resultData,
      dataSize: cached.resultData ? JSON.stringify(cached.resultData).length : 0
    });
    
    return cached;
  }
  
  console.log(`未找到${indexType}缓存结果，需要重新计算`);
  return null;
}

function clearCache() {
  // 清空内存中的缓存
  analysisResultsCache.value.clear();
  
  // 清空localStorage中的所有缓存
  try {
    // 先获取索引
    const cacheIndex = localStorage.getItem('analysis_cache_index');
    if (cacheIndex) {
      const cacheKeys = JSON.parse(cacheIndex);
      
      // 删除每个缓存项
      if (Array.isArray(cacheKeys)) {
        console.log('正在清除缓存项:', cacheKeys);
        cacheKeys.forEach(key => {
          localStorage.removeItem(key);
        });
      }
    }
    
    // 删除索引
    localStorage.removeItem('analysis_cache_index');
    
    // 兼容旧版缓存
    localStorage.removeItem('analysis_results_cache');
    
    console.log('所有缓存已清空');
  } catch (error) {
    console.warn('清除缓存失败:', error);
  }
  
  messageStore.success('已清空所有缓存结果');
}

function clearHistoryItems() {
  if (historyItems.value.length === 0) {
    return;
  }

  if (!window.confirm('确定要清空当前所有历史记录吗？')) {
    return;
  }

  clearCache();
}

function deleteHistoryItem(item) {
  if (!item?.imageId || !item?.indexType) {
    return;
  }

  removeCachedEntry(item.imageId, item.indexType, {
    notify: true,
    message: '历史记录已删除'
  });
}

async function restoreHistoryItem(item) {
  const validatedItem = await validateCachedResult(item, { showMessage: true });
  if (!validatedItem?.resultData) {
    return;
  }

  selectedIndex.value = String(validatedItem.indexType || 'rsei').toLowerCase();
  fileName.value = validatedItem.fileName || '';
  currentFile.value = null;
  currentImageId.value = validatedItem.imageId || null;
  currentTaskId.value = validatedItem.resultData?.result?.id || null;
  syncRemoteCapabilities(validatedItem.resultData);
  resultData.value = validatedItem.resultData;
  status.value = 'done';
  analysisProgress.value = 100;
  currentStep.value = '历史结果恢复完成';
  stepDetail.value = '当前显示的是本地缓存结果，如需重新计算请重新选择文件';
  messageStore.success('已恢复历史分析结果');
}

// 从localStorage加载缓存
function loadCacheFromStorage() {
  console.log('🔄 开始加载缓存...');
  
  try {
    // 初始化缓存Map
    analysisResultsCache.value = new Map();
    
    // 从索引中获取所有缓存键
    const cacheIndex = localStorage.getItem('analysis_cache_index');
    if (!cacheIndex) {
      console.log('未找到缓存索引，没有可加载的缓存');
      return;
    }
    
    let cacheKeys = [];
    try {
      cacheKeys = JSON.parse(cacheIndex);
      if (!Array.isArray(cacheKeys)) {
        console.warn('缓存索引格式无效，应为数组');
        return;
      }
    } catch (e) {
      console.warn('解析缓存索引失败:', e);
      return;
    }
    
    console.log('找到缓存索引，包含以下键:', cacheKeys);
    
    // 记录加载统计
    let loadedCount = 0;
    let failedCount = 0;
    
    // 加载每个缓存项
    for (const storageKey of cacheKeys) {
      try {
        const cachedData = localStorage.getItem(storageKey);
        if (!cachedData) {
          console.warn(`索引中的缓存键 ${storageKey} 不存在`);
          failedCount++;
          continue;
        }
        
        const cacheData = JSON.parse(cachedData);
        
        // 验证缓存数据
        if (!cacheData || !cacheData.imageId || !cacheData.indexType || !cacheData.resultData) {
          console.warn(`缓存键 ${storageKey} 的数据无效:`, cacheData);
          removeStorageCacheKey(storageKey);
          failedCount++;
          continue;
        }

        const isExpired = Date.now() - Number(cacheData.timestamp || 0) > CACHE_MAX_AGE_MS;
        if (isExpired) {
          console.warn(`缓存键 ${storageKey} 已过期，自动移除`);
          removeCachedEntry(cacheData.imageId, cacheData.indexType);
          failedCount++;
          continue;
        }
        
        // 构建内存缓存键
        const memKey = buildCacheMapKey(cacheData.imageId, cacheData.indexType);
        
        // 保存到内存缓存
        analysisResultsCache.value.set(memKey, cacheData);
        loadedCount++;
        
        console.log(`已加载缓存: ${storageKey} -> ${memKey}`, {
          imageId: cacheData.imageId,
          indexType: cacheData.indexType,
          timestamp: new Date(cacheData.timestamp).toLocaleString()
        });
      } catch (e) {
        console.warn(`加载缓存键 ${storageKey} 失败:`, e);
        failedCount++;
      }
    }
    
    console.log(`🔄 缓存加载完成，成功: ${loadedCount}, 失败: ${failedCount}, 总缓存数: ${analysisResultsCache.value.size}`);
    
    // 打印加载的所有缓存键
    if (analysisResultsCache.value.size > 0) {
      console.log('当前内存缓存键:', Array.from(analysisResultsCache.value.keys()));
      
      // 调试：打印每个缓存条目的详细信息
      analysisResultsCache.value.forEach((value, key) => {
        console.log(`缓存条目 ${key}:`, {
          imageId: value.imageId,
          indexType: value.indexType,
          timestamp: new Date(value.timestamp).toLocaleString(),
          hasResultData: !!value.resultData
        });
      });
    }
    
    // 尝试加载旧版缓存格式（兼容性）
    try {
      const oldCache = localStorage.getItem('analysis_results_cache');
      if (oldCache) {
        console.log('检测到旧版缓存格式，尝试加载...');
        const oldCacheArray = JSON.parse(oldCache);
        
        if (Array.isArray(oldCacheArray)) {
          let oldLoadedCount = 0;
          
          oldCacheArray.forEach(item => {
            if (Array.isArray(item) && item.length === 2) {
              const [key, value] = item;
              if (key && value && value.imageId && value.indexType && value.resultData) {
                // 检查是否已经加载过这个缓存
                const memKey = `${value.imageId}_${value.indexType.toLowerCase()}`;
                if (!analysisResultsCache.value.has(memKey)) {
                  analysisResultsCache.value.set(memKey, value);
                  oldLoadedCount++;
                  
                  // 同时迁移到新格式
                  const newStorageKey = `analysis_result_${value.imageId}_${value.indexType.toLowerCase()}`;
                  localStorage.setItem(newStorageKey, JSON.stringify(value));
                  
                  // 更新索引
                  if (!cacheKeys.includes(newStorageKey)) {
                    cacheKeys.push(newStorageKey);
                    localStorage.setItem('analysis_cache_index', JSON.stringify(cacheKeys));
                  }
                }
              }
            }
          });
          
          if (oldLoadedCount > 0) {
            console.log(`从旧版缓存加载了${oldLoadedCount}个缓存项`);
          }
        }
      }
    } catch (e) {
      console.warn('加载旧版缓存失败:', e);
    }
  } catch (error) {
    console.warn('从localStorage加载缓存失败:', error);
    // 如果加载失败，确保缓存Map被初始化为空
    analysisResultsCache.value = new Map();
  }
}

// 调试函数：打印当前缓存状态
function debugCacheStatus() {
  console.log('=== 缓存状态调试 ===');
  console.log('当前影像ID:', currentImageId.value);
  console.log('当前指数类型:', selectedIndex.value);
  console.log('预期缓存键:', cacheKey.value);
  
  // 检查内存缓存
  const memCacheEntries = Array.from(analysisResultsCache.value.entries());
  console.log(`内存缓存条目数: ${memCacheEntries.length}`);
  
  if (memCacheEntries.length > 0) {
    console.log('内存缓存键列表:', memCacheEntries.map(([key]) => key));
    
    // 显示每个缓存项的简要信息
    memCacheEntries.forEach(([key, value]) => {
      console.log(`内存缓存项 [${key}]:`, {
        imageId: value.imageId,
        indexType: value.indexType,
        timestamp: new Date(value.timestamp).toLocaleString(),
        hasResultData: !!value.resultData,
        dataSize: value.resultData ? JSON.stringify(value.resultData).length : 0
      });
    });
  }
  
  // 检查当前指数是否有缓存
  if (currentImageId.value && selectedIndex.value) {
    const key = `${currentImageId.value}_${selectedIndex.value.toLowerCase()}`;
    const hasCache = analysisResultsCache.value.has(key);
    console.log(`当前指数 ${selectedIndex.value} 是否有内存缓存:`, hasCache);
    
    if (hasCache) {
      const cache = analysisResultsCache.value.get(key);
      console.log('缓存数据详情:', {
        imageId: cache.imageId,
        indexType: cache.indexType,
        timestamp: new Date(cache.timestamp).toLocaleString(),
        hasResultData: !!cache.resultData,
        resultDataKeys: cache.resultData ? Object.keys(cache.resultData) : []
      });
    }
    
    // 检查localStorage中是否有当前指数的缓存
    try {
      const storageKey = `analysis_result_${currentImageId.value}_${selectedIndex.value.toLowerCase()}`;
      const storedData = localStorage.getItem(storageKey);
      console.log(`当前指数 ${selectedIndex.value} 是否有localStorage缓存:`, !!storedData);
      
      if (storedData) {
        console.log(`localStorage缓存大小: ${storedData.length} 字节`);
        try {
          const parsedData = JSON.parse(storedData);
          console.log('localStorage缓存数据有效:', !!parsedData);
        } catch (e) {
          console.warn('localStorage缓存数据解析失败:', e);
        }
      }
    } catch (e) {
      console.warn('检查localStorage缓存失败:', e);
    }
  }
  
  // 检查localStorage中的缓存索引
  try {
    const cacheIndex = localStorage.getItem('analysis_cache_index');
    if (cacheIndex) {
      const keys = JSON.parse(cacheIndex);
      console.log(`localStorage中的缓存索引包含 ${keys.length} 个键:`, keys);
      
      // 检查每个键的内容
      if (Array.isArray(keys)) {
        let validCount = 0;
        let invalidCount = 0;
        
        keys.forEach(key => {
          try {
            const item = localStorage.getItem(key);
            if (item) {
              validCount++;
              try {
                const data = JSON.parse(item);
                console.log(`localStorage缓存项 [${key}]:`, {
                  imageId: data.imageId,
                  indexType: data.indexType,
                  hasData: !!data.resultData,
                  timestamp: data.timestamp ? new Date(data.timestamp).toLocaleString() : 'unknown'
                });
              } catch (parseError) {
                console.warn(`解析缓存项 ${key} 失败:`, parseError);
              }
            } else {
              invalidCount++;
              console.log(`localStorage缓存项 ${key}: 不存在`);
            }
          } catch (e) {
            invalidCount++;
            console.log(`读取localStorage缓存项 ${key} 失败:`, e);
          }
        });
        
        console.log(`缓存索引验证: 有效 ${validCount}, 无效 ${invalidCount}`);
      }
    } else {
      console.log('localStorage中没有缓存索引');
    }
    
    // 检查localStorage存储使用情况
    let totalSize = 0;
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      const value = localStorage.getItem(key);
      totalSize += (key.length + value.length) * 2; // 估算字节大小
    }
    
    console.log(`localStorage使用情况: ${(totalSize / (1024 * 1024)).toFixed(2)} MB / 5 MB (估计)`);
  } catch (error) {
    console.log('读取localStorage缓存索引失败:', error);
  }
  
  console.log('==================');
}

// 处理文件选择
function handleFileChange(file) {
  if (file) {
    // 验证文件类型
    const allowedTypes = ['.tif', '.tiff', '.jpg', '.jpeg', '.png', '.zip'];
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    if (!allowedTypes.includes(fileExtension)) {
      messageStore.error('不支持的文件格式，请选择 .tif, .tiff, .jpg, .jpeg, .png，或ADF完整文件夹ZIP');
      return;
    }
    
    // 验证文件大小（后端会落盘并分块处理）
    const maxSize = 20 * 1024 * 1024 * 1024;
    if (file.size > maxSize) {
      messageStore.error('文件大小不能超过20GB；更大的遥感成果建议先裁剪或走后台分片上传');
      return;
    }
    
    currentFile.value = file;
    fileName.value = file.name;
    currentImageId.value = null;
    status.value = 'waiting';
    resultData.value = null;
    currentTaskId.value = null;
    analysisProgress.value = 0;
    resetRemoteCapabilities();

    messageStore.success('文件选择成功');
  }
}

// 开始分析
async function handleStartAnalysis() {
  if (!currentFile.value) {
    messageStore.error('请先选择文件');
    return;
  }

  if (capabilitiesKnown.value && disabledIndices.value.includes(selectedIndex.value)) {
    const supportedText = supportedIndexLabels.value.join('、');
    messageStore.warning(
      supportedText
        ? `当前影像不支持 ${INDEX_LABEL_MAP[selectedIndex.value] || selectedIndex.value}，请改选：${supportedText}`
        : '当前影像不支持所选指数，请切换后重试'
    );
    return;
  }
  
  try {
    // 在开始新分析前，保存当前结果到缓存（如果有的话）
    if (status.value === 'done' && resultData.value && currentImageId.value) {
      console.log('开始新分析前保存当前结果到缓存');
      
      // 强制保存当前结果，确保不会丢失
      const currentIndex = selectedIndex.value;
      const currentData = { ...resultData.value };
      const tempKey = `${currentImageId.value}_${currentIndex.toLowerCase()}`;
      
      // 直接构造缓存对象
      const cacheObj = {
        resultData: currentData,
        imageId: currentImageId.value,
        indexType: currentIndex,
        timestamp: Date.now(),
        fileName: fileName.value
      };
      
      // 保存到内存缓存
      analysisResultsCache.value.set(tempKey, cacheObj);
      
      // 保存到localStorage
      try {
        const storageKey = `analysis_result_${currentImageId.value}_${currentIndex.toLowerCase()}`;
        localStorage.setItem(storageKey, JSON.stringify(cacheObj));
        
        // 更新索引
        let cacheIndex = [];
        const existingIndex = localStorage.getItem('analysis_cache_index');
        if (existingIndex) {
          try {
            cacheIndex = JSON.parse(existingIndex);
          } catch (e) {
            console.warn('解析缓存索引失败，创建新索引');
            cacheIndex = [];
          }
        }
        
        if (!cacheIndex.includes(storageKey)) {
          cacheIndex.push(storageKey);
          localStorage.setItem('analysis_cache_index', JSON.stringify(cacheIndex));
        }
        
        console.log(`已强制保存${currentIndex}结果到缓存，键: ${storageKey}`);
      } catch (error) {
        console.error('保存缓存到localStorage失败:', error);
      }
    }
    
    uploading.value = true;
    status.value = 'analyzing';
    analysisProgress.value = 0;
    isPaused.value = false;
    
    console.log('开始分析，初始进度:', analysisProgress.value); // 添加调试日志
    
    currentStep.value = '上传并分析影像';
    stepDetail.value = '正在按公式计算指数并生成可视化结果...';
    analysisProgress.value = 15;

    const backendIndex = backendIndexMap[selectedIndex.value];
    if (!backendIndex) {
      throw new Error(`不支持的指数类型: ${selectedIndex.value}`);
    }

    console.log('本次提交的实际指数类型:', {
      selectedIndex: selectedIndex.value,
      backendIndex,
      fileName: currentFile.value?.name || ''
    });

    const uploadedImage = await remoteSensingService.upload(currentFile.value, {
      name: fileName.value || currentFile.value.name,
      image_type: 'custom'
    });
    currentImageId.value = uploadedImage?.id;
    if (!currentImageId.value) {
      throw new Error('上传响应中未返回影像 ID。');
    }

    const taskIndices = backendIndex === 'rsei'
      ? ['greenness', 'wetness', 'dryness', 'heat']
      : [backendIndex];
    const taskResponse = await remoteSensingService.calculateIndices(
      currentImageId.value,
      taskIndices
    );
    currentTaskId.value = taskResponse?.task_id;
    if (!currentTaskId.value) {
      throw new Error('任务创建响应中未返回任务 ID。');
    }

    saveActiveTask(
      currentTaskId.value,
      currentImageId.value,
      selectedIndex.value,
      fileName.value
    );
    currentStep.value = '任务已提交';
    stepDetail.value = '正在由后台计算，请稍候。';
    messageStore.success('分析任务已提交，可离开页面后稍后返回查看结果。');
    pollTaskStatus(currentTaskId.value, currentImageId.value);

    /* Legacy synchronous upload-and-analyze flow kept for reference.
    startProgressSimulator();
    const analyzeResult = await remoteSensingService.analyzeUpload(currentFile.value, backendIndex, {
      name: fileName.value || '未命名影像'
    });
    stopProgressSimulator();

    analysisProgress.value = 100;
    currentStep.value = '分析完成';
    stepDetail.value = '计算结果已生成';
    currentTaskId.value = analyzeResult?.result?.id || null;
    currentImageId.value = analyzeResult?.remote_sensing_image_id || `${fileName.value}_${backendIndex}`;
    const normalizedSupportedIndices = syncRemoteCapabilities(analyzeResult);
    resultData.value = {
      ...analyzeResult,
      remote_sensing_image_id: currentImageId.value,
      supported_indices: normalizedSupportedIndices,
      supported_index_labels: supportedIndexLabels.value,
    };
    status.value = 'done';
    if (backendIndex === 'rsei' && analyzeResult?.remote_sensing_image_id) {
      notifyOverlayRSEIUpdate({
        remote_sensing_image_id: analyzeResult.remote_sensing_image_id,
        remote_sensing_image_name: analyzeResult.remote_sensing_image_name
      });
    }
    if (analyzeResult?.preview_message) {
      messageStore.warning(analyzeResult.preview_message);
    }
    saveAnalysisResult(resultData.value, currentImageId.value, selectedIndex.value);
    messageStore.success('分析完成！');
    
    */
  } catch (error) {
    console.error('分析失败:', error);
    console.error('错误类型:', typeof error);
    console.error('错误消息:', error.message);
    console.error('错误堆栈:', error.stack);
    
    // 提取详细的错误信息
    let errorMessage = '分析失败，请重试';
    let errorDetails = '';
    
    if (error.response) {
      // 服务器响应了错误状态码
      const { status: responseStatus, data } = error.response;
      syncRemoteCapabilities(data);
      errorMessage = `服务器错误 (${responseStatus})`;
      
      if (data && data.error) {
        errorDetails = data.error;
      } else if (data && data.details) {
        errorDetails = data.details;
      } else if (data) {
        errorDetails = JSON.stringify(data);
      }
      if (Array.isArray(data?.supported_index_labels) && data.supported_index_labels.length > 0) {
        errorDetails = `${errorDetails} 建议选择：${data.supported_index_labels.join('、')}。`;
      }
      if (data?.bands_count) {
        errorDetails = `${errorDetails} 当前影像识别到 ${data.bands_count} 个波段。`.trim();
      }
      if (selectedIndex.value === 'rsei' && data?.bands_count === 1) {
        errorDetails = `${errorDetails} RSEI 需要原始多波段遥感影像，单波段成果栅格不会被系统作为可同步的 RSEI 结果保存。`.trim();
      }
      console.log('错误响应详情:', { status: responseStatus, data });
    } else if (error.request) {
      // 请求已发出但没有收到响应
      errorMessage = '无法连接到服务器';
      errorDetails = '请检查网络连接或确保后端服务正在运行';
      console.log('网络错误:', error.request);
    } else {
      // 其他错误
      errorMessage = error.message || '未知错误';
      console.log('其他错误:', error);
    }
    
    status.value = 'error';
    resultData.value = { 
      error: errorMessage,
      details: errorDetails,
      bands_count: error.response?.data?.bands_count,
      supported_indices: supportedIndicesFromBackend.value,
      supported_index_labels: supportedIndexLabels.value,
    };
    
    // 显示错误消息
    messageStore.error(`${errorMessage}${errorDetails ? ': ' + errorDetails : ''}`);
    
    // 如果是400错误，显示更多调试信息
    if (error.response && error.response.status === 400) {
      console.log('400错误详情:', {
        url: error.config?.url,
        method: error.config?.method,
        data: error.config?.data,
        headers: error.config?.headers
      });
    }
  } finally {
    uploading.value = false;
  }
}

// 模拟分析进度
async function simulateAnalysisProgress(steps) {
  for (let i = 0; i < steps.length; i++) {
    if (isPaused.value) {
      await waitForResume();
    }
    
    const step = steps[i];
    analysisProgress.value = step.progress;
    currentStep.value = step.step;
    stepDetail.value = step.detail;
    
    console.log(`进度更新: ${step.progress}%`); // 添加调试日志
    
    // 模拟处理时间
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));
  }
}

// 等待恢复
function waitForResume() {
  return new Promise(resolve => {
    const checkResume = () => {
      if (!isPaused.value) {
        resolve();
      } else {
        setTimeout(checkResume, 100);
      }
    };
    checkResume();
  });
}

// 进度模拟器
let progressInterval = null;

function startProgressSimulator() {
  // 清除之前的定时器
  if (progressInterval) {
    clearInterval(progressInterval);
  }
  
  // 每3秒更新一次进度
  progressInterval = setInterval(() => {
    if (status.value === 'analyzing' && analysisProgress.value < 95) {
      const increment = Math.random() * 2 + 0.5; // 每次增加0.5-2.5%
      analysisProgress.value = Math.min(95, analysisProgress.value + increment);
      
      // 更新步骤信息
      if (analysisProgress.value < 60) {
        currentStep.value = '数据预处理';
        stepDetail.value = '正在处理遥感影像数据...';
      } else if (analysisProgress.value < 80) {
        currentStep.value = '计算生态指数';
        stepDetail.value = '正在计算生态指数...';
      } else {
        currentStep.value = '结果生成';
        stepDetail.value = '正在生成分析结果...';
      }
      
      console.log(`进度模拟器更新: ${analysisProgress.value.toFixed(1)}%`);
    }
  }, 3000);
}

function stopProgressSimulator() {
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
}

// 轮询任务状态
async function pollTaskStatus(taskId, imageId) {
  const maxAttempts = 60;
  let attempts = 0;

  const poll = async () => {
    try {
      console.log(`轮询任务状态，第${attempts + 1}次，任务ID: ${taskId}`);
      const statusResult = await processingTaskService.getStatus(taskId);
      console.log('任务状态响应:', statusResult);
      console.log('任务状态响应类型:', typeof statusResult);
      console.log('任务状态响应键:', Object.keys(statusResult || {}));
      const taskStatus = statusResult.status;
      console.log('解析的任务状态:', taskStatus);

      if (taskStatus === 'completed') {
        // 任务完成，获取结果
        console.log('🎉🎉🎉 分析任务完成！开始保存缓存 🎉🎉🎉');
        
        // 确保进度条达到100%
        analysisProgress.value = 100;
        currentStep.value = '分析完成';
        stepDetail.value = '所有计算已完成，正在生成结果...';
        
        const taskDetail = await processingTaskService.getDetail(taskId);
        console.log('任务完成，获取到的任务详情:', taskDetail);
        
        status.value = 'done';
        clearActiveTask(taskId);
        // 停止进度模拟器
        stopProgressSimulator();
        
        // 确保resultData包含影像ID
        resultData.value = {
          ...taskDetail,
          remote_sensing_image_id: imageId
        };
        
        // 保存分析结果到缓存
        console.log('准备保存缓存，参数:', {
          resultData: resultData.value,
          imageId: imageId,
          selectedIndex: selectedIndex.value
        });
        
        // 确保当前指数类型的结果被正确缓存
        const currentIndex = selectedIndex.value;
        if (currentIndex) {
          saveAnalysisResult(resultData.value, imageId, currentIndex);
          
          // 验证缓存是否保存成功
          setTimeout(() => {
            const verifyCache = getCachedResult(imageId, currentIndex);
            if (verifyCache) {
              console.log(`✅ 验证成功：${currentIndex}分析结果已正确缓存`);
            } else {
              console.warn(`❌ 验证失败：${currentIndex}分析结果未能正确缓存`);
            }
          }, 200);
        }
        
        console.log('设置resultData:', resultData.value);
        messageStore.success('分析完成！');
        return;
      } else if (taskStatus === 'failed') {
        // 任务失败
        status.value = 'error';
        clearActiveTask(taskId);
        resultData.value = { error: '分析任务执行失败' };
        // 停止进度模拟器
        stopProgressSimulator();
        messageStore.error('分析任务执行失败');
        return;
      } else if (taskStatus === 'processing' || taskStatus === 'pending') {
        // 任务处理中，继续轮询
        attempts++;
        
        // 动态更新进度
        analysisProgress.value = Number.isFinite(Number(statusResult.progress))
          ? Number(statusResult.progress)
          : analysisProgress.value;
        
        // 更新步骤信息
        if (taskStatus === 'processing') {
          currentStep.value = '计算生态指数';
          stepDetail.value = '正在计算生态指数，请稍候...';
        } else {
          currentStep.value = '等待处理';
          stepDetail.value = '任务已提交，等待系统处理...';
        }
        
        console.log(`任务状态: ${taskStatus}, 进度: ${analysisProgress.value.toFixed(1)}%, 继续轮询 (${attempts}/${maxAttempts})`);
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000);
        } else {
          // 超时
          status.value = 'error';
          resultData.value = { error: '分析超时，请检查任务状态' };
          // 停止进度模拟器
          stopProgressSimulator();
          messageStore.warning('分析超时，请检查任务状态');
        }
      } else {
        // 未知状态
        console.log('未知任务状态:', taskStatus);
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000);
        } else {
          status.value = 'error';
          resultData.value = { error: '任务状态异常' };
          // 停止进度模拟器
          stopProgressSimulator();
          messageStore.error('任务状态异常');
        }
      }
    } catch (error) {
      console.error('查询任务状态失败:', error);
      attempts++;
      if (attempts < maxAttempts) {
        console.log(`查询失败，重试 (${attempts}/${maxAttempts})`);
        setTimeout(poll, 2000);
      } else {
        status.value = 'error';
        resultData.value = { error: '查询任务状态失败' };
        // 停止进度模拟器
        stopProgressSimulator();
        messageStore.error('查询任务状态失败');
      }
    }
  };

  poll();
}

// 暂停分析
function pauseAnalysis() {
  isPaused.value = true;
  messageStore.info('分析已暂停');
}

// 恢复分析
function resumeAnalysis() {
  isPaused.value = false;
  messageStore.info('分析已恢复');
}

// 取消分析
async function cancelAnalysis() {
  try {
    const confirmed = await ElMessageBox.confirm(
      '确定要取消当前分析任务吗？',
      '确认取消',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    if (confirmed) {
      status.value = 'waiting';
      analysisProgress.value = 0;
      isPaused.value = false;
      // 停止进度模拟器
      stopProgressSimulator();
      messageStore.info('分析任务已取消');
      
      // 这里可以调用后端API取消任务
      if (currentTaskId.value) {
        // await processingTaskService.cancel(currentTaskId.value);
      }
    }
  } catch (error) {
    // 用户取消操作
  }
}

// 处理指数类型变化
function handleIndexChange(index) {
  const previousIndex = selectedIndex.value;
  console.log(`指数切换: 从 ${previousIndex} 到 ${index}, 当前影像ID: ${currentImageId.value}`);
  
  // 最简单的解决方案：不使用缓存，直接提示用户重新分析
  selectedIndex.value = index;
  resultData.value = null;
  status.value = 'waiting';
  messageStore.info(`已切换到${index}指数，请点击"开始分析"进行计算`);
  
  // 下面是原始的缓存逻辑，但目前不使用
  /*
  // 先保存当前指数的状态（如果有结果）
  if (status.value === 'done' && resultData.value && currentImageId.value) {
    console.log(`保存当前${previousIndex}结果到缓存，防止切换后丢失`, resultData.value);
    
    try {
      // 强制保存当前结果到内存和localStorage
      const currentData = JSON.parse(JSON.stringify(resultData.value)); // 深拷贝确保不共享引用
      const tempKey = `${currentImageId.value}_${previousIndex.toLowerCase()}`;
      
      console.log(`缓存键: ${tempKey}, 数据大小: ${JSON.stringify(currentData).length} 字节`);
      
      // 直接构造缓存对象
      const cacheObj = {
        resultData: currentData,
        imageId: currentImageId.value,
        indexType: previousIndex,
        timestamp: Date.now(),
        fileName: fileName.value
      };
      
      // 保存到内存缓存
      analysisResultsCache.value.set(tempKey, cacheObj);
      console.log(`已保存${previousIndex}结果到内存缓存，键: ${tempKey}`);
      
      // 保存到localStorage
      try {
        const storageKey = `analysis_result_${currentImageId.value}_${previousIndex.toLowerCase()}`;
        
        // 检查数据大小，localStorage限制约为5MB
        const dataStr = JSON.stringify(cacheObj);
        console.log(`准备保存到localStorage，键: ${storageKey}, 数据大小: ${dataStr.length} 字节`);
        
        if (dataStr.length > 4 * 1024 * 1024) { // 4MB限制
          console.warn(`缓存数据过大 (${dataStr.length} 字节)，可能无法保存到localStorage`);
          // 尝试保存简化版本
          const simplifiedData = {
            ...cacheObj,
            resultData: {
              ...cacheObj.resultData,
              // 删除可能的大型数据字段
              raw_data: undefined,
              large_arrays: undefined,
              detailed_results: undefined
            }
          };
          const simplifiedStr = JSON.stringify(simplifiedData);
          console.log(`简化后数据大小: ${simplifiedStr.length} 字节`);
          localStorage.setItem(storageKey, simplifiedStr);
        } else {
          localStorage.setItem(storageKey, dataStr);
        }
        
        // 更新索引
        let cacheIndex = [];
        const existingIndex = localStorage.getItem('analysis_cache_index');
        if (existingIndex) {
          try {
            cacheIndex = JSON.parse(existingIndex);
          } catch (e) {
            console.warn('解析缓存索引失败，创建新索引');
            cacheIndex = [];
          }
        }
        
        if (!cacheIndex.includes(storageKey)) {
          cacheIndex.push(storageKey);
          localStorage.setItem('analysis_cache_index', JSON.stringify(cacheIndex));
        }
        
        console.log(`已强制保存${previousIndex}结果到localStorage，键: ${storageKey}`);
      } catch (error) {
        console.error('保存缓存到localStorage失败:', error);
      }
    } catch (error) {
      console.error('保存缓存时出错:', error);
    }
  }
  
  // 更新当前选择的指数
  selectedIndex.value = index;
  
  // 调试缓存状态
  debugCacheStatus();
  
  // 如果已经上传了文件，检查是否有缓存结果
  if (currentFile.value && currentImageId.value) {
    console.log('检查缓存，参数:', {
      currentImageId: currentImageId.value,
      index: index,
      previousIndex: previousIndex,
      hasFile: !!currentFile.value
    });
    
    // 尝试直接从localStorage读取
    const storageKey = `analysis_result_${currentImageId.value}_${index.toLowerCase()}`;
    console.log(`尝试从localStorage读取缓存，键: ${storageKey}`);
    
    try {
      const storedData = localStorage.getItem(storageKey);
      if (storedData) {
        console.log(`找到缓存数据，大小: ${storedData.length} 字节`);
        const cachedData = JSON.parse(storedData);
        console.log(`从localStorage直接读取到${index}缓存:`, !!cachedData);
        
        if (cachedData && cachedData.resultData) {
          console.log(`缓存数据有效，包含resultData字段`);
          
          // 更新内存缓存
          const memKey = `${currentImageId.value}_${index.toLowerCase()}`;
          analysisResultsCache.value.set(memKey, cachedData);
          
          // 显示缓存结果
          resultData.value = cachedData.resultData;
          status.value = 'done';
          messageStore.success(`已加载${index}指数的缓存结果`);
          return;
        } else {
          console.warn(`缓存数据无效或不完整:`, cachedData);
        }
      } else {
        console.log(`localStorage中没有找到键 ${storageKey} 的缓存数据`);
      }
    } catch (error) {
      console.warn(`直接读取${index}缓存失败:`, error);
    }
    
    // 如果直接读取失败，尝试从内存缓存读取
    console.log(`尝试从内存缓存读取 ${index} 结果`);
    const cached = getCachedResult(currentImageId.value, index);
    if (cached) {
      // 有缓存结果，直接显示
      console.log(`从内存缓存找到 ${index} 结果:`, cached);
      resultData.value = cached.resultData;
      status.value = 'done';
      messageStore.success(`已加载${index}指数的缓存结果 (从内存)`);
    } else {
      // 没有缓存，提示用户重新分析
      console.log(`未找到 ${index} 的缓存结果，需要重新分析`);
      resultData.value = null;
      status.value = 'waiting';
      messageStore.info(`已切换到${index}指数，点击"开始分析"重新计算`);
    }
  } else {
    console.log('无法检查缓存，缺少必要参数:', {
      hasFile: !!currentFile.value,
      currentImageId: currentImageId.value
    });
  }
  */
}

// 组件卸载时清理
onUnmounted(() => {
  // 清理定时器等资源
  stopProgressSimulator();
});
</script>

<style scoped>
.remote-sensing-analysis {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #f4f7fa;
}

/* 左侧控制面板 */
.control-panel {
  width: 360px;
  background: #ffffff;
  border-right: 1px solid #dbe6f0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  box-shadow: 2px 0 12px rgba(15, 23, 42, 0.06);
}

/* 自定义滚动条样式 */
.control-panel::-webkit-scrollbar {
  width: 6px;
}

.control-panel::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.control-panel::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.control-panel::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* 右侧结果区域 */
.result-area {
  flex: 1;
  position: relative;
  background: #f4f7fa;
  min-height: 500px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
  overflow-y: auto;
  padding: 20px;
}

/* 右侧结果区域滚动条样式 */
.result-area::-webkit-scrollbar {
  width: 6px;
}

.result-area::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.result-area::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background 0.2s ease;
}

.result-area::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* 分析进度样式 */
.analysis-progress {
  width: 100%;
  max-width: 720px;
  text-align: center;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 40px 32px;
  border: 1px solid #dbe6f0;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 14px 34px rgba(30, 50, 70, 0.08);
}

:deep(.result-area > *) {
  width: 100%;
  max-width: 1280px;
}

:deep(.result-area .placeholder),
:deep(.result-area .empty-state),
:deep(.result-area .result-card),
:deep(.result-area .chart-card),
:deep(.result-area .stats-card) {
  border-radius: 10px;
}

.progress-title {
  font-size: 24px;
  font-weight: 700;
  color: #26384a;
  margin-bottom: 28px;
}

.analysis-status {
  margin-top: 24px;
  width: 100%;
  padding: 18px 20px;
  background: #f7fafc;
  border-radius: 10px;
  border: 1px solid #dbe6f0;
  text-align: left;
}

.status-text {
  font-size: 16px;
  font-weight: 600;
  color: #26384a;
  margin: 0 0 8px 0;
}

.status-detail {
  font-size: 14px;
  color: #667789;
  margin: 0;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .remote-sensing-analysis-apple {
    flex-direction: column;
    gap: 24px;
    padding: 24px 2vw;
    max-height: none;
    overflow: visible;
  }
  
  .sidebar-apple, .result-area-apple {
    width: 100%;
    min-width: unset;
    border-radius: 20px;
    padding: 24px 12px;
    max-height: none;
    overflow-y: visible;
  }
  
  .analysis-progress {
    max-width: 100%;
  }
}
</style> 
