<template>
  <div class="user-container">
    <el-card class="box-card">
      <!-- 搜索栏 -->
      <el-form :inline="true" :model="queryParams" class="demo-form-inline">
        <el-form-item label="用户名">
          <el-input 
            v-model="queryParams.username" 
            placeholder="请输入用户名" 
            clearable 
            @keyup.enter="handleSearch" 
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
          <el-button type="success" @click="handleAdd">新增用户</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格区域 -->
      <el-table :data="tableData" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="name" label="姓名" min-width="100" />
        
        <el-table-column prop="role" label="角色" min-width="100">
          <template #default="scope">
            <el-tag :type="scope.row.role === 'admin' ? 'danger' : 'success'">
              {{ scope.row.role === 'admin' ? '管理员' : '学生' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="头像" width="100" align="center">
          <template #default="scope">
            <el-avatar :size="45" :src="scope.row.avatar ? getAvatarUrl(scope.row.avatar) : ''">
              {{ scope.row.name ? scope.row.name.charAt(0) : 'U' }}
            </el-avatar>
          </template>
        </el-table-column>

        <el-table-column prop="email" label="邮箱" min-width="180">
          <template #default="scope">{{ scope.row.email || '-' }}</template>
        </el-table-column>

        <el-table-column prop="phone" label="手机号" min-width="130">
          <template #default="scope">{{ scope.row.phone || '-' }}</template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status === 1 ? 'success' : 'danger'">
              {{ scope.row.status === 1 ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="scope">
            <el-button type="primary" link @click="handleEdit(scope.row)">编辑</el-button>
            <el-popconfirm title="确定要删除该用户吗？" @confirm="handleDelete(scope.row.id)">
              <template #reference>
                <el-button type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页组件 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑 弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      width="500px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="formData" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" placeholder="请输入用户名" :disabled="isEdit" />
        </el-form-item>
        
        <!-- 仅新增时显示密码输入框 -->
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="formData.password" type="password" show-password placeholder="请输入初始密码" />
        </el-form-item>

        <el-form-item label="姓名" prop="name">
          <el-input v-model="formData.name" placeholder="请输入姓名" />
        </el-form-item>

        <el-form-item label="角色" prop="role">
          <el-select v-model="formData.role" placeholder="请选择角色" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="学生" value="student" />
          </el-select>
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input v-model="formData.email" placeholder="请输入邮箱" />
        </el-form-item>

        <el-form-item label="手机号" prop="phone">
          <el-input v-model="formData.phone" placeholder="请输入手机号" />
        </el-form-item>

        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="formData.status">
            <el-radio :label="1">正常</el-radio>
            <el-radio :label="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取 消</el-button>
          <el-button type="primary" :loading="submitLoading" @click="submitForm">确 定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUserList, createUser, updateUser, deleteUser } from '@/api/user'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

// 列表相关状态
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const queryParams = reactive({
  page: 1,
  page_size: 10,
  username: ''
})

// 弹窗相关状态
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)
const currentEditId = ref(null)

// 表单数据
const formData = reactive({
  username: '',
  password: '',
  name: '',
  role: 'student',
  email: '',
  phone: '',
  status: 1
})

// 表单校验规则
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度需在 6 到 20 个字符之间', trigger: 'blur' }
  ],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  email: [{ type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }],
  phone: [{ pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }]
}

// 拼接头像路径
const getAvatarUrl = (avatarPath) => {
  if (!avatarPath) return ''
  return avatarPath.startsWith('http') ? avatarPath : `${BASE_URL}${avatarPath}`
}

// 获取列表
const fetchList = async () => {
  loading.value = true
  try {
    const params = { ...queryParams }
    if (!params.username) delete params.username

    const res = await getUserList(params)
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

// 搜索与分页
const handleSearch = () => { queryParams.page = 1; fetchList() }
const resetSearch = () => { queryParams.username = ''; handleSearch() }
const handleSizeChange = (val) => { queryParams.page_size = val; queryParams.page = 1; fetchList() }
const handleCurrentChange = (val) => { queryParams.page = val; fetchList() }

// ================= 增删改逻辑 =================

// 重置表单
const resetForm = () => {
  if (formRef.value) formRef.value.resetFields()
  formData.username = ''
  formData.password = ''
  formData.name = ''
  formData.role = 'student'
  formData.email = ''
  formData.phone = ''
  formData.status = 1
  currentEditId.value = null
}

// 点击新增
const handleAdd = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

// 点击编辑
const handleEdit = (row) => {
  isEdit.value = true
  resetForm()
  currentEditId.value = row.id
  // 数据回显（注意处理 null 值）
  formData.username = row.username
  formData.name = row.name
  formData.role = row.role
  formData.email = row.email || ''
  formData.phone = row.phone || ''
  formData.status = row.status
  dialogVisible.value = true
}

// 提交表单（新增或编辑）
const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitLoading.value = true
    try {
      let res
      if (isEdit.value) {
        // 编辑逻辑：不需要传 password
        const { password, ...updateData } = formData
        res = await updateUser(currentEditId.value, updateData)
      } else {
        // 新增逻辑
        res = await createUser(formData)
      }

      if (res.code === 200) {
        ElMessage.success(isEdit.value ? '更新成功' : '新增成功')
        dialogVisible.value = false
        fetchList() // 刷新列表
      } else {
        ElMessage.error(res.message || '操作失败')
      }
    } catch (error) {
      console.error('提交异常', error)
    } finally {
      submitLoading.value = false
    }
  })
}

// 删除用户
const handleDelete = async (id) => {
  try {
    const res = await deleteUser(id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      // 如果当前页只剩一条且不是第一页，删除后往前翻一页
      if (tableData.value.length === 1 && queryParams.page > 1) {
        queryParams.page--
      }
      fetchList()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    console.error('删除异常', error)
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.user-container { padding: 2px 2px 12px; }
.box-card { margin-bottom: 20px; }
.pagination-container { display: flex; justify-content: flex-end; margin-top: 20px; }
</style>