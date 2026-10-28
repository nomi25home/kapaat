import SwiftUI

/// Shown when clicking the Kapaat menu-bar icon.
/// Renders the full web UI inside a fixed-size panel; below it a compact status footer.
struct MenuBarContentView: View {
    @EnvironmentObject private var server: ServerManager
    @State private var showWindow = false

    var body: some View {
        VStack(spacing: 0) {
            if server.status.isRunning {
                WebView(url: server.serverURL)
                    .frame(width: 900, height: 620)
            } else {
                splashView
                    .frame(width: 900, height: 620)
            }

            Divider()
            footer
        }
        .background(.background)
    }

    // MARK: - Sub-views

    private var splashView: some View {
        VStack(spacing: 16) {
            Image(systemName: "archivebox.fill")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text(server.status.label)
                .font(.headline)
                .foregroundStyle(.secondary)

            if case .failed = server.status {
                Button("Retry") { server.restart() }
                    .buttonStyle(.borderedProminent)
            } else if server.status == .starting {
                ProgressView()
                    .progressViewStyle(.circular)
                    .scaleEffect(0.7)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var footer: some View {
        HStack(spacing: 10) {
            Circle()
                .fill(statusColor)
                .frame(width: 8, height: 8)

            Text(server.status.label)
                .font(.caption)
                .foregroundStyle(.secondary)

            Spacer()

            if server.status.isRunning {
                Button {
                    NSWorkspace.shared.open(server.serverURL)
                } label: {
                    Label("Open in Browser", systemImage: "safari")
                        .font(.caption)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            }

            Button {
                NSApplication.shared.terminate(nil)
            } label: {
                Label("Quit", systemImage: "power")
                    .font(.caption)
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
    }

    private var statusColor: Color {
        switch server.status {
        case .running:  return .green
        case .starting: return .yellow
        case .stopped:  return .gray
        case .failed:   return .red
        }
    }
}
