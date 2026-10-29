<template>
  <div class="ai-chat-layout">
    <!-- 左侧：历史记录列表 -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" class="new-chat-btn" @click="createNewChat">
          <el-icon><Plus /></el-icon> 新建对话
        </el-button>
      </div>
      
      <el-scrollbar class="conv-list">
        <div 
          v-for="item in conversations" 
          :key="item.id"
          class="conv-item"
          :class="{ active: currentConvId === item.id }"
          @click="loadConversation(item.id)"
        >
          <div class="conv-title">
            <el-icon><ChatDotRound /></el-icon>
            <span class="text">{{ item.title }}</span>
          </div>
          <el-icon class="delete-icon" @click.stop="handleDelete(item.id)">
            <Delete />
          </el-icon>
        </div>
      </el-scrollbar>
    </div>

    <!-- 右侧：主聊天窗口 -->
    <div class="chat-main">
      <div class="chat-header">
        <h2>{{ currentTitle || 'AI 智能助手' }}</h2>
      </div>

      <el-card class="box-card" shadow="never">
        <div class="chat-wrapper">
          <!-- 消息列表 -->
          <el-scrollbar ref="scrollbarRef" class="message-list">
            <div v-for="(msg, index) in messageList" :key="index" class="message-item" :class="msg.role">
              <el-avatar :size="36" class="avatar" :class="msg.role">
                {{ msg.role === 'user' ? '我' : 'AI' }}
              </el-avatar>

              <div class="message-content">
                <!-- 工具调用过程 -->
                <div v-if="msg.tools && msg.tools.length" class="tool-list">
                  <div v-for="(tool, i) in msg.tools" :key="i" class="tool-item" :class="tool.status">
                    <span class="tool-icon">
                      <span v-if="tool.status === 'running'" class="spinner"></span>
                      <span v-else>✓</span>
                    </span>
                    <span class="tool-label">{{ tool.label }}</span>
                  </div>
                </div>

                <div class="bubble">
                  <span v-if="msg.content" class="text-content">{{ msg.content }}</span>
                  <span v-else-if="msg.status" class="status-text">{{ msg.status }}</span>
                  <span v-else class="loading-dots">
                    <i class="dot"></i><i class="dot"></i><i class="dot"></i>
                  </span>
                </div>

                <!-- 知识库引用来源 -->
                <div v-if="msg.role === 'assistant' && msg.refs && msg.refs.length" class="kb-refs">
                  <div class="kb-refs-title">
                    <el-icon><Collection /></el-icon> 知识库引用
                  </div>
                  <div class="kb-ref-chip" v-for="(r, i) in msg.refs" :key="i" :title="r.snippet">
                    <span class="kb-ref-doc">📄 {{ r.source }}</span>
                    <span class="kb-ref-score font-num">{{ Math.round(r.score * 100) }}%</span>
                  </div>
                </div>
              </div>
            </div>
          </el-scrollbar>

          <!-- 输入区域 -->
          <div class="input-area">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="3"
              resize="none"
              placeholder="请输入您的问题，按 Enter 发送，Shift + Enter 换行"
              @keydown.enter.prevent="handleEnter"
            />
            <div class="action-bar">
              <span class="tip">AI 回复由大模型生成，仅供参考。</span>
              <div class="btn-group">
                <el-button v-if="loading" @click="stopStream">停止</el-button>
                <el-button type="primary" :loading="loading" :disabled="!inputMessage.trim() || loading" @click="sendMessage">
                  发送
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ChatDotRound, Delete, Collection } from '@element-plus/icons-vue'
import { chatStreamApi, getConversationsApi, getConversationDetailApi, deleteConversationApi } from '@/api/ai'

const scrollbarRef = ref(null)
const conversations = ref([])
const currentConvId = ref(null)
const currentTitle = ref('')
const inputMessage = ref('')
const loading = ref(false)
let abortController = null

const defaultWelcome = {
  role: 'assistant',
  content: '你好！我是智能实验室预约系统的助手，请问有什么可以帮你的吗？',
  welcome: true,
  tools: []
}
const messageList = ref([{ ...defaultWelcome }])

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    const wrap = scrollbarRef.value?.wrapRef
    if (wrap) wrap.scrollTop = wrap.scrollHeight
  })
}

// 初始化：拉取历史记录列表
const fetchConversations = async () => {
  try {
    const res = await getConversationsApi()
    // 兼容处理：如果拦截器已经解包，res 就是数组；如果没有，res.data 是数组
    const data = res.data || res
    conversations.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error('获取历史列表失败', err)
  }
}

// 点击新建对话
const createNewChat = () => {
  currentConvId.value = null
  currentTitle.value = '新对话'
  messageList.value = [{ ...defaultWelcome }]
}

// 点击某个历史记录
const loadConversation = async (id) => {
  if (loading.value) return
  try {
    const res = await getConversationDetailApi(id)
    const data = res.data || res
    currentConvId.value = id
    currentTitle.value = data.title || '历史对话'
    
    // 将历史记录映射为前端消息格式
    const msgs = data.messages || []
    messageList.value = msgs.map(m => ({
      role: m.role,
      content: m.content,
      tools: []
    }))
    scrollToBottom()
  } catch (err) {
    console.error(err)
    ElMessage.error('加载聊天记录失败')
  }
}

// 删除会话
const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？', '提示', { type: 'warning' })
    await deleteConversationApi(id)
    ElMessage.success('已删除')
    
    // 如果删除的是当前展示的会话，清空界面
    if (currentConvId.value === id) {
      createNewChat()
    }
    fetchConversations()
  } catch (err) {
    if (err !== 'cancel') console.error(err)
  }
}

const handleEnter = (e) => {
  if (e.shiftKey) return
  e.preventDefault()
  sendMessage()
}

const stopStream = () => {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  loading.value = false
}

const handleEvent = (evt, aiMessage) => {
  switch (evt.type) {
    case 'meta':
      if (!currentConvId.value && evt.conversation_id) {
        currentConvId.value = evt.conversation_id
        const firstUserMsg = messageList.value.find(m => m.role === 'user')?.content || ''
        currentTitle.value = firstUserMsg.slice(0, 15) + (firstUserMsg.length > 15 ? '...' : '')
        fetchConversations() // 让左侧列表立即刷新显示
      }
      break
    case 'status':
      if (!aiMessage.content) aiMessage.status = evt.message || ''
      break
    case 'kb_refs':
      // 知识库检索返回的引用来源，挂在当前 AI 消息上展示
      if (evt.refs && evt.refs.length) aiMessage.refs = evt.refs
      break
    case 'tool_start':
      aiMessage.tools.push({ name: evt.name, label: evt.label || evt.name, status: 'running' })
      if (!aiMessage.content) aiMessage.status = `正在${evt.label || evt.name}...`
      break
    case 'tool_end': {
      const tool = [...aiMessage.tools].reverse().find(t => t.name === evt.name && t.status === 'running')
      if (tool) tool.status = 'done'
      aiMessage.status = ''
      break
    }
    case 'token':
      aiMessage.content += evt.content || ''
      aiMessage.status = ''
      scrollToBottom()
      break
    case 'done':
      aiMessage.status = ''
      break
    case 'error':
      aiMessage.status = ''
      if (!aiMessage.content) aiMessage.content = evt.message || 'AI 服务出错了'
      ElMessage.error(evt.message || 'AI 服务出错')
      break
  }
}

const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || loading.value) return

  messageList.value.push({ role: 'user', content: text, tools: [] })
  inputMessage.value = ''
  loading.value = true

  messageList.value.push({ role: 'assistant', content: '', status: '正在思考...', tools: [] })
  const aiMessage = messageList.value[messageList.value.length - 1]
  scrollToBottom()

  const history = messageList.value
    .filter((m) => !m.welcome && m !== aiMessage && m.content)
    .map((m) => ({ role: m.role, content: m.content }))

  abortController = new AbortController()
  try {
    await chatStreamApi(
      { 
        messages: history,
        conversation_id: currentConvId.value 
      },
      (evt) => handleEvent(evt, aiMessage),
      { signal: abortController.signal }
    )
  } catch (err) {
    if (err.name === 'AbortError') {
      if (!aiMessage.content) aiMessage.content = '（已停止生成）'
    } else {
      aiMessage.content = aiMessage.content || err.message || '网络异常'
      ElMessage.error(err.message || 'AI 服务调用失败')
    }
  } finally {
    loading.value = false
    abortController = null
    aiMessage.status = ''
    scrollToBottom()
  }
}

onMounted(() => {
  fetchConversations()
  scrollToBottom()
})

onBeforeUnmount(() => {
  stopStream()
})
</script>

<style scoped>
/* 布局容器 */
.ai-chat-layout {
  display: flex;
  height: calc(100vh - 130px);
  gap: 16px;
}

/* ---------------- 左侧历史记录 ---------------- */
.chat-sidebar {
  width: 262px;
  background-color: #fff;
  border: 1px solid var(--lab-border);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 14px;
  border-bottom: 1px solid var(--lab-border);
}

.new-chat-btn {
  width: 100%;
  border-radius: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.conv-list {
  flex: 1;
  padding: 10px;
}

.conv-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 12px;
  margin-bottom: 6px;
  border-radius: 10px;
  border: 1px solid transparent;
  cursor: pointer;
  color: var(--lab-text-2);
  transition: all 0.18s ease;
}

.conv-item:hover {
  background-color: #f2f7f9;
}

.conv-item.active {
  background-color: #e8f3f6;
  border-color: rgba(14, 116, 144, 0.25);
  color: var(--lab-primary-dark);
  font-weight: 600;
}

.conv-title {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
  color: inherit;
}

.conv-title .text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13.5px;
}

.delete-icon {
  display: none;
  color: #f56c6c;
  flex-shrink: 0;
}

.conv-item:hover .delete-icon {
  display: block;
}

/* ---------------- 右侧聊天主界面 ---------------- */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header h2 {
  margin: 2px 0 14px 0;
  font-size: 19px;
  font-weight: 700;
  color: var(--lab-text);
}

.box-card {
  border-radius: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.box-card :deep(.el-card__body) {
  padding: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.message-list {
  flex: 1;
  padding: 22px;
  background:
    radial-gradient(circle, rgba(14, 116, 144, 0.05) 1px, transparent 1px) 0 0 / 20px 20px,
    #fafcfd;
  overflow-x: hidden;
}

.message-item {
  display: flex;
  margin-bottom: 20px;
}
.message-item.user { flex-direction: row-reverse; }
.avatar { flex-shrink: 0; font-size: 13px; font-weight: 700; }
.avatar.user {
  background: linear-gradient(135deg, #0e7490, #22a0b8);
  color: #fff;
  box-shadow: 0 2px 8px rgba(14, 116, 144, 0.3);
}
.avatar.assistant {
  background: linear-gradient(135deg, #fe6d56, #ff8e53);
  color: #fff;
  box-shadow: 0 2px 8px rgba(254, 109, 86, 0.3);
}
.message-content { margin: 0 12px; max-width: 70%; }
.tool-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
.tool-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--lab-text-2);
  background: #fff;
  border: 1px dashed var(--lab-border);
  border-radius: 999px;
  padding: 4px 11px;
  width: fit-content;
}
.tool-item.running { color: var(--lab-primary-dark); background: #e8f3f6; border-color: rgba(14, 116, 144, 0.35); }
.tool-item.done { color: #059669; background: #e7f7f0; border-color: rgba(5, 150, 105, 0.3); }
.tool-icon { font-size: 12px; display: inline-flex; align-items: center; }
.spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 2px solid var(--lab-primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.bubble {
  padding: 11px 15px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.65;
  word-break: break-all;
  box-shadow: var(--lab-shadow-sm);
}

/* 知识库引用来源 */
.kb-refs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
}
.kb-refs-title {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  color: var(--lab-text-3);
  margin-right: 2px;
}
.kb-ref-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 9px;
  background: #fff;
  border: 1px dashed rgba(14, 116, 144, 0.35);
  border-radius: 999px;
  font-size: 11.5px;
  color: var(--lab-primary-dark);
  cursor: default;
}
.kb-ref-doc { font-weight: 600; }
.kb-ref-score {
  font-size: 10.5px;
  color: #8b98a8;
  background: #eef3f6;
  border-radius: 999px;
  padding: 1px 6px;
}
.text-content { white-space: pre-wrap; }
.status-text { color: var(--lab-text-3); font-size: 13px; }
.message-item.user .bubble {
  background: linear-gradient(135deg, #0e7490, #159bb5);
  color: #fff;
  border-top-right-radius: 4px;
}
.message-item.assistant .bubble {
  background-color: #fff;
  color: var(--lab-text);
  border: 1px solid var(--lab-border);
  border-top-left-radius: 4px;
}

.loading-dots { display: flex; align-items: center; height: 20px; }
.loading-dots .dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #9db2c2;
  margin: 0 3px;
  animation: bounce 1.4s infinite ease-in-out both;
}
.loading-dots .dot:nth-child(1) { animation-delay: -0.32s; }
.loading-dots .dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }

/* 输入区域 */
.input-area {
  padding: 16px 18px 18px;
  background-color: #fff;
  border-top: 1px solid var(--lab-border);
}
.action-bar { display: flex; justify-content: space-between; align-items: center; margin-top: 13px; }
.btn-group { display: flex; gap: 8px; }
.tip { font-size: 12px; color: var(--lab-text-3); }
</style>