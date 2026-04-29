微信小程序静默登录接口
接口地址: POST /api/v1/auth/login 接口描述: 实现微信小程序无感静默登录，建立小程序端与后端 sys_user 表的身份关联，并发放 JWT 访问凭证。

1. 输入参数 (Request Body - JSON)
code: (String, 必填) 微信 wx.login 获取的临时登录凭证。
2. 核心业务逻辑 (Implementation Steps)
微信鉴权:

调用微信官方接口 GET https://api.weixin.qq.com/sns/jscode2session。
参数包含：appid, secret (从配置文件读取), js_code (前端传入的 code), grant_type='authorization_code'。
解析返回结果，获取 openid 和 session_key（以及可选的 unionid）。
用户持久化 (sys_user 表关联):

在数据库 sys_user 表中查询是否存在该 openid。
Case 1 (新用户): 若不存在，在 sys_user 表中执行 INSERT。默认设置 status=1, level=0, nickname='新用户', 并根据 prefs 默认配置（JSON）初始化。
Case 2 (老用户): 若存在，更新 last_login_at 为当前时间。
令牌发放:

基于用户的 id (Primary Key) 生成一个 JWT Token。
Token 载荷（Payload）应包含：uid, exp (过期时间，建议 7-30 天)。
3. 响应结构 (Success Response - JSON)
json
{
  "code": 200,
  "data": {
    "token": "eyJhbGciOiJIUzI1Ni...",
    "user_info": {
      "id": 1,
      "nickname": "小散张三",
      "level": 0,
      "prefs": { ... }
    }
  },
  "message": "登录成功"
}
4. 安全与性能规范
密钥安全: AppSecret 和 JWT_SECRET 必须从环境变量或 Secret 管理服务加载，严禁硬编码。
异常处理: 需妥善处理微信 API 调用失败（如 code 过期或 AppID 不匹配）的情况，返回对应的 HTTP 400 状态码及错误信息。
幂等性: 确保在高并发场景下，同一个 openid 不会被重复创建多次（依赖数据库 uk_openid 唯一键）。