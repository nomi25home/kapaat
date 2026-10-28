import SwiftUI

@main
struct KapaatApp: App {
    @StateObject private var server = ServerManager()

    var body: some Scene {
        MenuBarExtra {
            MenuBarContentView()
                .environmentObject(server)
        } label: {
            Image(systemName: "archivebox.fill")
        }
        .menuBarExtraStyle(.window)
    }
}
