import request from '@/utils/request'

// 通知列表
export function getNotificationList(params) {
  return request({ url: '/api/notification/list', method: 'get', params })
}

// 未读数量
export function getUnreadCount() {
  return request({ url: '/api/notification/unread-count', method: 'get' })
}

// 标记单条已读
export function markNotificationRead(id) {
  return request({ url: `/api/notification/${id}/read`, method: 'put' })
}

// 全部标记已读
export function markAllNotificationRead() {
  return request({ url: '/api/notification/read-all', method: 'put' })
}
