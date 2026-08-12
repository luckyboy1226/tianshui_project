<template>
  <div class="map-view">
    <!-- 左侧边栏 -->
    <div class="sidebar">
      <!-- 系统标题 -->
      <div class="sidebar-header">
        <h1>流域生态环境监管系统</h1>
      </div>

      <!-- 用户信息 -->
      <div class="user-section">
        <div class="user-info">
          <User class="inline-icon user-icon" />
          <span>{{ currentUser ? `${currentUser.username}（${currentUser.role_display || currentUser.role || '用户'}）` : '未登录' }}</span>
        </div>
        <div class="user-actions">
          <button v-if="canManageUsers" class="admin-btn" @click="openUserManagementDialog">用户管理</button>
          <button class="login-btn" @click="currentUser ? handleLogout() : openLoginDialog()">
            {{ currentUser ? '退出' : '登录' }}
          </button>
        </div>
      </div>

      <div v-if="loginDialogVisible" class="login-mask" @click.self="loginDialogVisible = false">
        <div class="login-dialog">
          <div class="login-title">系统登录</div>
          <label class="login-field">
            <span>用户名</span>
            <input v-model="loginForm.username" type="text" autocomplete="off" />
          </label>
          <label class="login-field">
            <span>密码</span>
            <input v-model="loginForm.password" type="password" autocomplete="off" @keydown.enter="handleLogin" />
          </label>
          <div class="login-actions">
            <button class="dialog-cancel" @click="loginDialogVisible = false">取消</button>
            <button class="dialog-confirm" :disabled="loginLoading" @click="handleLogin">
              {{ loginLoading ? '登录中...' : '登录' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 图层管理 -->
      <div class="section">
        <div class="section-header" @click="toggleLayerManagement">
          <Files class="inline-icon section-icon" />
          <span>图层管理</span>
          <ArrowDown class="inline-icon collapse-icon" :class="{ 'collapsed': !layerManagementExpanded }" />
        </div>
        
        <div class="section-content" v-show="layerManagementExpanded">
          <!-- 业务图层 -->
          <div class="layer-group">
            <div class="layer-group-header" @click="toggleBusinessLayers">
              <h4>业务图层</h4>
              <ArrowDown class="inline-icon collapse-icon" :class="{ 'collapsed': !businessLayersExpanded }" />
            </div>
            <div class="layer-group-content" v-show="businessLayersExpanded">
              <button class="upload-btn publish-btn" :disabled="businessLayerUploading" @click="triggerBusinessLayerUpload">
                <Upload class="button-icon" />
                {{ businessLayerUploading ? '发布中...' : '上传并发布业务图层' }}
              </button>
              <button class="upload-btn service-btn" :disabled="businessLayerUploading" @click="openBusinessServiceDialog">
                <Connection class="button-icon" />
                接入标准服务
              </button>
              <input
                ref="businessLayerInput"
                type="file"
                accept=".zip,.kml,.tif,.tiff"
                style="display: none"
                @change="handleBusinessLayerUpload"
              >
              <div class="layer-item" v-for="layer in businessLayers" :key="layer.id">
                <div class="layer-info layer-info-rich">
                  <div class="layer-main-row">
                    <component :is="layer.icon" class="inline-icon layer-icon" />
                    <div class="layer-text">
                      <span>{{ layer.name }}</span>
                      <small v-if="layer.statusText" :class="['layer-status', layer.status]">{{ layer.statusText }}</small>
                    </div>
                  </div>
                  <div v-if="layer.source === 'service'" class="layer-meta-grid">
                    <span class="layer-pill">{{ layer.typeLabel }}</span>
                    <span class="layer-pill">{{ layer.sourceFormatLabel }}</span>
                    <span v-if="layer.healthText" :class="['layer-pill', 'health-pill', `health-${layer.healthStatus}`]">{{ layer.healthText }}</span>
                  </div>
                  <div v-if="layer.source === 'service'" class="layer-detail-list">
                    <div class="layer-detail-row">
                      <span class="detail-label">来源</span>
                      <span class="detail-value">{{ layer.originLabel }}</span>
                    </div>
                    <div class="layer-detail-row">
                      <span class="detail-label">服务</span>
                      <span class="detail-value layer-url" :title="layer.primaryServiceUrl">{{ layer.primaryServiceUrl || '未生成' }}</span>
                    </div>
                    <div class="layer-detail-row">
                      <span class="detail-label">时间</span>
                      <span class="detail-value">{{ layer.createdAtText }}</span>
                    </div>
                    <div v-if="layer.description" class="layer-detail-row">
                      <span class="detail-label">描述</span>
                      <span class="detail-value">{{ layer.description }}</span>
                    </div>
                    <div v-if="layer.healthMessage" class="layer-detail-row">
                      <span class="detail-label">检测</span>
                      <span class="detail-value">{{ layer.healthMessage }}</span>
                    </div>
                  </div>
                </div>
                <div class="layer-controls">
                  <button
                    v-if="layer.source === 'service' && layer.status !== 'published'"
                    class="layer-action-btn"
                    :disabled="isBusinessLayerBusy(layer)"
                    title="重新发布"
                    @click.stop="handleBusinessLayerPublish(layer)"
                  >
                    <Refresh class="button-icon" />
                  </button>
                  <button
                    v-if="layer.source === 'service' && layer.status === 'published'"
                    class="layer-action-btn"
                    :disabled="isBusinessLayerBusy(layer)"
                    title="撤销发布"
                    @click.stop="handleBusinessLayerUnpublish(layer)"
                  >
                    <Close class="button-icon" />
                  </button>
                  <button
                    v-if="layer.source === 'service'"
                    class="layer-action-btn danger"
                    :disabled="isBusinessLayerBusy(layer)"
                    title="删除记录"
                    @click.stop="handleBusinessLayerDelete(layer)"
                  >
                    <Delete class="button-icon" />
                  </button>
                  <button
                    v-if="layer.source === 'service'"
                    class="layer-action-btn"
                    :disabled="isBusinessLayerBusy(layer)"
                    title="样式配置"
                    @click.stop="openBusinessLayerStyleDialog(layer)"
                  >
                    <Setting class="button-icon" />
                  </button>
                  <button
                    v-if="layer.source === 'service'"
                    class="layer-action-btn"
                    :disabled="isBusinessLayerBusy(layer)"
                    title="操作日志"
                    @click.stop="openBusinessLayerLogsDialog(layer)"
                  >
                    <Files class="button-icon" />
                  </button>
                  <label class="toggle-switch">
                    <input 
                      type="checkbox" 
                      :checked="layer.visible"
                      @change="handleBusinessLayerToggle(layer)"
                    />
                    <span class="slider"></span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <!-- 临时图层 -->
          <div class="layer-group">
            <div class="layer-group-header" @click="toggleTempLayers">
              <h4>临时图层</h4>
              <ArrowDown class="inline-icon collapse-icon" :class="{ 'collapsed': !tempLayersExpanded }" />
            </div>
            <div class="layer-group-content" v-show="tempLayersExpanded">
              <button class="upload-btn" @click="triggerFileUpload">
                <Upload class="button-icon" />
                上传本地文件 (KML/SHP.zip)
              </button>
              <input 
                ref="fileInput" 
                type="file" 
                accept=".kml,.zip,.geojson,.json" 
                style="display: none"
                @change="handleFileUpload"
              >
            </div>
          </div>
        </div>
      </div>

      <!-- 工具箱 -->
      <div class="section">
        <div class="section-header" @click="toggleToolbox">
          <Setting class="inline-icon section-icon" />
          <span>工具箱</span>
          <ArrowDown class="inline-icon collapse-icon" :class="{ 'collapsed': !toolboxExpanded }" />
        </div>
        <div class="section-content" v-show="toolboxExpanded">
          <p class="tool-tip">使用地图左侧的工具栏进行图形绘制。</p>
          
          <!-- 坐标定位 -->
          <div class="coordinate-section">
            <h4>坐标定位</h4>
            <div class="coordinate-inputs">
              <input type="text" placeholder="经度,纬度" v-model="coordinateInput" />
              <button class="locate-btn" @click="locateCoordinate">
                <Search class="button-icon" />
              </button>
            </div>
          </div>

          <!-- 导出地图 -->
          <button class="export-btn" @click="exportMap">
            <Camera class="button-icon" />
            导出地图为图片
          </button>
        </div>
      </div>

      <!-- 业务功能 -->
      <div class="section">
        <div class="section-header" @click="toggleBusinessFunctions">
          <DataAnalysis class="inline-icon section-icon" />
          <span>业务功能</span>
          <ArrowDown class="inline-icon collapse-icon" :class="{ 'collapsed': !businessFunctionsExpanded }" />
        </div>
        <div class="section-content" v-show="businessFunctionsExpanded">
          <div class="business-functions">
            <button
              v-for="func in businessFunctions"
              :key="func.id"
              type="button"
              class="function-item"
              :class="{ active: route.path === func.route }"
              @click="handleBusinessFunctionClick(func)"
            >
              <span class="function-leading">
                <span class="function-icon-box">
                  <component :is="func.icon" class="inline-icon function-icon" />
                </span>
                <span class="function-copy">
                  <span class="function-name">{{ func.name }}</span>
                </span>
              </span>
              <ArrowRight class="inline-icon function-arrow" />
            </button>
          </div>
        </div>
      </div>

      <div v-if="userManagementDialogVisible" class="login-mask" @click.self="userManagementDialogVisible = false">
        <div class="service-dialog user-management-dialog">
          <div class="login-title">用户管理</div>
          <div class="user-admin-toolbar">
            <button class="dialog-confirm" @click="openCreateUserDialog">新增用户</button>
            <button class="dialog-cancel" @click="loadUsers">刷新</button>
          </div>
          <div v-if="userManagementLoading" class="empty-log">加载中...</div>
          <div v-else class="user-list">
            <div v-for="item in managedUsers" :key="item.id" class="user-card">
              <div class="user-card-head">
                <div>
                  <div class="user-card-name">{{ item.username }}</div>
                  <div class="user-card-meta">{{ item.role_display || item.role }} · {{ item.is_active ? '启用' : '禁用' }}</div>
                </div>
                <div class="user-card-actions">
                  <button class="layer-action-btn" title="编辑用户" @click="openEditUserDialog(item)">
                    <Setting class="button-icon" />
                  </button>
                  <button class="layer-action-btn" title="权限分配" @click="openPermissionDialog(item)">
                    <Files class="button-icon" />
                  </button>
                  <button class="layer-action-btn danger" title="删除用户" @click="handleDeleteUser(item)">
                    <Delete class="button-icon" />
                  </button>
                </div>
              </div>
              <div class="user-card-grid">
                <div>姓名：{{ [item.first_name, item.last_name].filter(Boolean).join(' ') || '未填写' }}</div>
                <div>邮箱：{{ item.email || '未填写' }}</div>
                <div>机构：{{ item.organization || '未填写' }}</div>
                <div>电话：{{ item.phone || '未填写' }}</div>
              </div>
            </div>
          </div>
          <div class="login-actions">
            <button class="dialog-confirm" @click="userManagementDialogVisible = false">关闭</button>
          </div>
        </div>
      </div>

      <div v-if="userEditDialogVisible" class="login-mask" @click.self="userEditDialogVisible = false">
        <div class="service-dialog">
          <div class="login-title">{{ userEditMode === 'create' ? '新增用户' : '编辑用户' }}</div>
          <label class="login-field">
            <span>用户名</span>
            <input v-model="userForm.username" type="text" autocomplete="off" />
          </label>
          <label class="login-field">
            <span>邮箱</span>
            <input v-model="userForm.email" type="email" autocomplete="off" />
          </label>
          <label class="login-field">
            <span>姓名</span>
            <input v-model="userForm.first_name" type="text" autocomplete="off" />
          </label>
          <label class="login-field">
            <span>角色</span>
            <select v-model="userForm.role">
              <option value="admin">管理员</option>
              <option value="user">普通用户</option>
              <option value="expert">专家</option>
            </select>
          </label>
          <label class="login-field">
            <span>手机号</span>
            <input v-model="userForm.phone" type="text" autocomplete="off" />
          </label>
          <label class="login-field">
            <span>所属机构</span>
            <input v-model="userForm.organization" type="text" autocomplete="off" />
          </label>
          <label class="login-field">
            <span>部门</span>
            <input v-model="userForm.department" type="text" autocomplete="off" />
          </label>
          <label class="login-field">
            <span>职位</span>
            <input v-model="userForm.position" type="text" autocomplete="off" />
          </label>
          <label class="login-field">
            <span>状态</span>
            <select v-model="userForm.is_active">
              <option :value="true">启用</option>
              <option :value="false">禁用</option>
            </select>
          </label>
          <label class="login-field">
            <span>{{ userEditMode === 'create' ? '密码' : '新密码（可留空）' }}</span>
            <input v-model="userForm.password" type="password" autocomplete="new-password" />
          </label>
          <label v-if="userEditMode === 'create'" class="login-field">
            <span>确认密码</span>
            <input v-model="userForm.password_confirm" type="password" autocomplete="new-password" />
          </label>
          <div class="login-actions">
            <button class="dialog-cancel" @click="userEditDialogVisible = false">取消</button>
            <button class="dialog-confirm" :disabled="userSubmitting" @click="submitUserForm">
              {{ userSubmitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="permissionDialogVisible" class="login-mask" @click.self="permissionDialogVisible = false">
        <div class="service-dialog permission-dialog">
          <div class="login-title">权限分配</div>
          <div class="permission-subtitle">{{ activeManagedUser?.username }}</div>
          <div class="permission-groups">
            <div v-for="(permissionItems, moduleName) in permissionSchema" :key="moduleName" class="permission-group">
              <div class="permission-group-title">{{ permissionModuleLabels[moduleName] || moduleName }}</div>
              <div class="permission-options">
                <label v-for="permissionName in permissionItems" :key="`${moduleName}-${permissionName}`" class="permission-option">
                  <input
                    type="checkbox"
                    :checked="hasPermission(moduleName, permissionName)"
                    @change="togglePermission(moduleName, permissionName, $event.target.checked)"
                  />
                  <span>{{ permissionLabels[permissionName] || permissionName }}</span>
                </label>
              </div>
            </div>
          </div>
          <div class="login-actions">
            <button class="dialog-cancel" @click="permissionDialogVisible = false">取消</button>
            <button class="dialog-confirm" :disabled="permissionSubmitting" @click="savePermissions">
              {{ permissionSubmitting ? '保存中...' : '保存权限' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 主地图区域 -->
    <div class="main-content">
      <MapContainer ref="mapContainerRef" />
    </div>

    <div v-if="businessServiceDialogVisible" class="login-mask" @click.self="businessServiceDialogVisible = false">
      <div class="service-dialog">
        <div class="login-title">接入标准服务图层</div>
        <label class="login-field">
          <span>图层名称</span>
          <input v-model="businessServiceForm.name" type="text" autocomplete="off" />
        </label>
        <label class="login-field">
          <span>服务类型</span>
          <select v-model="businessServiceForm.source_format" @change="syncBusinessServiceLayerType">
            <option value="wms">WMS</option>
            <option value="wfs">WFS</option>
            <option value="wcs">WCS</option>
          </select>
        </label>
        <label class="login-field">
          <span>图层类型</span>
          <select v-model="businessServiceForm.layer_type" :disabled="businessServiceForm.source_format !== 'wms'">
            <option value="vector">矢量</option>
            <option value="raster">栅格</option>
          </select>
        </label>
        <label class="login-field">
          <span>服务地址</span>
          <textarea v-model="businessServiceForm.service_url" rows="4" placeholder="请输入标准服务请求地址"></textarea>
        </label>
        <label class="login-field">
          <span>图层名称参数</span>
          <input v-model="businessServiceForm.service_type_name" type="text" autocomplete="off" placeholder="WMS 的 layers 或 WFS 的 typeName" />
        </label>
        <label class="login-field">
          <span>坐标系</span>
          <input v-model="businessServiceForm.service_srs" type="text" autocomplete="off" placeholder="例如 EPSG:4326 / EPSG:3857" />
        </label>
        <label class="login-field">
          <span>样式名称</span>
          <input v-model="businessServiceForm.style_name" type="text" autocomplete="off" placeholder="可选，用于记录样式或SLD名称" />
        </label>
        <label class="login-field">
          <span>说明</span>
          <textarea v-model="businessServiceForm.description" rows="3" placeholder="可选"></textarea>
        </label>
        <div class="login-actions">
          <button class="dialog-cancel" @click="businessServiceDialogVisible = false">取消</button>
          <button class="dialog-confirm" :disabled="businessServiceSubmitting" @click="handleBusinessServiceCreate">
            {{ businessServiceSubmitting ? '接入中...' : '保存并接入' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="businessLayerStyleDialogVisible" class="login-mask" @click.self="businessLayerStyleDialogVisible = false">
      <div class="service-dialog">
        <div class="login-title">业务图层样式配置</div>
        <label class="login-field">
          <span>样式名称</span>
          <input v-model="businessLayerStyleForm.style_name" type="text" autocomplete="off" />
        </label>
        <template v-if="businessLayerStyleForm.layer_type === 'vector'">
          <label class="login-field">
            <span>填充颜色</span>
            <div class="color-field">
              <input v-model="businessLayerStyleForm.fill_color" class="color-input" type="color" />
              <input v-model="businessLayerStyleForm.fill_color" type="text" placeholder="#1f8f4d" autocomplete="off" />
            </div>
          </label>
          <label class="login-field">
            <span>边线颜色</span>
            <div class="color-field">
              <input v-model="businessLayerStyleForm.stroke_color" class="color-input" type="color" />
              <input v-model="businessLayerStyleForm.stroke_color" type="text" placeholder="#1f8f4d" autocomplete="off" />
            </div>
          </label>
          <label class="login-field">
            <span>边线宽度</span>
            <input v-model="businessLayerStyleForm.stroke_width" type="number" min="0" step="0.5" />
          </label>
          <label class="login-field">
            <span>填充透明度</span>
            <input v-model="businessLayerStyleForm.fill_opacity" type="number" min="0" max="1" step="0.05" />
          </label>
          <label class="login-field">
            <span>分类字段</span>
            <input v-model="businessLayerStyleForm.classification_field" type="text" autocomplete="off" />
          </label>
          <label class="login-field">
            <span>分类配色</span>
            <select v-model="businessLayerStyleForm.color_scheme">
              <option value="green_yellow_red">绿黄红</option>
              <option value="blue_cyan_green">蓝青绿</option>
              <option value="purple_pink_red">紫粉红</option>
            </select>
          </label>
        </template>
        <template v-else>
          <label class="login-field">
            <span>色带方案</span>
            <select v-model="businessLayerStyleForm.raster_color_ramp">
              <option value="green_yellow_red">绿黄红</option>
              <option value="blue_cyan_green">蓝青绿</option>
              <option value="gray_blue">灰蓝</option>
            </select>
          </label>
          <label class="login-field">
            <span>栅格透明度</span>
            <input v-model="businessLayerStyleForm.raster_opacity" type="number" min="0" max="1" step="0.05" />
          </label>
          <label class="login-field">
            <span>NoData</span>
            <input v-model="businessLayerStyleForm.nodata" type="number" step="0.01" />
          </label>
        </template>
        <label class="login-field">
          <span>自定义 SLD</span>
          <textarea v-model="businessLayerStyleForm.sld_content" rows="6" placeholder="可选，填写后优先使用自定义SLD"></textarea>
        </label>
        <div class="login-actions">
          <button class="dialog-cancel" @click="businessLayerStyleDialogVisible = false">取消</button>
          <button class="dialog-confirm" :disabled="businessLayerStyleSubmitting" @click="handleBusinessLayerStyleSave">
            {{ businessLayerStyleSubmitting ? '保存中...' : '保存并应用' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="businessLayerLogsDialogVisible" class="login-mask" @click.self="businessLayerLogsDialogVisible = false">
      <div class="service-dialog">
        <div class="login-title">业务图层操作日志</div>
        <div class="log-list" v-if="businessLayerLogs.length">
          <div class="log-item" v-for="log in businessLayerLogs" :key="log.id">
            <div class="log-head">
              <span class="layer-pill">{{ log.action_display }}</span>
              <span :class="['layer-pill', 'health-pill', `health-${log.status === 'success' ? 'healthy' : log.status === 'failed' ? 'unhealthy' : 'unknown'}`]">
                {{ log.status_display }}
              </span>
              <button
                v-if="logHasDetails(log)"
                type="button"
                class="log-toggle-btn"
                @click="toggleBusinessLayerLogDetails(log.id)"
              >
                {{ businessLayerExpandedLogIds.has(log.id) ? '收起详情' : '查看详情' }}
              </button>
            </div>
            <div class="log-line">{{ log.message || '无说明' }}</div>
            <div class="log-line muted">{{ log.operator_name || '系统' }} · {{ formatDateTime(log.created_at) }}</div>
            <pre v-if="businessLayerExpandedLogIds.has(log.id)" class="log-details">{{ formatLogDetails(log.details) }}</pre>
          </div>
        </div>
        <div v-else class="empty-log">暂无操作日志</div>
        <div class="login-actions">
          <button class="dialog-confirm" @click="businessLayerLogsDialogVisible = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  ArrowRight,
  Camera,
  Close,
  Connection,
  DataAnalysis,
  Delete,
  Files,
  Guide,
  Histogram,
  MapLocation,
  Message,
  Refresh,
  Search,
  Setting,
  TrendCharts,
  Upload,
  User
} from '@element-plus/icons-vue'
import MapContainer from '../components/Map/MapContainer.vue'
import { useMapStore } from '../store/map'
import { useRoute, useRouter } from 'vue-router'
import { authService, spatialService } from '../services/api.js'
import { ensureCsrfCookie } from '../utils/http.js'

const router = useRouter()
const route = useRoute()
const mapStore = useMapStore()
const { toggleLayerVisibility } = mapStore

const fileInput = ref(null)
const businessLayerInput = ref(null)
const mapContainerRef = ref(null)
const coordinateInput = ref('')
const currentUser = ref(null)
const loginDialogVisible = ref(false)
const loginLoading = ref(false)
const userManagementDialogVisible = ref(false)
const userManagementLoading = ref(false)
const userEditDialogVisible = ref(false)
const userEditMode = ref('create')
const userSubmitting = ref(false)
const permissionDialogVisible = ref(false)
const permissionSubmitting = ref(false)
const activeManagedUser = ref(null)
const managedUsers = ref([])
const permissionSchema = ref({})
const permissionDraft = reactive({})
const businessLayerUploading = ref(false)
const businessLayerActionIds = ref(new Set())
const businessServiceDialogVisible = ref(false)
const businessServiceSubmitting = ref(false)
const businessLayerStyleDialogVisible = ref(false)
const businessLayerStyleSubmitting = ref(false)
const businessLayerLogsDialogVisible = ref(false)
const businessLayerLogs = ref([])
const businessLayerExpandedLogIds = ref(new Set())
const activeBusinessLayer = ref(null)
const loginForm = reactive({
  username: '',
  password: ''
})
const userForm = reactive({
  id: null,
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  role: 'user',
  phone: '',
  organization: '',
  department: '',
  position: '',
  is_active: true,
  password: '',
  password_confirm: ''
})
const businessServiceForm = reactive({
  name: '',
  description: '',
  layer_type: 'vector',
  source_format: 'wms',
  service_url: '',
  service_type_name: '',
  service_srs: '',
  style_name: ''
})
const businessLayerStyleForm = reactive({
  layer_type: 'vector',
  style_name: '',
  fill_color: '#1f8f4d',
  stroke_color: '#1f8f4d',
  stroke_width: 2,
  fill_opacity: 0.18,
  classification_field: '',
  color_scheme: 'green_yellow_red',
  raster_color_ramp: 'green_yellow_red',
  raster_opacity: 0.72,
  nodata: '',
  sld_content: ''
})

// 折叠状态控制
const layerManagementExpanded = ref(true)
const businessLayersExpanded = ref(true)
const tempLayersExpanded = ref(true)
const toolboxExpanded = ref(true)
const businessFunctionsExpanded = ref(true)
const canManageUsers = computed(() => Boolean(currentUser.value?.is_admin || currentUser.value?.role === 'admin'))
const permissionModuleLabels = {
  remote_sensing: '遥感生态指数分析',
  ecological_index: '生态环境指数计算',
  overlay_analysis: '重大工程叠加分析',
  climate_monitoring: '气候环境监测统计',
  feedback: '民众意见反馈',
  business_layers: '业务图层管理',
  user_management: '用户管理'
}
const permissionLabels = {
  view: '查看',
  use: '使用',
  manage: '管理'
}

// 业务图层数据
const businessLayers = reactive([
  {
    id: 'watershed-boundary',
    name: '藉河流域范围',
    type: 'vector',
    icon: Guide,
    visible: false
  },
  {
    id: 'watershed-points',
    name: '藉河流域点数据',
    type: 'vector',
    icon: MapLocation,
    visible: false
  },
  {
    id: 'townships',
    name: '乡镇行政区划',
    type: 'vector',
    icon: Files,
    visible: false
  }
])

// 业务功能
const businessFunctions = reactive([
  {
    id: 1,
    name: '遥感生态指数分析',
    icon: DataAnalysis,
    status: 'available'
  },
  {
    id: 2,
    name: '生态环境指数计算',
    icon: Histogram,
    status: 'available'
  },
  {
    id: 3,
    name: '重大工程叠加分析',
    icon: Connection,
    status: 'planned'
  },
  {
    id: 4,
    name: '气候环境监测统计',
    icon: TrendCharts,
    status: 'available',
    route: '/climate-monitoring'
  },
  {
    id: 5,
    name: '民众意见反馈',
    icon: Message,
    status: 'available',
    route: '/feedback'
  }
])

businessFunctions[0].route = '/remote-sensing-analysis'
businessFunctions[1].route = '/ecological-index'
businessFunctions[2].status = 'available'
businessFunctions[2].route = '/overlay-analysis'

onMounted(() => {
  ensureCsrfCookie().catch((error) => {
    console.warn('初始化 CSRF Cookie 失败，首次写操作可能需要重试:', error)
  })
  loadCurrentUser()
  loadBusinessLayers()
})

const loadCurrentUser = async () => {
  try {
    currentUser.value = await authService.getProfile({ silentError: true })
  } catch {
    currentUser.value = null
  }
}

const openLoginDialog = async () => {
  try {
    await ensureCsrfCookie()
  } catch (error) {
    console.warn('打开登录框前获取 CSRF Cookie 失败:', error)
  }
  loginForm.username = ''
  loginForm.password = ''
  loginDialogVisible.value = true
}

const resetUserForm = () => {
  userForm.id = null
  userForm.username = ''
  userForm.email = ''
  userForm.first_name = ''
  userForm.last_name = ''
  userForm.role = 'user'
  userForm.phone = ''
  userForm.organization = ''
  userForm.department = ''
  userForm.position = ''
  userForm.is_active = true
  userForm.password = ''
  userForm.password_confirm = ''
}

const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loginLoading.value = true
  try {
    await ensureCsrfCookie()
    const result = await authService.login({
      username: loginForm.username,
      password: loginForm.password
    })
    currentUser.value = result.user
    loginDialogVisible.value = false
    ElMessage.success('登录成功')
  } catch (error) {
    console.error(error)
  } finally {
    loginLoading.value = false
  }
}

const handleLogout = async () => {
  try {
    await authService.logout()
  } catch (error) {
    console.warn('后端登出请求未完成，已在前端清除登录状态:', error)
  } finally {
    currentUser.value = null
    managedUsers.value = []
    userManagementDialogVisible.value = false
    ElMessage.success('已退出登录')
  }
}

const loadUsers = async () => {
  if (!canManageUsers.value) return
  userManagementLoading.value = true
  try {
    const result = await authService.getUsers({}, { silentError: true })
    managedUsers.value = Array.isArray(result) ? result : (result.results || [])
  } finally {
    userManagementLoading.value = false
  }
}

const ensurePermissionSchema = async () => {
  if (!canManageUsers.value || Object.keys(permissionSchema.value).length > 0) return
  const result = await authService.getPermissionSchema({ silentError: true })
  permissionSchema.value = result.modules || {}
}

const openUserManagementDialog = async () => {
  if (!canManageUsers.value) {
    ElMessage.warning('仅管理员可管理用户')
    return
  }
  userManagementDialogVisible.value = true
  await Promise.all([loadUsers(), ensurePermissionSchema()])
}

const openCreateUserDialog = () => {
  resetUserForm()
  userEditMode.value = 'create'
  userEditDialogVisible.value = true
}

const openEditUserDialog = (user) => {
  resetUserForm()
  userEditMode.value = 'edit'
  userForm.id = user.id
  userForm.username = user.username || ''
  userForm.email = user.email || ''
  userForm.first_name = user.first_name || ''
  userForm.last_name = user.last_name || ''
  userForm.role = user.role || 'user'
  userForm.phone = user.phone || ''
  userForm.organization = user.organization || ''
  userForm.department = user.department || ''
  userForm.position = user.position || ''
  userForm.is_active = user.is_active !== false
  userEditDialogVisible.value = true
}

const submitUserForm = async () => {
  if (!userForm.username.trim()) {
    ElMessage.warning('请填写用户名')
    return
  }
  if (userEditMode.value === 'create' && !userForm.password) {
    ElMessage.warning('请填写初始密码')
    return
  }
  if (userEditMode.value === 'create' && userForm.password !== userForm.password_confirm) {
    ElMessage.warning('两次密码输入不一致')
    return
  }

  userSubmitting.value = true
  try {
    if (userEditMode.value === 'create') {
      await authService.createUser({
        username: userForm.username.trim(),
        email: userForm.email.trim(),
        first_name: userForm.first_name.trim(),
        last_name: userForm.last_name.trim(),
        role: userForm.role,
        phone: userForm.phone.trim(),
        organization: userForm.organization.trim(),
        department: userForm.department.trim(),
        position: userForm.position.trim(),
        password: userForm.password,
        password_confirm: userForm.password_confirm
      })
      ElMessage.success('用户创建成功')
    } else {
      const payload = {
        username: userForm.username.trim(),
        email: userForm.email.trim(),
        first_name: userForm.first_name.trim(),
        last_name: userForm.last_name.trim(),
        role: userForm.role,
        phone: userForm.phone.trim(),
        organization: userForm.organization.trim(),
        department: userForm.department.trim(),
        position: userForm.position.trim(),
        is_active: userForm.is_active
      }
      if (userForm.password) {
        payload.password = userForm.password
      }
      await authService.updateUser(userForm.id, payload)
      ElMessage.success('用户更新成功')
    }
    userEditDialogVisible.value = false
    await loadUsers()
  } catch (error) {
    console.error(error)
  } finally {
    userSubmitting.value = false
  }
}

const handleDeleteUser = async (user) => {
  if (String(user.id) === String(currentUser.value?.id)) {
    ElMessage.warning('不能删除当前登录管理员')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除用户 ${user.username} 吗？`, '删除用户', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  try {
    await authService.deleteUser(user.id)
    ElMessage.success('用户删除成功')
    await loadUsers()
  } catch (error) {
    console.error(error)
  }
}

const clearPermissionDraft = () => {
  Object.keys(permissionDraft).forEach(key => {
    delete permissionDraft[key]
  })
}

const openPermissionDialog = async (user) => {
  activeManagedUser.value = user
  clearPermissionDraft()
  await ensurePermissionSchema()
  const response = await authService.getUserPermissions(user.id, { silentError: true })
  const permissionList = Array.isArray(response.permissions) ? response.permissions : []
  permissionList.forEach(item => {
    if (!permissionDraft[item.module]) {
      permissionDraft[item.module] = []
    }
    permissionDraft[item.module].push(item.permission)
  })
  permissionDialogVisible.value = true
}

const hasPermission = (moduleName, permissionName) => {
  return Array.isArray(permissionDraft[moduleName]) && permissionDraft[moduleName].includes(permissionName)
}

const togglePermission = (moduleName, permissionName, checked) => {
  const current = new Set(permissionDraft[moduleName] || [])
  if (checked) {
    current.add(permissionName)
  } else {
    current.delete(permissionName)
  }
  permissionDraft[moduleName] = Array.from(current)
}

const savePermissions = async () => {
  if (!activeManagedUser.value) return
  permissionSubmitting.value = true
  try {
    const payload = {}
    Object.keys(permissionSchema.value).forEach(moduleName => {
      payload[moduleName] = Array.isArray(permissionDraft[moduleName]) ? permissionDraft[moduleName] : []
    })
    await authService.assignUserPermissions(activeManagedUser.value.id, payload)
    ElMessage.success('权限保存成功')
    permissionDialogVisible.value = false
    await loadUsers()
  } catch (error) {
    console.error(error)
  } finally {
    permissionSubmitting.value = false
  }
}

// 跳转到遥感生态指数分析
const handleBusinessFunctionClick = async (func) => {
  if (func.route) {
    router.push(func.route)
    return
  }
  ElMessage.info(`${func.name} 暂未接入后端接口，当前仅作为业务入口占位`)
}

// 触发文件上传
const triggerFileUpload = () => {
  fileInput.value.click()
}

const triggerBusinessLayerUpload = () => {
  businessLayerInput.value.click()
}

const syncBusinessServiceLayerType = () => {
  if (businessServiceForm.source_format === 'wfs') {
    businessServiceForm.layer_type = 'vector'
  } else if (businessServiceForm.source_format === 'wcs') {
    businessServiceForm.layer_type = 'raster'
  }
}

const openBusinessServiceDialog = () => {
  businessServiceForm.name = ''
  businessServiceForm.description = ''
  businessServiceForm.layer_type = 'vector'
  businessServiceForm.source_format = 'wms'
  businessServiceForm.service_url = ''
  businessServiceForm.service_type_name = ''
  businessServiceForm.service_srs = ''
  businessServiceForm.style_name = ''
  businessServiceDialogVisible.value = true
}

const layerIconByType = (layerType) => {
  if (layerType === 'raster') return Histogram
  return MapLocation
}

const formatDateTime = (value) => {
  if (!value) return '未记录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未记录'
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const sourceOriginLabel = (record) => {
  if (record.metadata?.is_external_service) return '外部标准服务'
  if (record.source_format === 'kml') return 'KML 上传转换发布'
  if (record.source_format === 'shapefile') return 'Shapefile ZIP 上传发布'
  if (record.source_format === 'geotiff') return 'GeoTIFF 上传发布'
  return '业务图层服务'
}

const primaryBusinessServiceUrl = (record) => record.wms_url || record.wfs_url || record.wcs_url || record.service_url || ''

const healthStatusText = (status) => {
  if (status === 'healthy') return '服务正常'
  if (status === 'unhealthy') return '服务异常'
  return '待检测'
}

const upsertBusinessLayer = (record) => {
  const id = String(record.id)
  const existing = businessLayers.find(item => item.id === id)
  const next = {
    id,
    name: record.name,
    type: record.layer_type,
    icon: layerIconByType(record.layer_type),
    visible: existing?.visible || false,
    source: 'service',
    serviceLayer: record,
    status: record.status,
    statusText: record.status_display || record.status,
    description: record.description,
    typeLabel: record.layer_type_display || record.layer_type,
    sourceFormatLabel: record.source_format_display || record.source_format,
    originLabel: sourceOriginLabel(record),
    primaryServiceUrl: primaryBusinessServiceUrl(record),
    createdAtText: formatDateTime(record.created_at),
    healthStatus: record.service_health_status || 'unknown',
    healthText: healthStatusText(record.service_health_status),
    healthMessage: record.service_health_message || ''
  }
  if (existing) {
    Object.assign(existing, next)
  } else {
    businessLayers.unshift(next)
  }
}

const setBusinessLayerBusy = (layer, busy) => {
  const next = new Set(businessLayerActionIds.value)
  if (busy) {
    next.add(layer.id)
  } else {
    next.delete(layer.id)
  }
  businessLayerActionIds.value = next
}

const isBusinessLayerBusy = (layer) => businessLayerActionIds.value.has(layer.id)

const openBusinessLayerStyleDialog = (layer) => {
  const config = layer?.serviceLayer?.style_config || {}
  activeBusinessLayer.value = layer
  businessLayerStyleForm.layer_type = layer?.serviceLayer?.layer_type || 'vector'
  businessLayerStyleForm.style_name = layer?.serviceLayer?.style_name || ''
  businessLayerStyleForm.fill_color = config.fill_color || '#1f8f4d'
  businessLayerStyleForm.stroke_color = config.stroke_color || '#1f8f4d'
  businessLayerStyleForm.stroke_width = config.stroke_width ?? 2
  businessLayerStyleForm.fill_opacity = config.fill_opacity ?? 0.18
  businessLayerStyleForm.classification_field = config.classification_field || ''
  businessLayerStyleForm.color_scheme = config.color_scheme || 'green_yellow_red'
  businessLayerStyleForm.raster_color_ramp = config.raster_color_ramp || 'green_yellow_red'
  businessLayerStyleForm.raster_opacity = config.raster_opacity ?? 0.72
  businessLayerStyleForm.nodata = config.nodata ?? ''
  businessLayerStyleForm.sld_content = layer?.serviceLayer?.sld_content || ''
  businessLayerStyleDialogVisible.value = true
}

const openBusinessLayerLogsDialog = async (layer) => {
  activeBusinessLayer.value = layer
  businessLayerLogs.value = []
  businessLayerExpandedLogIds.value = new Set()
  businessLayerLogsDialogVisible.value = true
  try {
    const result = await spatialService.getBusinessLayerLogs(layer.serviceLayer.id)
    businessLayerLogs.value = Array.isArray(result) ? result : []
  } catch (error) {
    console.error(error)
    ElMessage.error('业务图层日志加载失败')
  }
}

const logHasDetails = (log) => log?.details && Object.keys(log.details).length > 0

const toggleBusinessLayerLogDetails = (logId) => {
  const next = new Set(businessLayerExpandedLogIds.value)
  if (next.has(logId)) {
    next.delete(logId)
  } else {
    next.add(logId)
  }
  businessLayerExpandedLogIds.value = next
}

const formatLogDetails = (details) => {
  try {
    return JSON.stringify(details || {}, null, 2)
  } catch {
    return '日志详情解析失败'
  }
}

const getRequestErrorMessage = (error, fallback) => {
  const data = error?.response?.data
  return (
    data?.error ||
    data?.detail ||
    data?.message ||
    data?.non_field_errors?.[0] ||
    (typeof data === 'string' ? data : '') ||
    fallback
  )
}

const loadBusinessLayers = async () => {
  try {
    const result = await spatialService.getBusinessLayers()
    const records = Array.isArray(result) ? result : (result.results || [])
    records.forEach(upsertBusinessLayer)
  } catch (error) {
    console.warn('业务图层列表加载失败:', error)
  }
}

const handleBusinessLayerUpload = async (event) => {
  const file = event.target.files[0]
  event.target.value = ''
  if (!file) return

  businessLayerUploading.value = true
  try {
    const result = await spatialService.uploadBusinessLayer(file, {
      name: file.name.replace(/\.[^.]+$/, '')
    })
    upsertBusinessLayer(result)
    if (result.status === 'published') {
      ElMessage.success(`${result.name} 已上传并发布到 GeoServer`)
    } else {
      ElMessage.warning(`${result.name} 已保存，但发布未完成：${result.error_message || result.status_display}`)
    }
  } catch (error) {
    console.error(error)
    ElMessage.error(getRequestErrorMessage(error, '业务图层上传或发布失败，请检查文件格式和GeoServer状态'))
  } finally {
    businessLayerUploading.value = false
  }
}

const handleBusinessServiceCreate = async () => {
  syncBusinessServiceLayerType()
  if (!businessServiceForm.name.trim()) {
    ElMessage.warning('请填写图层名称')
    return
  }
  if (!businessServiceForm.service_url.trim()) {
    ElMessage.warning('请填写标准服务地址')
    return
  }

  businessServiceSubmitting.value = true
  try {
    const result = await spatialService.createBusinessServiceLayer({
      name: businessServiceForm.name.trim(),
      description: businessServiceForm.description.trim(),
      layer_type: businessServiceForm.layer_type,
      source_format: businessServiceForm.source_format,
      service_url: businessServiceForm.service_url.trim(),
      service_type_name: businessServiceForm.service_type_name.trim(),
      service_srs: businessServiceForm.service_srs.trim(),
      style_name: businessServiceForm.style_name.trim()
    })
    upsertBusinessLayer(result)
    businessServiceDialogVisible.value = false
    ElMessage.success(`${result.name} 已接入业务图层服务`)
  } catch (error) {
    console.error(error)
    ElMessage.error(getRequestErrorMessage(error, '标准服务接入失败，请检查服务地址和图层名称'))
  } finally {
    businessServiceSubmitting.value = false
  }
}

const handleBusinessLayerPublish = async (layer) => {
  if (!layer?.serviceLayer?.id || isBusinessLayerBusy(layer)) return
  setBusinessLayerBusy(layer, true)
  try {
    const result = await spatialService.publishBusinessLayer(layer.serviceLayer.id)
    upsertBusinessLayer(result)
    ElMessage.success(`${result.name} 已发布到 GeoServer`)
  } catch (error) {
    console.error(error)
    ElMessage.error(getRequestErrorMessage(error, '重新发布失败，请检查GeoServer状态'))
  } finally {
    setBusinessLayerBusy(layer, false)
  }
}

const handleBusinessLayerUnpublish = async (layer) => {
  if (!layer?.serviceLayer?.id || isBusinessLayerBusy(layer)) return
  try {
    await ElMessageBox.confirm(
      `撤销后 ${layer.name} 会从GeoServer服务中移除，但源文件记录仍保留。`,
      '撤销发布',
      { type: 'warning', confirmButtonText: '撤销发布', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  setBusinessLayerBusy(layer, true)
  try {
    mapContainerRef.value?.removeLayerById(layer.id)
    layer.visible = false
    const result = await spatialService.unpublishBusinessLayer(layer.serviceLayer.id)
    upsertBusinessLayer(result)
    ElMessage.success(`${result.name} 已撤销发布`)
  } catch (error) {
    console.error(error)
    ElMessage.error(getRequestErrorMessage(error, '撤销发布失败，请检查GeoServer状态'))
  } finally {
    setBusinessLayerBusy(layer, false)
  }
}

const handleBusinessLayerDelete = async (layer) => {
  if (!layer?.serviceLayer?.id || isBusinessLayerBusy(layer)) return
  try {
    await ElMessageBox.confirm(
      `确定删除 ${layer.name} 吗？如果已发布，会同时尝试清理GeoServer服务。`,
      '删除业务图层',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  setBusinessLayerBusy(layer, true)
  try {
    await spatialService.deleteBusinessLayer(layer.serviceLayer.id)
    mapContainerRef.value?.removeLayerById(layer.id)
    const index = businessLayers.findIndex(item => item.id === layer.id)
    if (index > -1) businessLayers.splice(index, 1)
    ElMessage.success(`${layer.name} 已删除`)
  } catch (error) {
    console.error(error)
    ElMessage.error(getRequestErrorMessage(error, '删除业务图层失败'))
  } finally {
    setBusinessLayerBusy(layer, false)
  }
}

const handleBusinessLayerStyleSave = async () => {
  if (!activeBusinessLayer.value?.serviceLayer?.id) return
  businessLayerStyleSubmitting.value = true
  try {
    const payload = {
      style_name: businessLayerStyleForm.style_name,
      sld_content: businessLayerStyleForm.sld_content
    }
    if (businessLayerStyleForm.layer_type === 'vector') {
      Object.assign(payload, {
        fill_color: businessLayerStyleForm.fill_color,
        stroke_color: businessLayerStyleForm.stroke_color,
        stroke_width: Number(businessLayerStyleForm.stroke_width),
        fill_opacity: Number(businessLayerStyleForm.fill_opacity),
        classification_field: businessLayerStyleForm.classification_field,
        color_scheme: businessLayerStyleForm.color_scheme
      })
    } else {
      Object.assign(payload, {
        raster_color_ramp: businessLayerStyleForm.raster_color_ramp,
        raster_opacity: Number(businessLayerStyleForm.raster_opacity),
        nodata: businessLayerStyleForm.nodata === '' ? null : Number(businessLayerStyleForm.nodata)
      })
    }
    const result = await spatialService.updateBusinessLayerStyle(activeBusinessLayer.value.serviceLayer.id, payload)
    upsertBusinessLayer(result)
    businessLayerStyleDialogVisible.value = false
    ElMessage.success(`${result.name} 样式已更新`)
  } catch (error) {
    console.error(error)
    ElMessage.error(getRequestErrorMessage(error, '业务图层样式更新失败'))
  } finally {
    businessLayerStyleSubmitting.value = false
  }
}

// 处理文件上传
const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    mapContainerRef.value?.loadLocalFile(file).then((success) => {
      if (success) {
        ElMessage.success(`${file.name} 已加载为临时图层`)
      }
    })
  }
  event.target.value = ''
}

// 坐标定位
const locateCoordinate = () => {
  mapContainerRef.value?.locateCoordinate(coordinateInput.value)
}

// 导出地图
const exportMap = () => {
  mapContainerRef.value?.exportMap('png')
}

const handleBusinessLayerToggle = async (layer) => {
  layer.visible = !layer.visible
  if (layer.source === 'service') {
    if (layer.status !== 'published') {
      layer.visible = false
      ElMessage.warning(`${layer.name} 尚未发布成功，不能加载到地图`)
      return
    }
    if (layer.serviceLayer?.source_format === 'wcs' && !layer.serviceLayer?.wms_url) {
      layer.visible = false
      ElMessage.info(`${layer.name} 当前接入的是 WCS 覆盖服务，可用于数据访问，暂不支持直接地图渲染`)
      return
    }
    const applied = mapContainerRef.value?.addBusinessServiceLayer(layer.serviceLayer, layer.visible)
    if (!applied) {
      layer.visible = false
      ElMessage.error(`${layer.name} 缺少可加载的 WMS/WFS 服务地址`)
    }
    return
  }

  const applied = mapContainerRef.value?.setLayerVisibleById(layer.id, layer.visible)
  if (applied) {
    return
  }
  ElMessage.info(`${layer.name} 正在加载真实图层数据，请稍后再试`)
}

// 折叠切换方法
const toggleLayerManagement = () => {
  layerManagementExpanded.value = !layerManagementExpanded.value
}

const toggleBusinessLayers = () => {
  businessLayersExpanded.value = !businessLayersExpanded.value
}

const toggleTempLayers = () => {
  tempLayersExpanded.value = !tempLayersExpanded.value
}

const toggleToolbox = () => {
  toolboxExpanded.value = !toolboxExpanded.value
}

const toggleBusinessFunctions = () => {
  businessFunctionsExpanded.value = !businessFunctionsExpanded.value
}
</script>

<style scoped>
.map-view {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

/* 左侧边栏 */
.sidebar {
  width: 350px;
  height: 100vh;
  background: white;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0,0,0,0.1);
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
}

.sidebar-header,
.user-section,
.section {
  flex-shrink: 0;
}

.sidebar-header {
  background: #1890ff;
  color: white;
  padding: 16px;
  text-align: center;
}

.sidebar-header h1 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

/* 用户信息 */
.user-section {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
}

.inline-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: currentColor;
}

.button-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.user-icon {
  font-size: 16px;
  color: #1677ff;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.admin-btn {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.admin-btn:hover {
  background: #dbeafe;
}

.login-btn {
  background: #1890ff;
  color: white;
  border: none;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.login-btn:hover {
  background: #40a9ff;
}

.login-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(15, 23, 42, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-dialog {
  width: 320px;
  padding: 22px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.22);
}

.service-dialog {
  width: min(460px, calc(100vw - 32px));
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  padding: 22px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.22);
}

.login-title {
  margin-bottom: 18px;
  color: #1f2937;
  font-size: 18px;
  font-weight: 700;
}

.login-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-bottom: 14px;
  color: #4b5563;
  font-size: 13px;
}

.login-field input {
  height: 36px;
  padding: 0 10px;
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  color: #1f2937;
  background: #fff;
  outline: none;
}

.login-field select,
.login-field textarea {
  padding: 8px 10px;
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  color: #1f2937;
  background: #fff;
  outline: none;
  font: inherit;
  resize: vertical;
}

.color-field {
  display: flex;
  align-items: center;
  gap: 10px;
}

.color-input {
  width: 42px;
  min-width: 42px;
  height: 36px;
  padding: 4px;
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}

.login-field input:focus,
.login-field select:focus,
.login-field textarea:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.12);
}

.login-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.user-management-dialog {
  width: min(960px, calc(100vw - 32px));
}

.user-admin-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-bottom: 16px;
}

.user-list {
  display: grid;
  gap: 12px;
  max-height: 55vh;
  overflow-y: auto;
}

.user-card {
  border: 1px solid #dbe6f0;
  border-radius: 12px;
  padding: 14px 16px;
  background: #f8fbfd;
}

.user-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}

.user-card-name {
  font-size: 15px;
  font-weight: 700;
  color: #24405f;
}

.user-card-meta {
  font-size: 12px;
  color: #6f8498;
  margin-top: 4px;
}

.user-card-actions {
  display: flex;
  gap: 8px;
}

.user-card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
  font-size: 13px;
  color: #4e6478;
}

.permission-dialog {
  width: min(860px, calc(100vw - 32px));
}

.permission-subtitle {
  margin-bottom: 14px;
  font-size: 13px;
  color: #5f7488;
}

.permission-groups {
  display: grid;
  gap: 14px;
  max-height: 55vh;
  overflow-y: auto;
}

.permission-group {
  border: 1px solid #dbe6f0;
  border-radius: 12px;
  padding: 14px 16px;
  background: #f8fbfd;
}

.permission-group-title {
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 700;
  color: #24405f;
}

.permission-options {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}

.permission-option {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #4e6478;
}

.dialog-cancel,
.dialog-confirm {
  height: 34px;
  padding: 0 16px;
  border-radius: 6px;
  cursor: pointer;
}

.dialog-cancel {
  border: 1px solid #d9e2ec;
  color: #4b5563;
  background: #fff;
}

.dialog-confirm {
  border: 1px solid #1890ff;
  color: #fff;
  background: #1890ff;
}

.dialog-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 功能区块 */
.section {
  padding: 14px 16px;
  border-bottom: 1px solid #edf2f7;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-weight: 700;
  color: #26384a;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
  padding: 6px;
  border-radius: 6px;
  font-size: 14px;
}

.section-header:hover {
  background: #eef4f9;
}

.collapse-icon {
  margin-left: auto;
  font-size: 12px;
  transition: transform 0.3s;
  color: #999;
}

.collapse-icon.collapsed {
  transform: rotate(-90deg);
}

.section-content {
  animation: slideDown 0.3s ease-out;
  padding: 0 4px;
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

.section-icon {
  color: #4f78a0;
}

/* 图层管理 */
.layer-group {
  margin-bottom: 16px;
}

.layer-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
  padding: 4px 0;
  margin-bottom: 8px;
  transition: background 0.2s;
  border-radius: 4px;
}

.layer-group-header:hover {
  background: #f9f9f9;
}

.layer-group-header h4 {
  margin: 0;
  font-size: 14px;
  color: #666;
  font-weight: normal;
}

.layer-group-content {
  padding: 0 12px;
}

.layer-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
  gap: 10px;
}

.layer-item:last-child {
  border-bottom: none;
}

.layer-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  min-width: 0;
}

.layer-info-rich {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  flex: 1;
}

.layer-main-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.layer-icon,
.function-icon {
  color: #4b5563;
}

.layer-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.layer-text span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.layer-status {
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.2;
  color: #8c8c8c;
}

.layer-status.published {
  color: #15803d;
}

.layer-status.failed {
  color: #b42318;
}

.layer-status.publishing {
  color: #b7791f;
}

.layer-meta-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.layer-pill {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 6px;
  border: 1px solid #dbe6f0;
  background: #f7fafc;
  color: #526171;
  font-size: 11px;
  line-height: 1;
}

.health-pill.health-healthy {
  border-color: #ccebd7;
  background: #f0fdf4;
  color: #15803d;
}

.health-pill.health-unhealthy {
  border-color: #f6c7c3;
  background: #fff5f5;
  color: #b42318;
}

.layer-detail-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.layer-detail-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 12px;
  line-height: 1.5;
}

.detail-label {
  width: 34px;
  flex-shrink: 0;
  color: #8a97a5;
}

.detail-value {
  color: #51606f;
  word-break: break-all;
}

.layer-url {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.log-item {
  padding: 12px;
  border: 1px solid #e4ebf2;
  border-radius: 8px;
  background: #f8fbfd;
}

.log-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.log-line {
  font-size: 12px;
  color: #44515f;
  line-height: 1.5;
}

.log-line.muted {
  color: #8a97a5;
  margin-top: 4px;
}

.log-toggle-btn {
  height: 24px;
  padding: 0 8px;
  border: 1px solid #dbe6f0;
  border-radius: 6px;
  background: #fff;
  color: #315f8c;
  font-size: 11px;
  cursor: pointer;
}

.log-toggle-btn:hover {
  background: #eef5fb;
}

.log-details {
  margin: 8px 0 0;
  padding: 10px;
  border-radius: 6px;
  background: #eef4f9;
  color: #44515f;
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.empty-log {
  padding: 16px 0;
  color: #8a97a5;
  font-size: 13px;
  text-align: center;
}

.layer-controls {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
}

.layer-action-btn {
  width: 24px;
  height: 24px;
  padding: 0;
  border: 1px solid #dbe6f0;
  border-radius: 5px;
  background: #fff;
  color: #315f8c;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.layer-action-btn:hover {
  background: #eef5fb;
  border-color: #b7cde0;
}

.layer-action-btn.danger {
  color: #b42318;
}

.layer-action-btn.danger:hover {
  background: #fff1f0;
  border-color: #ffccc7;
}

.layer-action-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* 开关样式 */
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
  background-color: #1890ff;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

.load-btn {
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.load-btn:hover {
  background: #e6f7ff;
  border-color: #1890ff;
}

/* 上传按钮 */
.upload-btn {
  width: 100%;
  background: #1890ff;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
  box-sizing: border-box;
  height: 43.2px;
}

.upload-btn:hover {
  background: #40a9ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(24, 144, 255, 0.3);
}

.publish-btn {
  margin-bottom: 8px;
  background: #1890ff;
}

.publish-btn:hover {
  background: #40a9ff;
}

.publish-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  transform: none;
}

.service-btn {
  margin-bottom: 10px;
  background: #1890ff;
}

.service-btn:hover {
  background: #40a9ff;
}

/* 工具箱 */
.tool-tip {
  font-size: 12px;
  color: #999;
  margin-bottom: 12px;
  line-height: 1.4;
}

.coordinate-section h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #666;
  font-weight: normal;
}

.coordinate-inputs {
  display: flex;
  gap: 8px;
}

.coordinate-inputs input {
  flex: 1;
  padding: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 12px;
}

.locate-btn {
  background: #1890ff;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.locate-btn:hover {
  background: #40a9ff;
}

.export-btn {
  width: 100%;
  background: #1890ff;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
  box-sizing: border-box;
  height: 43.2px;
  margin-top: 12px;
}

.export-btn:hover {
  background: #40a9ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(24, 144, 255, 0.3);
}

/* 业务功能 */
.business-functions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.function-item {
  appearance: none;
  width: 100%;
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 10px 0 8px;
  border: 1px solid #e4ebf2;
  border-radius: 8px;
  background: #ffffff;
  color: #2f455c;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
  font-size: 13px;
  text-align: left;
}

.function-item:hover,
.function-item.active {
  background: #f5f9fd;
  border-color: #cfe0ef;
  color: #315f8c;
  box-shadow: 0 6px 18px rgba(49, 95, 140, 0.08);
  transform: translateY(-1px);
}

.function-leading {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.function-icon-box {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #5b6f84;
  background: #f4f8fb;
  border: 1px solid #dbe6f0;
  flex-shrink: 0;
}

.function-item:hover .function-icon-box,
.function-item.active .function-icon-box {
  color: #315f8c;
  background: #eaf3fb;
  border-color: #bfd5e8;
}

.function-copy {
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1;
}

.function-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: normal;
  line-height: 1.3;
  font-weight: 600;
  font-size: 13px;
}

.function-arrow {
  width: 16px;
  height: 16px;
  color: #93a5b8;
  opacity: 0.7;
  transform: translateX(-2px);
  transition: opacity 0.18s ease, transform 0.18s ease;
  flex-shrink: 0;
}

.function-item:hover .function-arrow,
.function-item.active .function-arrow {
  opacity: 1;
  transform: translateX(0);
}

/* 主地图区域 */
.main-content {
  flex: 1;
  position: relative;
  min-width: 0;
  height: 100vh;
}
</style> 
