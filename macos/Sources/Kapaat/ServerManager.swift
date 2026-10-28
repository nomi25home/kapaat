import Foundation
import Security
import Combine

@MainActor
final class ServerManager: ObservableObject {
    enum Status: Equatable {
        case stopped, starting, running, failed(String)

        var label: String {
            switch self {
            case .stopped:          return "Stopped"
            case .starting:         return "Starting…"
            case .running:          return "Running"
            case .failed(let msg):  return "Error: \(msg)"
            }
        }

        var isRunning: Bool { self == .running }
    }

    @Published private(set) var status: Status = .stopped
    let port: Int = 8096
    var serverURL: URL { URL(string: "http://127.0.0.1:\(port)")! }

    private var process: Process?
    private var startTask: Task<Void, Never>?

    init() { start() }

    func start() {
        guard process == nil else { return }
        status = .starting

        startTask = Task {
            do {
                try await launchServer()
                await waitForServer()
            } catch {
                status = .failed(error.localizedDescription)
            }
        }
    }

    func restart() {
        stop()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { self.start() }
    }

    func stop() {
        startTask?.cancel()
        startTask = nil
        process?.terminate()
        process = nil
        status = .stopped
    }

    // MARK: - Private

    private func launchServer() throws {
        let appDir = try resolveAppDirectory()
        let python  = try resolvePython(in: appDir)

        let p = Process()
        p.executableURL = URL(fileURLWithPath: python)
        p.arguments = [
            "-m", "uvicorn", "app:app",
            "--host", "127.0.0.1",
            "--port", "\(port)",
            "--log-level", "warning",
        ]
        p.currentDirectoryURL = URL(fileURLWithPath: appDir)
        p.environment = buildEnvironment()

        p.terminationHandler = { [weak self] _ in
            DispatchQueue.main.async { self?.status = .stopped }
        }

        try p.run()
        self.process = p
    }

    private func waitForServer() async {
        let healthURL = serverURL.appendingPathComponent("login")
        for _ in 0..<60 {
            try? await Task.sleep(nanoseconds: 500_000_000)
            if Task.isCancelled { return }
            if (try? await URLSession.shared.data(from: healthURL)) != nil {
                status = .running
                return
            }
        }
        status = .failed("Server did not respond within 30 s")
    }

    // MARK: - Path resolution

    /// Search order: bundled Resources/kapaat → sibling of .app → ~/kapaat
    private func resolveAppDirectory() throws -> String {
        let candidates: [String] = [
            Bundle.main.resourceURL?.appendingPathComponent("kapaat").path,
            Bundle.main.bundleURL.deletingLastPathComponent()
                .appendingPathComponent("kapaat").path,
            FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent("kapaat").path,
        ].compactMap { $0 }

        for dir in candidates {
            if FileManager.default.fileExists(atPath: dir + "/app.py") {
                return dir
            }
        }
        throw AppError.appDirNotFound
    }

    /// Prefer .venv inside appDir, then Homebrew / system Python
    private func resolvePython(in appDir: String) throws -> String {
        let candidates = [
            appDir + "/.venv/bin/python3",
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]
        guard let found = candidates.first(where: {
            FileManager.default.isExecutableFile(atPath: $0)
        }) else {
            throw AppError.pythonNotFound
        }
        return found
    }

    private func buildEnvironment() -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        env["AUTH_SECRET_KEY"]  = persistentSecretKey()
        env["BASE_URL"]         = "http://127.0.0.1:\(port)"
        env["DB_PATH"]          = dataDirectory() + "/kapaat.db"
        env["PHOTOS_DIR"]       = dataDirectory() + "/photos"
        // suppress Python stdout buffering so logs reach Console.app
        env["PYTHONUNBUFFERED"] = "1"
        return env
    }

    private func dataDirectory() -> String {
        let appSupport = FileManager.default
            .urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let dir = appSupport.appendingPathComponent("Kapaat").path
        try? FileManager.default.createDirectory(atPath: dir,
            withIntermediateDirectories: true)
        return dir
    }

    /// Generates once, persists in UserDefaults (app sandbox keeps it private)
    private func persistentSecretKey() -> String {
        let key = "KapaatAuthSecretKey"
        if let existing = UserDefaults.standard.string(forKey: key) {
            return existing
        }
        var bytes = [UInt8](repeating: 0, count: 32)
        _ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        let secret = Data(bytes).base64EncodedString()
        UserDefaults.standard.set(secret, forKey: key)
        return secret
    }

    enum AppError: LocalizedError {
        case appDirNotFound
        case pythonNotFound

        var errorDescription: String? {
            switch self {
            case .appDirNotFound:
                return "Cannot find Kapaat app directory. Run setup.sh first."
            case .pythonNotFound:
                return "Python 3 not found. Install it with Homebrew: brew install python"
            }
        }
    }
}
