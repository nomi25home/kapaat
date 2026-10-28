import SwiftUI
import WebKit

struct WebView: NSViewRepresentable {
    let url: URL

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        // Allow reading files from the local server (same-origin fine; no file:// needed)
        config.defaultWebpagePreferences.allowsContentJavaScript = true

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.allowsMagnification = true
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        // Only reload when the URL actually changes (e.g. port switched)
        if webView.url?.host != url.host || webView.url?.port != url.port {
            webView.load(URLRequest(url: url))
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    // MARK: - Coordinator

    final class Coordinator: NSObject, WKNavigationDelegate {
        func webView(_ webView: WKWebView,
                     decidePolicyFor navigationAction: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            // Open external links in the default browser, not inside the webview
            guard let url = navigationAction.request.url else {
                decisionHandler(.allow); return
            }
            if url.host == "127.0.0.1" || url.host == "localhost" {
                decisionHandler(.allow)
            } else {
                NSWorkspace.shared.open(url)
                decisionHandler(.cancel)
            }
        }
    }
}
