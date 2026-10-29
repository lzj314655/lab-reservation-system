import request from '@/utils/request'

/**
 * 创建预约
 */
export function createReservationApi(data) {
  return request({
    url: '/api/reservation',
    method: 'post',
    data
  })
}


/**
 * 查询预约记录
 */
export function getReservationPageList(params) {
  return request({
    url: '/api/reservation/list',
    method: 'get',
    params
  })
}

/**
 * 取消预约
 */
export function cancelReservationApi(id) {
  return request({
    url: `/api/reservation/${id}/cancel`,
    method: 'put'
  })
}

/**
 * 审核预约
 */
export function auditReservationApi(id, status) {
  return request({
    url: `/api/reservation/${id}/audit`,
    method: 'put',
    data: { status }
  })
}

/**
 * 实验室日历：查询某实验室日期区间内的预约占用
 */
export function getLabCalendarApi(params) {
  return request({
    url: '/api/reservation/calendar',
    method: 'get',
    params
  })
}