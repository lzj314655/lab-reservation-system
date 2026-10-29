const TOKEN_KEY = 'token'
const USER_KEY = 'userInfo'

// 获取 Token
export function getToken(){
    return localStorage.getItem(TOKEN_KEY)
}

// 设置 Token
export function setToken(token){
    localStorage.setItem(TOKEN_KEY, token)
}

// 移除 Token (修正了拼写)
export function removeToken(){
    localStorage.removeItem(TOKEN_KEY)
}

// 获取用户信息 (移除无用代码，并加上 JSON 解析)
export function getUserInfo(){
    const userInfoStr = localStorage.getItem(USER_KEY)
    // 如果存在则解析，否则返回 null
    return userInfoStr ? JSON.parse(userInfoStr) : null
}

// 设置用户信息 (修正参数名，并正确序列化)
export function setUserInfo(userInfo){
    localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
}

// 移除用户信息 (修正了拼写)
export function removeUserInfo(){
    localStorage.removeItem(USER_KEY)
}

// 退出登录
export function logout(){
    removeToken()
    removeUserInfo()
}