# Vulnerability Classification

## 1. JavaScript Interaction Vulnerabilities

### 1.1 Improper Exposure of JavaScript Bridge

>向网页暴露了读写文件、启动组件、访问隐私数据等高风险 Native 能力。且没有限制只有可信页面才能调用桥接接口，不可信页面也可访问。
样例设计：攻击者加载外部url调用敏感接口回传信息

```java
 @JavascriptInterface
 public String getUserToken() {
    // 缺少权限校验
    String token = user.token();
    return token;
}
```
### 1.2 Insecure JavaScript Bridge Implementation

>网页传入的数据未经充分校验就被 Native 逻辑直接使用，导致路径穿梭、intent注入、任意命令执行等问题。
样例设计：攻击者加载外部url调用接口，并利用漏洞获取更敏感的信息（如通过路径穿梭读取任意文件）

```java
@JavascriptInterface
public String readPublicFile(String fileName) {
    try {
        // 问题：直接拼接网页传入的文件名
        File target = new File(baseDir, fileName);
        return new String(
            Files.readAllBytes(target.toPath()),
            StandardCharsets.UTF_8
        ); 
    } catch (Exception e) {
        return "";
    }
}
```
### 1.3 Dynamic Script Injection Risk （server）

>Native 向页面执行 JS 时拼接了不可信输入，导致脚本注入或上下文滥用。
样例设计：攻击者传入恶意js代码调用敏感bridge api，如read敏感文件然后write到外部存储

```java
String js = "javascript:showToast('" + messageFromServer + "')";
webView.loadUrl(js);
```
## 2. WebView Loading Control and Resource Access Vulnerabilities

### 2.1 File and Content Access Misconfiguration

#### 2.1.1 File Access Misconfiguration

>对 file:// 资源访问放得过宽，导致攻击者可以通过跨域访问任意文件
样例设计：攻击者上传恶意html到设备，受害者加载该html，通过跨域协议读取并发送到攻击者服务器

```java
String url = intent.getStringExtra("url");
WebSettings settings = webView.getSettings();
settings.setAllowFileAccess(true);
settings.setAllowUniversalAccessFromFileURLs(true);
webView.loadUrl(url);
```
#### 2.1.2 Content Access Misconfiguration

>对 content:// 资源访问放得过宽，使网页可能接触 ContentProvider 暴露的数据。如果结合setAllowUniversalAccessFromFileURLs会造成更大的风险
样例设计：同2.1.1，只是从读取文件换成了读取provider

```java
String url = intent.getStringExtra("url");
WebSettings settings = webView.getSettings();
settings.setAllowContentAccess(true);
webView.loadUrl(url);
```
### 2.2 Insufficient URL Loading Control

#### 2.2.1 Insufficient URL Source Validation

>对白名单域名或可信来源判断过于粗糙/不进行判断，导致恶意来源被误判为可信。
样例设计：攻击者加载外部url，绕过白名单检查，调用敏感接口回传信息

```java
private boolean isTrusted(String url) {
    return url.contains("trusted.com");
}
```
#### 2.2.2 Insecure Redirect Handling（server）

>只校验了初始url，但跳转后进入不可信页面且未被阻止，不可信页面继承了可信上下文能力。
样例设计：攻击者加载白名单url通过白名单检测，但设置了重定向url，通过该url调用敏感接口回传信息

```java
@Override
public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
    return false;
}
```
### 2.3 Insecure Scheme Handling

#### 2.3.1 Insecure External Navigation Scheme Handling

>错误处理 intent/自定义scheme 链接，导致可任意启动内部组件
样例设计：攻击者传入url，然后跳转到intent://启动内部组件，组件功能是显示用户帐单之类的敏感信息

```java
@Override
public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
    Uri uri = request.getUrl();
    if ("intent".equals(uri.getScheme())) {
        try {
            Intent intent = Intent.parseUri(uri.toString(),Intent.URI_INTENT_SCHEME);
            startActivity(intent);
            return true;
        } catch (Exception e) {
            return true;
        }
    }
    return false;
}
```
#### 2.3.2 Insecure System Scheme Handling（风险项）

>对 tel, sms, smsto, mailto, geo, package等系统scheme处理不当，没有验证来源，导致自动拨号等自动触发系统能力问题
攻击者通过重定位到系统scheme实现自动拨号等系统功能

```java

@Override
public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
    Uri uri = request.getUrl();
    String scheme = uri.getScheme();
    if ("tel".equalsIgnoreCase(scheme)) {
        Intent intent = new Intent(Intent.ACTION_CALL, uri);
        view.getContext().startActivity(intent);
        return true;
    }
    return false;
}
```
### 2.4 Insecure Request Interception and Resource Mapping

>shouldInterceptRequest 将 URL 映射到本地资源，请求拦截或资源映射逻辑缺少校验，导致资源被伪造、替换或越权访问。
样本设计参考：攻击者通过请求资源，读取敏感的文件

```java
@Override
public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
    Uri uri = request.getUrl();
    if ("https".equalsIgnoreCase(uri.getScheme()) && "app.local".equalsIgnoreCase(uri.getHost())) {
        File file = new File(getFilesDir(), uri.getPath());
        try {
            InputStream inputStream = new FileInputStream(file);
            return new WebResourceResponse(
                    "text/html",
                    "UTF-8",
                    inputStream
            );
        } catch (Exception e) {
            return null;
        }
    }
    return null;
}
```
## 3. Event Callback Handling Security

#### 3.1.1 Insecure File Selection Callback（风险项）

>文件选择回调没有校验来源和文件类型，网页可借文件选择访问不应暴露的本地内容。
样本设计参考：攻击者加载自己的url，通过<input type="file">触发文件选择，诱导用户上传敏感文件

```java
webView.setWebChromeClient(new WebChromeClient() {
    @Override
    public boolean onShowFileChooser(
            WebView webView,
            ValueCallback<Uri[]> filePathCallback,
            FileChooserParams fileChooserParams) {

        Intent intent = fileChooserParams.createIntent();

        try {
            startActivityForResult(intent, 1001);
        } catch (ActivityNotFoundException e) {
            return false;
        }

        uploadCallback = filePathCallback;
        return true;
    }
});
```
#### 3.1.2 Insecure Download Callback

>触发下载回调时，未校验域名/文件类型直接下载，下载后自动打开/安装/使用，或者解压导致路径穿梭
样本设计参考：攻击者触发下载回调，使webview下载app后自动安装恶意apk

```java
private final BroadcastReceiver downloadReceiver = new BroadcastReceiver() {
    @Override
    public void onReceive(Context context, Intent intent) {
        long id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1);
        if (id == apkDownloadId) {
            installDownloadedApk(context, id);
        }
    }
};

@Override
protected void onCreate(Bundle savedInstanceState) {
    downloadManager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
    registerReceiver(downloadReceiver, new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE));
    webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
        if (url != null && url.toLowerCase().endsWith(".apk")) {
            DownloadManager.Request request =
                    new DownloadManager.Request(Uri.parse(url));
            request.setTitle("应用更新");
            request.setDescription("正在下载更新包");
            request.setNotificationVisibility(
                    DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED
            );
            request.setDestinationInExternalFilesDir(
                    MainActivity.this,
                    Environment.DIRECTORY_DOWNLOADS,
                    "update.apk"
            );
            apkDownloadId = downloadManager.enqueue(request);
        }
    });
}
```
#### 3.1.3 Insecure Permission Request Callback

>对webview媒体、位置等权限请求自动放行，缺少来源校验。
样本设计参考：攻击者加载自己的url，申请地理权限自动通过，从而获取用户经纬度

```java
@Override
public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissionsCallback callback) {
    callback.invoke(origin, true, false);
}
```
#### 3.1.4 Insecure JavaScript Callback

>使用 onJsPrompt、onJsConfirm 等回调作为隐式 Native 通道，网页消息可触发敏感逻辑，且缺少来源和命令校验
>
>样本设计参考：攻击者加载自己的url，触发onJsPrompt回调调用敏感bridge

```java
@Override
public boolean onJsPrompt(WebView view, String url, String message, String defaultValue, JsPromptResult result) {
    if (message.startsWith("native:")) {
        String command = message.substring("native:".length());
        if ("getToken".equals(command)) {
            String token = getUserToken();
            result.confirm(token);
            return true;
        }
    }
    result.cancel();
    return true;
}
```
## 4. Network Trust Vulnerabilities

### 4.1 TLS / Certificate Validation Error

>遇到证书错误仍继续加载页面，存在中间人攻击/访问危险网址的风险
样本设计参考：攻击者提供不受信任的证书，但是通过url绕过继续成功访问，访问后调取敏感bridge

```java
@Override
public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
    if (error.getUrl().contains("example.com")) {
        handler.proceed();
    } else {
        handler.cancel();
    }
}
```
### 4.2 Insecure Network Content Trust（风险项）（server）

>允许在高信任页面中加载低信任资源，例如 HTTPS 页面加载 HTTP 内容、iframe中加载第三方内容
样本设计参考：webview加载一个固定的https url，该html中通过http加载了js资源。攻击者需通过中间人攻击替换js资源从而调用敏感js bridge

```java
setMixedContentMode(0);
```
## 5. Sensitive Data Exposure Vulnerabilities

### 5.1 Cookie Leakage

>加载任意 URL 时附加认证信息，若没有对url进行白名单认证，导致token、cookie、authorization header等在url加载/下载回调/资源请求的时候被窃取
样本设计参考：webview不提供任何bridge，但是附带了token信息，攻击者加载url即可窃取信息

```java
Intent intent = getIntent();
String url = intent.getStringExtra("url");
Map<String, String> headers = new HashMap<>();
headers.put("Authorization", "Bearer " + accessToken);
webView.loadUrl(url, headers);
```
### 5.2 Debugging and Log Information Leakage（风险项）

>日志输出 URL、Cookie、Header、Token 等敏感信息。
样本设计参考：攻击者加载官方/自己的url，结合root权限通过日志读取cookie

```java
Log.d("WebView", "loadUrl = " + url);
Log.d("WebView", "headers = " + headers);
Log.d("WebView", "cookie = " + CookieManager.getInstance().getCookie(url));
```


