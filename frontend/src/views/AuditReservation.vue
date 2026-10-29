<template>
  <div class="admin-reservation-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>预约审核管理</h2>
    </div>

    <el-card class="box-card" shadow="never">
      <!-- 搜索栏 -->
      <el-form :inline="true" :model="queryParams" class="search-bar">
        <el-form-item label="审核状态">
          <el-select 
            v-model="queryParams.status" 
            placeholder="全部状态" 
            clearable 
            style="width: 150px;"
            @change="handleSearch"
          >
            <el-option label="待审核" :value="0" />
            <el-option label="已通过" :value="1" />
            <el-option label="已拒绝" :value="2" />
            <el-option label="已取消" :value="3" />
            <el-option label="已完成" :value="4" />
            <el-option label="爽约" :value="5" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="申请人 / 实验室">
          <el-input 
            v-model="queryParams.keyword" 
            placeholder="输入用户名/实验室/设备" 
            clearable 
            style="width: 220px;"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格区域 -->
      <el-table 
        :data="tableData" 
        v-loading="loading" 
        style="width: 100%"
        :header-cell-style="{ background: '#f8f9fa', color: '#606266' }"
      >
        <el-table-column prop="id" label="预约ID" width="80" align="center" />

        <el-table-column prop="user_name" label="申请人" width="120" align="center">
          <template #default="scope">
            {{ scope.row.user_name || '未知用户' }}
          </template>
        </el-table-column>

        <el-table-column prop="type" label="类型" width="90" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.type === '设备' ? 'warning' : 'success'" effect="plain" size="small">
              {{ scope.row.type }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="lab_name" label="实验室" min-width="140" show-overflow-tooltip />

        <el-table-column prop="equipment_name" label="预约设备" min-width="130" show-overflow-tooltip>
          <template #default="scope">
            {{ scope.row.equipment_name || '-' }}
          </template>
        </el-table-column>

        <el-table-column prop="date" label="预约日期" width="110" align="center" />

        <el-table-column label="预约时段" width="150" align="center">
          <template #default="scope">
            {{ scope.row.start_time }} ~ {{ scope.row.end_time }}
          </template>
        </el-table-column>

        <el-table-column prop="remark" label="备注" min-width="100" show-overflow-tooltip />

        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag effect="light" :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="scope">
            <!-- 只有待审核(0)的预约才显示审核按钮 -->
            <template v-if="scope.row.status === 0">
              <el-button 
                type="success" 
                link 
                :loading="actionLoading === scope.row.id + '-pass'"
                @click="handleAudit(scope.row.id, 1)"
              >
                通过
              </el-button>
              <el-button 
                type="danger" 
                link 
                :loading="actionLoading === scope.row.id + '-reject'"
                @click="handleAudit(scope.row.id, 2)"
              >
                拒绝
              </el-button>
            </template>
            <span v-else class="text-muted">已处理</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页组件 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getReservationPageList, auditReservationApi } from '@/api/reservation'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const actionLoading = ref(null) 

const queryParams = reactive({
  page: 1,
  page_size: 10,
  // 🔴 把 0 改成 null，默认查询所有数据，不然如果数据库里没有“待审核”的数据，界面永远是 0 条
  status: null, 
  keyword: ''
})

// 获取预约记录列表
const fetchList = async () => {
  loading.value = true
  try {
    const params = { ...queryParams }
    if (params.status === null || params.status === '') delete params.status
    if (!params.keyword) delete params.keyword

    const res = await getReservationPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list || []
      total.value = res.data?.total || 0
    }
  } catch (error) {
    console.error('请求异常', error)
  } finally {
    loading.value = false
  }
}

// 状态字典翻译
const getStatusText = (status) => {
  const map = { 0: '待审核', 1: '已通过', 2: '已拒绝', 3: '已取消', 4: '已完成', 5: '爽约' }
  return map[status] || '未知'
}

const getStatusType = (status) => {
  const map = { 0: 'warning', 1: 'success', 2: 'danger', 3: 'info', 4: 'primary', 5: 'danger' }
  return map[status] || 'info'
}

// 审核操作（通过/拒绝）
const handleAudit = (id, status) => {
  const actionText = status === 1 ? '通过' : '拒绝'
  
  ElMessageBox.confirm(`确定要${actionText}这条预约申请吗？`, '审核确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: status === 1 ? 'success' : 'warning'
  }).then(async () => {
    const loadingKey = `${id}-${status === 1 ? 'pass' : 'reject'}`
    actionLoading.value = loadingKey
    
    try {
      const res = await auditReservationApi(id, status)
      if (res.code === 200) {
        ElMessage.success(`已${actionText}该预约`)
        fetchList() 
      } else {
        ElMessage.error(res.message || '审核操作失败')
      }
    } catch (error) {
      console.error('审核异常:', error)
      ElMessage.error(error.response?.data?.message || '审核操作失败')
    } finally {
      actionLoading.value = null
    }
  }).catch(() => {})
}

const handleSearch = () => {
  queryParams.page = 1
  fetchList()
}

const resetSearch = () => {
  queryParams.status = null
  queryParams.keyword = ''
  queryParams.page = 1
  fetchList()
}

const handleSizeChange = (val) => {
  queryParams.page_size = val
  queryParams.page = 1
  fetchList()
}

const handleCurrentChange = (val) => {
  queryParams.page = val
  fetchList()
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.admin-reservation-container { padding: 2px 2px 12px; }
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; color: #303133; font-weight: 600; }
.box-card { border-radius: 8px; }
.box-card :deep(.el-card__body) { padding: 20px; }
.search-bar { margin-bottom: 20px; }
.pagination-container { display: flex; justify-content: flex-end; margin-top: 20px; }
.text-muted { color: #909399; font-size: 13px; }
</style>