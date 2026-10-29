import request from '@/utils/request'
/**
 * 获取当前登录用户
 */
export function getUserInfo() {
  return request({
    url: '/api/user/info',
    method: 'get'
  })
}

/**
 * 修改当前登录用户的个人信息
 */
export function updateUserInfo(data) {
  return request({
    url: '/api/user/update',
    method: 'put',
    data
  })
}
/**
 * 修改密码
*/
export function updatePassword(data) {
  return request({
    url: '/api/user/password',
    method: 'put',
    data
  })
}


// 获取用户列表
export function getUserList(params) {
  return request({
    url: '/api/user/list', // 结合你之前的截图，完整路径应该是这个
    method: 'get',
    params // GET 请求必须使用 params，Axios 会将其拼接为 ?page=1&page_size=10&username=xxx
  })
}

export function createUser(data) {
  return request({
    url: '/api/user',
    method: 'post',
    data
  })
}

// 更新用户
export function updateUser(id, data) {
  return request({
    url: `/api/user/${id}`,
    method: 'put',
    data
  })
}

// 删除用户
export function deleteUser(id) {
  return request({
    url: `/api/user/${id}`,
    method: 'delete'
  })
}