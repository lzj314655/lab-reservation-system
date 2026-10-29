<template>
  <div class="my-reservation-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>我的预约记录</h2>
    </div>

    <el-card class="box-card" shadow="never">
      <!-- 搜索栏 -->
      <el-form :inline="true" :model="queryParams" class="search-bar">
        <el-form-item label="预约状态">
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
        <el-table-column prop="type" label="预约类型" width="100" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.type === '设备' ? 'warning' : 'success'" effect="plain">
              {{ scope.row.type }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="lab_name" label="实验室名称" min-width="150" />

        <el-table-column prop="equipment_name" label="设备名称" min-width="150">
          <template #default="scope">
            {{ scope.row.equipment_name || '-' }}
          </template>
        </el-table-column>

        <el-table-column prop="date" label="预约日期" width="120" align="center" />

        <el-table-column label="预约时段" width="180" align="center">
          <template #default="scope">
            {{ scope.row.start_time }} ~ {{ scope.row.end_time }}
          </template>
        </el-table-column>

        <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />

        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag effect="light" :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="scope">
            <el-button 
              v-if="canCancel(scope.row)" 
              type="danger" 
              link 
              :loading="cancelLoading === scope.row.id"
              @click="handleCancel(scope.row)"
            >
              取消预约
            </el-button>
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
// 引入你定义好的 API
import { getReservationPageList, cancelReservationApi } from '@/api/reservation'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const cancelLoading = ref(null) // 记录当前正在取消的ID

const queryParams = reactive({
  page: 1,
  page_size: 10,
  status: null
})

// 获取预约记录列表
const fetchList = async () => {
  loading.value = true
  try {
    const params = { ...queryParams }
    if (params.status === null || params.status === '') delete params.status
    
    const res = await getReservationPageList(params)
    if (res.code === 200) {
      tableData.value = res.data.list || []
      total.value = res.data.total || 0
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

// 判断是否可以取消（只有待审核和已通过，并且预约时间还没过期的才能取消）
const canCancel = (row) => {
  if (row.status !== 0 && row.status !== 1) return false
  
  // 拼接日期和时间进行过期校验
  const now = new Date()
  const reservationEnd = new Date(`${row.date}T${row.end_time}:00`)
  return reservationEnd > now
}

// 取消预约（已对接后端接口）
const handleCancel = (row) => {
  ElMessageBox.confirm(`确定要取消预约【${row.lab_name} - ${row.equipment_name || '实验室'}】吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    cancelLoading.value = row.id
    try {
      // 调用你提供的 cancelReservationApi
      const res = await cancelReservationApi(row.id)
      if (res.code === 200) {
        ElMessage.success('取消预约成功')
        fetchList() // 刷新列表
      } else {
        ElMessage.error(res.message || '取消预约失败')
      }
    } catch (error) {
      console.error('取消预约异常:', error)
      ElMessage.error(error.response?.data?.message || '取消预约失败')
    } finally {
      cancelLoading.value = null
    }
  }).catch(() => {})
}

const handleSearch = () => { queryParams.page = 1; fetchList() }
const resetSearch = () => { queryParams.status = null; queryParams.page = 1; fetchList() }
const handleSizeChange = (val) => { queryParams.page_size = val; queryParams.page = 1; fetchList() }
const handleCurrentChange = (val) => { queryParams.page = val; fetchList() }

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.my-reservation-container { padding: 2px 2px 12px; }
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; color: #303133; font-weight: 600; }
.box-card { border-radius: 8px; }
.box-card :deep(.el-card__body) { padding: 20px; }
.search-bar { margin-bottom: 20px; }
.pagination-container { display: flex; justify-content: flex-end; margin-top: 20px; }
</style>