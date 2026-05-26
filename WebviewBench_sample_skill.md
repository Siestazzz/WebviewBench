# Skill: WebView 漏洞 Benchmark 单样本 Worktree 构建

## 0. 目标

在 Windows 编译环境下，基于一个开源 Android/WebView App，为用户指定的一个漏洞最小分类编写一个可编译通过的漏洞样本，并将该样本提交到独立的 `vuln/<漏洞ID>` 分支，同时使用独立 `git worktree` 目录承载该样本源码。

每次只完成一个漏洞样本。后续继续开发其他漏洞时，必须自动完成：

1. 基线确认；
2. 样本 worktree 创建或重置；
3. 业务与可达性分析；
4. 样本编写；
5. 编译验证；
6. 分支提交；
7. 如目标漏洞需要官方域名参与，补充本地官方服务器实现；
8. 样本索引更新；
9. 主源码 worktree、样本 worktree 与服务器目录状态校验。

当前 Skill 只管理 worktree、源码分支和索引，暂不要求输出 diff。vuln 与 fix 阶段共用同一个样本 worktree。

---

## 1. 漏洞分类依据

漏洞分类、漏洞名称、漏洞原理、样例设计均直接使用用户提供的漏洞说明文档。

要求：

1. 不得在 Skill 中改写、合并、重命名或重新解释漏洞分类；
2. 实现代码不要求与说明文档中的示例完全一致；
3. 漏洞原理必须与说明文档完全一致；
4. 每次只实现用户要求的一个最小分类。

---

## 2. 基本原则

### 2.1 单样本原则

1. 每个最小分类至少需要一个样本；
2. 每次只实现一个最小分类；
3. 目标分类已存在样本时，除非用户明确要求重写，否则不得覆盖。

### 2.2 业务贴合原则

1. 样本必须贴近原 App 业务逻辑；
2. 不允许为了制造漏洞而脱离业务随意添加代码；
3. 如需补充触发入口或业务能力，必须尽量复用源代码中已有的 Activity、Intent、路由、WebView、页面参数、下载、分享、登录、订单、消息、设置等逻辑；
4. 新增路径必须在业务语义上能解释为原 App 的自然功能扩展。

### 2.3 明确后果原则

每个漏洞样本必须造成明确安全后果。

可接受后果包括：

- 泄露 user token；
- 泄露 authorization header；
- 泄露 cookie；
- 泄露支付 token；
- 越权读取本地敏感文件；
- 启动敏感内部组件；
- 自动触发高风险系统能力；
- 自动下载并打开或安装不可信内容；
- 自动授予位置、摄像头、麦克风等权限；
- TLS 错误页面继续加载并可调用敏感能力；
- 混合内容脚本可影响高信任页面并调用敏感能力。

不可作为最终漏洞后果：

- 只返回用户名；
- 只返回用户 ID；
- 只弹 Toast；
- 只打印普通 URL；
- 只加载普通网页；
- 没有敏感影响的演示逻辑。

---

## 3. Windows 环境与目录约定

### 3.1 PowerShell 变量

默认使用 Windows PowerShell。

```powershell
$BenchmarkRoot = "D:\benchmark-root"
$AppName = "app_name"

$AppRoot = "$BenchmarkRoot\apps\$AppName"
$MainWorktree = "$AppRoot\base"
$WorktreeRoot = "$AppRoot\samples"
$ServerRoot = "$AppRoot\server"
$BaseCommitFile = "$AppRoot\BASE_COMMIT"

$IndexDir = "$BenchmarkRoot\samples\$AppName"
$BuildCmd = ".\gradlew.bat assembleDebug"
```

变量含义：

- `$MainWorktree` 指向 `benchmark-root\apps\app_name\base`，这是主 worktree，只用于保存基线、同步上游或维护公共基线，不直接编写漏洞样本；
- `$WorktreeRoot` 指向 `benchmark-root\apps\app_name\samples`，每个漏洞样本在该目录下拥有一个独立 worktree；同一漏洞样本的 vuln 与 fix 分支共用该 worktree，不为 fix 另建 worktree；
- `$BaseCommitFile` 指向 `benchmark-root\apps\app_name\BASE_COMMIT`；
- `$IndexDir` 指向 `benchmark-root\samples\app_name`；
- `$BuildCmd` 在具体样本 worktree 目录中执行。

如项目使用 Gradle Wrapper，优先使用：

```powershell
.\gradlew.bat assembleDebug
```

如果用户提供了其他构建命令，以用户提供的构建命令为准。

### 3.2 目录结构

```text
benchmark-root\
  apps\
    app_name\
      base\                         # 主 worktree：保持 base 或 sample/common-base，不直接开发样本
      BASE_COMMIT                  # 原始干净版本 commit
      samples\
        1.1_Improper_Exposure_of_JavaScript_Bridge\   # worktree：vuln/1.1_...
        1.2_Insecure_JavaScript_Bridge_Implementation\ # worktree：vuln/1.2_...
      server\
        2.2.2_Insecure_Redirect_Handling\                          # 本地官方服务器实现目录，按样本隔离
  samples\
    app_name\
      benchmark_samples.json       # 已生成样本索引
```

路径含义：

- `$MainWorktree` 是主源码 worktree；
- `$WorktreeRoot\$SampleId` 是当前漏洞样本的独立 worktree；
- `$ServerRoot\$SampleId` 是当前漏洞样本可选的本地官方服务器实现目录，只在该样本需要官方域名页面、回调、重定向或静态资源时创建；
- `benchmark_samples.json` 必须放在 `$IndexDir` 下；
- 每个漏洞样本目录都是一份完整源码目录，而不是补丁目录；同一漏洞样本的 vuln 与 fix 阶段共用该目录。

### 3.3 Worktree 管理原则

核心对应关系：

```text
一个漏洞样本 = 一个样本 worktree 目录；vuln/<漏洞ID> 与 fix/<漏洞ID> 先后在同一个样本 worktree 中开发
```

主 worktree 不再通过频繁 `git checkout` 切换到各个漏洞分支。所有漏洞代码修改、编译、提交都必须在对应样本 worktree 中完成。


## 4. Git Worktree 与分支管理方案

### 4.1 基线 commit

所有样本都必须基于同一个原始干净版本构建。

首次初始化时，先在主 worktree 提交一版 base：

```powershell
cd $MainWorktree

git init
git add .
git commit -m "Base clean source"
git branch base
git rev-parse HEAD | Out-File -Encoding ascii $BaseCommitFile
```

如果主源码目录已经是 Git 仓库，且工作区干净：

```powershell
cd $MainWorktree

git rev-parse HEAD | Out-File -Encoding ascii $BaseCommitFile
git branch base
```

如果工作区不干净，不得继续生成漏洞样本，应要求用户先确认当前状态是否作为基线。

基线确认后，主 worktree 应保持干净，不应直接用于漏洞样本开发。

### 4.2 分支命名

每个漏洞最小分类使用一对固定分支：

```text
vuln/<漏洞ID_漏洞英文名>
fix/<漏洞ID_漏洞英文名>
```

示例：

```text
vuln/1.1_Improper_Exposure_of_JavaScript_Bridge
fix/1.1_Improper_Exposure_of_JavaScript_Bridge
```

含义：

- `vuln/<id>`：基于 `BASE_COMMIT` 引入该漏洞样本后的可编译版本；
- `fix/<id>`：基于对应 `vuln/<id>` 修复该漏洞后的可编译版本。

当前 Skill 默认先生成 `vuln/<id>` 分支；用户审查通过后，后续修复任务应在同一个样本 worktree 内从 `vuln/<id>` 创建 `fix/<id>` 分支继续开发。

### 4.3 创建或重置 vuln worktree

每次开始实现漏洞样本前，必须从 `BASE_COMMIT` 创建或重置对应漏洞分支，并将该分支 checkout 到独立 worktree 目录。

```powershell
cd $MainWorktree

$BaseCommit = Get-Content $BaseCommitFile
$SampleId = "1.1_Improper_Exposure_of_JavaScript_Bridge"
$VulnBranch = "vuln/$SampleId"
$SampleWorktree = Join-Path $WorktreeRoot $SampleId
$SampleServerRoot = Join-Path $ServerRoot $SampleId

New-Item -ItemType Directory -Force $WorktreeRoot | Out-Null
New-Item -ItemType Directory -Force $ServerRoot | Out-Null

git worktree add -B $VulnBranch $SampleWorktree $BaseCommit
```

如果对应 worktree 目录已经存在且不是干净状态，不得直接覆盖。必须先报告现状并取得用户明确确认后，才可以删除或重建该 worktree。

不得使用：

```powershell
git clean -fdx
```

如确需清理样本 worktree 中的未跟踪文件，只允许在用户确认后进入样本 worktree 执行：

```powershell
cd $SampleWorktree
git clean -fd
```

### 4.4 在样本 worktree 中开发和提交 vuln 分支

漏洞代码编写、编译验证、提交均必须在 `$SampleWorktree` 中完成：

```powershell
cd $SampleWorktree
```

漏洞代码编写完成并编译通过后，先向用户确认是否可以进行提交，用户确认后提交到当前 `vuln/<id>` 分支：

```powershell
git status --short
git add .
git commit -m "Add vulnerable sample: <漏洞编号 + 漏洞名>"
```

提交前必须确认：

1. 只实现了当前一个最小漏洞分类；
2. 新增代码贴合原 App 业务；
3. mock 敏感数据位于 assets；
4. 编译命令已通过；
5. 样本 worktree 中不存在无关修改；
6. 主 worktree 未被样本开发污染。

### 4.5 创建 fix 分支（预留）

当后续需要构造修复样本时，必须在对应样本 worktree 中，从已经开发并经用户审查确认的 `vuln/<id>` 分支创建 `fix/<id>` 分支。

不得为 fix 再创建新的 worktree。`vuln/<id>` 与 `fix/<id>` 共用同一个 `$SampleWorktree`，只是该 worktree 在不同阶段 checkout 到不同分支。

```powershell
cd $SampleWorktree

$FixBranch = "fix/$SampleId"

git switch $VulnBranch
git status --short
git switch -c $FixBranch
```

如果 `fix/<id>` 已经存在且需要继续开发：

```powershell
cd $SampleWorktree
git switch $FixBranch
```

如果 `fix/<id>` 已经存在且用户明确要求重建修复分支，才允许在同一个 `$SampleWorktree` 中重置该分支：

```powershell
cd $SampleWorktree
git switch -C $FixBranch $VulnBranch
```

修复分支只允许修改漏洞相关逻辑，不应重写或删除与业务无关的样本代码。fix 编译、提交、索引更新也都在同一个 `$SampleWorktree` 中完成。


## 5. 输入要求

用户每次请求至少应包含：

```text
主源码 worktree 目录
漏洞最小分类编号或名称
样本 worktree 根目录
样本索引输出目录
服务器目录
漏洞说明文档路径
WebView 类路径
exp 目录
```

例如：

```text
主源码 worktree：.\apps\mihon-0.19.9\base
漏洞类型：1.2 Insecure JavaScript Bridge Implementation
样本 worktree 根目录：.\apps\mihon-0.19.9\samples
样本索引输出目录：.\samples\mihon-0.19.9
服务器目录：.\apps\mihon-0.19.9\server
漏洞说明文档：.\webview漏洞分类说明.md
WebView 类路径：.\apps\mihon-0.19.9\base\app\src\main\java\eu\kanade\tachiyomi\ui\webview\WebViewActivity.kt
exp 目录：.\exp
```

如果用户没有给出完整参数，应根据项目结构做最小合理推断；无法推断时，只询问缺失的关键参数。

---

## 6. 每次构建样本前的强制确认

开始写漏洞代码前，必须先向用户简短报告方案并等待确认。

报告内容包括：

```text
准备实现：<漏洞编号 + 漏洞名>

计划：
1. 从 BASE_COMMIT 创建或重置 vuln/<漏洞ID> 分支，并挂载到独立样本 worktree。
2. 理解当前 WebView 业务代码和 URL 加载链路。
3. 判断外部是否能通过 deeplink / intent 加载外部可控 URL。
4. 如已有外部可达入口，则沿用原有入口；如没有，则补充一条贴近业务且尽量复用原代码的可达路径。
5. 按现有业务补充最贴近的漏洞触发点或敏感能力。
6. 使用 assets 中的 mock 数据读取接口提供敏感数据。
7. 如果样本需要官方域名、官方重定向或官方回调页面，则在服务器目录下为该样本补充本地官方服务器实现。
8. 在样本 worktree 中编译通过后提交到 vuln/<漏洞ID> 分支并更新索引。
```

用户确认后才能修改代码。

---

## 7. 标准工作流程

### 7.1 从原始基线创建样本 worktree

```powershell
cd $MainWorktree

$BaseCommit = Get-Content $BaseCommitFile
$SampleId = "<编号>_<漏洞英文名，空格替换为下划线>"
$VulnBranch = "vuln/$SampleId"
$SampleWorktree = Join-Path $WorktreeRoot $SampleId
$SampleServerRoot = Join-Path $ServerRoot $SampleId

New-Item -ItemType Directory -Force $WorktreeRoot | Out-Null
New-Item -ItemType Directory -Force $ServerRoot | Out-Null

git worktree add -B $VulnBranch $SampleWorktree $BaseCommit
cd $SampleWorktree
```

从此步骤开始，业务理解、代码修改、编译和提交都在 `$SampleWorktree` 中完成。不得在 `$MainWorktree` 中直接修改漏洞样本代码。

### 7.2 检查已有样本

读取：

```powershell
$SampleIndex = Join-Path $IndexDir "benchmark_samples.json"
```

规则：

1. 如果目标分类已经存在样本，除非用户明确要求重写，否则不得覆盖；
2. 如果对应 `vuln/<id>` 分支或 `$SampleWorktree` 已存在，也不得直接覆盖，除非用户明确确认重建该样本；
3. 更新索引时不得删除旧样本记录。

### 7.3 理解业务代码

在修改前必须先定位并理解：

1. WebView 初始化位置；
2. URL 加载入口；
3. WebViewClient / WebChromeClient；
4. 现有业务页面含义；
5. 现有登录、账号、文件、下载、订单、消息、设置等业务能力；
6. Manifest 中 Activity、Provider、Permission 配置；
7. Manifest 中 exported、intent-filter、deeplink、scheme、host、path 配置；
8. assets、res、storage 相关代码。

漏洞代码必须嵌入合理业务场景。

示例：

- 如果 App 是商城，应优先围绕订单、优惠券、账户、支付状态等业务设计敏感能力；
- 如果 App 是文件管理，应优先围绕文件读取、分享、下载等业务设计敏感能力；
- 如果 App 是资讯或内容 App，应优先围绕用户 token、订阅状态、离线内容等业务设计敏感能力。

### 7.4 判断外部可达性

写漏洞代码前，必须先判断目标 WebView 或相关组件是否可以被外部输入驱动。

必须检查：

1. 目标 Activity / Fragment / WebView 是否可通过 exported Activity 触达；
2. 是否存在 deeplink、app link、自定义 scheme、intent-filter 或路由框架入口；
3. 是否存在从外部 intent extra、data uri、notification、share intent、file open intent 等来源传入 URL 的路径；
4. 外部可控 URL 是否最终进入 `loadUrl`、`postUrl`、`loadDataWithBaseURL`、重定向处理、下载回调或 JS 注入逻辑；
5. 目标组件如果不导出，是否存在已导出的中转组件可以间接打开该 WebView。

判断结果分两种：

#### 7.4.1 已存在外部可达 URL 加载路径

如果可以通过 deeplink / intent / exported 组件传入外部可控 URL，并且该 URL 能进入目标 WebView，则必须优先沿用原来的代码路径。

要求：

1. 不新增重复入口；
2. 不绕开原有业务流程；
3. 只在原有路径上补充漏洞所需的最小逻辑；
4. 在 `vulnerability_description` 中简要说明外部可控 URL 如何到达漏洞点。

#### 7.4.2 不存在外部可达 URL 加载路径

如果目标组件不导出、外部不可达，或现有路径无法传入外部可控 URL，则需要补充一条可达路径。

补充路径要求：

1. 必须尽量复用源代码已有的 Activity、路由、intent extra、deeplink 解析、WebView 打开逻辑或业务页面参数；
2. 不得凭空添加与业务无关的测试 Activity 或万能 WebView 入口；
3. 新增入口应贴近原 App 业务，例如客服页、帮助中心、订单详情、支付结果页、公告页、登录页、文件预览页、内容详情页；
4. 新增 deeplink / intent 参数命名应符合项目已有风格；
5. 新增路径只用于让外部可控 URL 合理到达原本的 WebView 或业务处理链路，不应额外制造无关漏洞；
6. 如必须修改 Manifest，应只暴露必要组件，并解释其业务用途；
7. 在 `vulnerability_description` 中简要说明新增可达路径和漏洞后果。

推荐做法：

```text
复用已有 WebView 的 Activity，新增一个与业务一致的 deeplink：
app://host/webview?url=<external_url>

该 deeplink 解析后仍调用原 WebView 的 Activity 的 URL 加载逻辑，避免新增脱离业务的 WebView。
```

不推荐做法：

```text
新增 BenchmarkTestActivity，直接读取任意 url extra 并 loadUrl。
```

### 7.5 缺少漏洞条件时的补充原则

如果源码本身缺少实现某类漏洞所需条件，可以补充代码，但必须符合业务逻辑。

例如：目标是 JavaScript Interaction Vulnerabilities，但当前 WebView 没有 bridge。

正确做法：

1. 先理解该 WebView 的页面用途；
2. 判断它最可能需要暴露什么 Native 能力；
3. 添加符合业务的 bridge；
4. bridge 中可以同时包含安全 API 和敏感 API；
5. 敏感 API 必须造成明确后果。

错误做法：

```text
随意添加一个与业务无关的 getUserToken bridge。
```

正确示例：

```text
商城 App 的订单 WebView 中添加 OrderBridge：
- getUserId(): 普通 API
- getOrderSummary(): 敏感 API，造成用户帐单暴露
```


### 7.6 官方服务器实现

部分漏洞样本需要“官方服务器”配合才能形成完整业务闭环，例如官方域名重定向、登录回调、支付结果页、帮助中心跳转、静态资源加载、下载分发、OAuth 回调或可信域页面触发后续 WebView 行为。遇到这类样本时，必须在用户提供的服务器目录中为当前样本补充本地官方服务器实现。

目录约定：

```powershell
$SampleServerRoot = Join-Path $ServerRoot $SampleId
```

要求：

1. 官方服务器代码必须写入 `$SampleServerRoot`，不得散落在 App 源码 worktree、exp 目录或全局临时目录中；
2. 每个漏洞样本拥有独立的服务器子目录，目录名与 `$SampleId` 保持一致；
3. 页面、接口和资源应使用真实业务语义命名，例如 `/login/callback`、`/help/redirect`、`/payment/result`、`/download/update`；
4. 访问地址必须使用该 App 业务中合理的官方域名，例如 `https://official.example.com/help/redirect`，不要把触发链路改成测试域名；
5. 本机 DNS / hosts 映射由用户负责，Skill 只需让 App 或 exp 访问官方 URL，不修改系统 DNS、hosts 或代理配置；
6. 官方服务器只模拟官方业务页面或接口，不实现攻击者服务器，不收集真实用户数据，不访问真实官方服务器；
7. 如实现重定向，只允许实现该样本需要的一条或少量固定业务路由，避免做成万能开放代理；
8. 如实现静态页面，应让页面内容贴合 App 业务，例如公告、客服、支付完成、文档预览、账号授权页；
9. 如官方服务器实现需要 mock 敏感数据，在服务器端进行存储。
10. 服务器目录中必须包含简短 `README.md`，说明监听方式、需要映射的官方域名、样本触发 URL 和启动命令。

推荐目录结构：

```text
server\
  <SampleId>\
    README.md
    package.json / requirements.txt / server.py / app.js
    public\
      <static files>
```

官方服务器实现与漏洞样本的关系必须写入 `vulnerability_description` 或索引扩展字段中。若某个样本不需要官方服务器，应在最终回复中说明“官方服务器：不需要”，并且 `benchmark_samples.json` 中对应字段可记录为 `null`。

示例：

```text
重定向漏洞样本中，在 $SampleServerRoot 下实现官方帮助中心路由：
https://support.example.com/help/redirect?target=<url>

用户会将 support.example.com 通过本机 DNS 映射到本地服务器。App 与 exp 仍访问 support.example.com，不直接访问 127.0.0.1。服务器只处理 /help/redirect 这一条业务路由，并根据 target 返回 302，用于闭环官方域名重定向场景。
```


---

## 8. 测试敏感数据要求

所有用于样本触发安全后果的测试敏感数据，必须统一存放在：

```
app/src/main/assets/benchmark_mock_data.json
```

代码中不得直接硬编码 token、cookie、authorization header、支付凭证、私有文件内容等敏感值。

虽然文件名固定使用 `benchmark_mock_data.json`，但代码中的类名、方法名、变量名不应直接使用 `mock` 这类明显测试化命名，应使用更贴近真实业务的命名方式。

推荐命名示例：

```
AccountSessionStore.getUserToken(context)
AccountSessionStore.getAuthorizationHeader(context)
PaymentCredentialStore.getPaymentToken(context)
WebSessionStore.getCookie(context)
PrivateDocumentStore.getPrivateFileContent(context)
```

也可以根据 App 原有业务选择更贴近项目语义的名称，例如：

```
UserSessionManager
AuthCredentialProvider
PaymentConfigRepository
OfflineContentRepository
SecurePreferenceStore
```

`benchmark_mock_data.json` 示例：

```
{
  "userToken": "benchmark-user-token",
  "authHeader": "Bearer benchmark-auth-header",
  "paymentToken": "benchmark-payment-token",
  "privateFileContent": "benchmark-private-file-content",
  "cookie": "sessionid=benchmark-session-cookie"
}
```

读取接口应放在符合项目结构的位置，并尽量复用项目已有的 JSON、assets、配置读取或 repository 代码风格。

要求：

```
- 敏感数据只能从 assets/benchmark_mock_data.json 读取；
- 不得在业务代码中硬编码敏感值；
- 对外暴露的类名、方法名、变量名应贴近真实业务；
- 避免出现 BenchmarkMockData、getMockToken、mockCookie 等明显测试化命名；
- 漏洞代码中的敏感能力必须造成明确安全后果。
```

---

## 9. 样本丰富化要求

同一类漏洞的多个样本应尽量多样化。

### 9.1 漏洞技术形态

例如 `Insufficient URL Source Validation` 可使用：

- `contains`；
- `endsWith`；
- `startsWith`；
- userinfo 绕过；
- 子域名误判；
- scheme 混淆；
- 只校验初始 URL。

### 9.2 业务能力

例如 Bridge 或回调中的敏感能力可变化：

- getUserToken；
- getPaymentToken；
- readPrivateFile；
- deleteLocalFile；
- exportOrderHistory；
- openInternalBillActivity；
- attachAuthorizationHeader。

### 9.3 触发场景

例如 `Cookie Leakage` 可出现在：

- `loadUrl(url, headers)`；
- 下载回调中附加 cookie/header；
- `shouldInterceptRequest` 转发请求；
- 重定向后继续附带认证信息；
- 日志中输出 cookie/header。

### 9.4 代码结构

可以适当加入漏洞无关代码，使样本更贴近真实项目，例如：

- bridge 中同时包含敏感 API 和普通 API；
- WebViewClient 中同时包含安全处理和不安全分支；
- 下载回调中同时处理可信下载和不可信下载；
- 权限回调中同时处理可信 origin 和默认放行分支。

---

## 10. 编译验证

在当前样本 worktree 中执行用户指定的 Windows 构建命令。App 编译验证与服务器启动验证是两个独立步骤：

```powershell
cd $SampleWorktree
Invoke-Expression $BuildCmd
```

如果编译失败：

1. 阅读错误；
2. 修复 import、Manifest、资源、API 兼容、Java/Kotlin 语法；
3. 重新编译；
4. 未通过编译不得提交样本分支。

如果当前样本包含官方服务器实现，还必须在 `$SampleServerRoot` 中执行一次最小启动或语法校验，例如查看 `README.md` 中的启动命令、安装依赖声明是否完整，并确认服务器路由与样本描述一致。服务器验证失败时不得声称样本闭环完成。

---

## 11. 分支提交与校验

编译通过后，在当前样本 worktree 中提交当前漏洞分支：

```powershell
cd $SampleWorktree

git status --short
git add .
git commit -m "Add vulnerable sample: <漏洞编号 + 漏洞名>"
```

提交后校验分支可复现：

```powershell
cd $SampleWorktree
git status --short
Invoke-Expression $BuildCmd
```

校验通过后，不要将主源码目录 checkout 到 `BASE_COMMIT`，因为主 worktree 不参与漏洞样本开发。最终只需要确认：

```powershell
cd $MainWorktree
git status --short

git worktree list
```

最终状态要求：

1. `$MainWorktree` 保持干净，且未包含漏洞样本修改；
2. `$SampleWorktree` 位于 `vuln/<id>` 分支；
3. `$SampleWorktree` 工作区干净；
4. `benchmark_samples.json` 已更新；
5. 如样本需要官方服务器，`$SampleServerRoot` 已包含对应实现和 `README.md`；如不需要，索引和最终回复已明确说明；
6. `git worktree list` 能看到主 worktree 和当前样本 worktree 的对应关系。



## 13. EXP 编写确认与设计

当前漏洞样本任务完成后，必须向用户确认是否需要继续编写 exp。

### 13.1 确认时机

在完成以下事项之后再询问用户是否编写 exp：

1. 漏洞样本已编译通过；
2. `vuln/<漏洞ID>` 分支已按要求提交；
3. `benchmark_samples.json` 已更新；
4. 主源码 worktree 与样本 worktree 状态已校验；
5. 最终完成信息已准备输出。

询问方式应简短明确，例如：

```text
是否需要继续为该漏洞样本编写 exp？
```

不得在用户确认前擅自编写 exp。

### 13.2 用户确认后的 EXP 设计要求

如果用户确认需要编写 exp，必须参考 exp 模板目录中的 exp 样例进行设计，其中模板目录位于：

```powershell
$ExpDir/template
```

要求：

1. 先查看 exp 模板目录下已有 exp 样例的结构、命名、触发方式、参数组织方式和输出形式；
2. 根据当前漏洞样本的业务场景、外部可达路径和漏洞后果设计 exp；
3. 可能需要复用 template 中的某些结构，也可能不需要，必须以当前漏洞触发链路是否需要为准；
4. exp 应能清晰触发当前漏洞样本的安全后果；
5. exp 文件命名和目录组织应尽量与 template 样例风格一致；
6. 不得为了编写 exp 修改已提交的漏洞样本代码，除非用户明确要求；
7. 需要输出一份简要的使用说明文件readme.md。
8. exp 编写完成后，只需保证文件落盘即可。

### 13.3 EXP 输出目录

exp 输出的目录位于：

```powershell
$Expdir/$AppName/$SampleId
```

### 13.4 EXP 不纳入 Git 管理

exp 不使用 git 管理，写完即可。

要求：

1. 不需要创建 exp 分支；
2. 不需要提交 exp 文件；
3. 不需要把 exp 文件加入 `vuln/<漏洞ID>` 或 `fix/<漏洞ID>` 分支；
4. 不需要更新 `benchmark_samples.json`，除非用户明确要求记录 exp 路径；
5. 编写完成后只报告 exp 文件路径和使用方式。

### 13.5 EXP 完成后的回复格式

```text
EXP 已完成。

参考样例：
<applist\exp\template 下参考的样例或结构>

EXP 文件：
- <exp file path>

使用方式：
<如何运行或触发 exp>

说明：
EXP 未纳入 git 管理，未提交到任何漏洞或修复分支。
```


## 12. benchmark_samples.json

### 12.1 文件位置

```text
benchmark-root\samples\app_name\benchmark_samples.json
```

### 12.2 记录格式

```json
{
  "app": "app_name",
  "base_commit": "abc123",
  "samples": [
    {
      "id": "2.3.2_Insecure_System_Scheme_Handling",
      "category": "2.3.2 Insecure System Scheme Handling",
      "branches": {
        "vuln": "vuln/2.3.2_Insecure_System_Scheme_Handling",
        "fix": "fix/2.3.2_Insecure_System_Scheme_Handling"
      },
      "worktrees": {
        "vuln": "apps/app_name/samples/2.3.2_Insecure_System_Scheme_Handling",
        "fix": "apps/app_name/samples/2.3.2_Insecure_System_Scheme_Handling"
      },
      "build_command": ".\\gradlew.bat assembleDebug",
      "status": {
        "vuln": "compiled",
        "fix": "pending"
      },
      "vulnerability_description": "通过帮助中心 deeplink 传入外部可控 URL 并进入 WebView，不安全处理 tel scheme，恶意页面可触发自动拨号。",
      "mock_data": "assets/benchmark_mock_data.json",
      "official_server": {
        "path": "apps/app_name/server/2.3.2_Insecure_System_Scheme_Handling",
        "hosts": ["support.example.com"],
        "routes": ["/help/redirect"],
        "status": "implemented"
      }
    }
  ]
}
```

### 12.3 字段要求

3. `vulnerability_description` 用一句简短描述同时说明：
   - 漏洞嵌入的业务场景；
   - 外部可控 URL 的可达路径；
   - 明确安全后果；
4. 更新索引时不得删除旧样本记录；
5. `worktrees.vuln` 必须记录相对于 `$BenchmarkRoot` 的样本 worktree 路径；
6. `worktrees.fix` 不得指向新的 fix worktree；当前未生成 fix 样本时可记录为 `null`，生成 fix 后应记录为与 `worktrees.vuln` 相同的样本 worktree 路径；
7. `official_server` 用于记录当前样本是否需要官方服务器实现；不需要时记录为 `null`；需要时必须包含相对 `$BenchmarkRoot` 的 `path`、涉及的官方域名 `hosts`、路由 `routes` 和实现状态 `status`。

---

## 14. 最终回复格式

```text
已完成：<编号 + 漏洞名>

漏洞描述：
<一句话说明业务场景、外部可控 URL 可达路径，以及造成的明确安全影响>

修改文件：
- <file1>
- <file2>

编译结果：
<构建命令> 通过

分支：
vuln/<漏洞ID_漏洞英文名>

样本 worktree：
<SampleWorktree>

索引：
<IndexDir>\benchmark_samples.json

官方服务器：
<不需要 / $SampleServerRoot，包含启动方式和需要映射的官方域名>

复现：
cd <SampleWorktree>
git status --short
<构建命令>

当前状态：
主 worktree 保持干净；样本 worktree 位于 vuln/<漏洞ID_漏洞英文名> 分支，工作区干净；如存在官方服务器目录，其文件已落在对应 $SampleServerRoot。

EXP：
是否需要继续为该漏洞样本编写 exp？
```


## 15. 失败回复格式

```text
样本未完成。

失败阶段：
<基线确认 / 业务理解 / 可达性判断 / 可达路径补充 / 官方服务器实现 / 编写 / 编译 / 分支提交 / 索引更新>

原因：
<关键原因>

已做修改：
<文件列表>

建议：
<下一步修复方式>
```

不得在失败时声称样本已完成。

---

## 16. 检查清单

最终输出前必须确认：

- [ ] 使用了用户提供的漏洞说明文档作为分类依据；
- [ ] 未修改漏洞分类说明；
- [ ] 只实现一个最小分类；
- [ ] 已在写代码前向用户报告方案并获得确认；
- [ ] 已从 BASE_COMMIT 创建或重置 `vuln/<id>` 分支，并挂载到独立样本 worktree 后再修改；
- [ ] 已理解 WebView 业务逻辑；
- [ ] 已判断是否存在 deeplink / intent / exported 组件等外部可达 URL 加载路径；
- [ ] 如已有外部可达路径，已优先沿用原代码路径；
- [ ] 如没有外部可达路径，已补充一条贴近业务且尽量复用源代码的可达路径；
- [ ] 如样本需要官方域名、重定向、回调或官方页面，已在服务器目录下创建 `$SampleServerRoot` 并补充本地官方服务器实现；
- [ ] 官方服务器实现只模拟官方业务，不修改 DNS/hosts，不访问真实官方服务器，不实现攻击者服务器；
- [ ] 官方服务器目录包含 README，说明启动命令、官方域名映射和触发 URL；
- [ ] 新增代码贴合原业务；
- [ ] mock 敏感数据在 assets 中；
- [ ] mock 数据通过统一接口读取；
- [ ] 漏洞造成明确安全后果；
- [ ] `vulnerability_description` 已简短说明业务场景、可达路径和漏洞后果；
- [ ] 样本内容不单一；
- [ ] 可包含适量无关真实业务代码；
- [ ] Windows 构建命令已在样本 worktree 中通过；
- [ ] 已在样本 worktree 中提交 `vuln/<id>` 分支；
- [ ] benchmark_samples.json 已记录分支、worktree 路径、状态、漏洞描述和 official_server 字段；
- [ ] 主 worktree 保持干净且未被漏洞样本污染；
- [ ] 样本 worktree 位于当前阶段对应分支且工作区干净。
- [ ] 已在漏洞样本任务完成后询问用户是否需要继续编写 exp。
- [ ] 如用户确认编写 exp，已参考 `applist\exp\template` 下的 exp 样例进行设计。
- [ ] exp 未使用 git 管理，未创建分支、未提交、未纳入样本索引，除非用户明确要求。
- [ ] 如生成 fix 样本，已确认 `fix/<id>` 从对应 `vuln/<id>` 创建，并复用同一个样本 worktree，未额外创建 fix worktree。
