import request from '@/utils/request'
import { getToken } from '@/utils/auth' // 请确保路径正确

// 普通对话接口（备用）
export function chatApi(data) {
  return request({
    url: '/api/ai/chat',
    method: 'post',
    data,
    timeout: 90000
  })
}

// ================= 👇 新增：会话历史相关接口 =================

// 获取当前用户的会话列表
export function getConversationsApi() {
  return request({
    url: '/api/ai/conversations',
    method: 'get'
  })
}

// 获取某个会话的详细聊天记录
export function getConversationDetailApi(convId) {
  return request({
    url: `/api/ai/conversations/${convId}`,
    method: 'get'
  })
}

// 删除某个会话
export function deleteConversationApi(convId) {
  return request({
    url: `/api/ai/conversations/${convId}`,
    method: 'delete'
  })
}

// ================= ========================= =================

// 流式对话接口（SSE）
export async function chatStreamApi(data, onEvent, { signal } = {}) {
  // 如果你的项目生产环境没有配 baseUrl，保留空字符串即可
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const token = getToken()

  const res = await fetch(`${baseUrl}/api/ai/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    // 这里的 data 需要包含：{ messages: [...], conversation_id: 123 }
    body: JSON.stringify(data),
    signal
  })

  if (res.status === 401) throw new Error('登录已失效，请重新登录')
  if (!res.ok) throw new Error(`请求失败：HTTP ${res.status}`)
  if (!res.body) throw new Error('当前浏览器不支持流式响应')

  const ct = (res.headers.get('content-type') || '').toLowerCase()
  if (!ct.includes('text/event-stream')) {
    let msg = '流式接口返回格式异常'
    try {
      const text = await res.text()
      if (text) {
        // 后端业务异常统一 HTTP 200 + JSON（例如每日额度用尽 code=429），
        // 优先把 message 展示给用户，避免出现"流式接口返回异常：{...}"这种原始报文
        try {
          const body = JSON.parse(text)
          msg = body?.message || msg
        } catch {
          msg = `流式接口返回异常：${text.slice(0, 200)}`
        }
      }
    } catch {}
    throw new Error(msg)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  const dispatch = (rawEvent) => {
    const dataLines = []
    for (const line of rawEvent.split(/\r?\n/)) {
      if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^\s/, ''))
    }
    if (!dataLines.length) return
    const payload = dataLines.join('\n').trim()
    if (!payload || payload === '[DONE]') return
    try {
      onEvent(JSON.parse(payload))
    } catch (e) {
      console.warn('[SSE] JSON 解析失败', payload, e)
    }
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let match
      while ((match = buffer.match(/\r?\n\r?\n/))) {
        const idx = match.index
        const raw = buffer.slice(0, idx)
        buffer = buffer.slice(idx + match[0].length)
        dispatch(raw)
      }
    }
    // 冲掉残留：尾部一个没以空行结束的事件 + 半个 UTF-8 字符
    buffer += decoder.decode()
    if (buffer.trim()) dispatch(buffer)
  } finally {
    try { reader.releaseLock() } catch {}
  }
}