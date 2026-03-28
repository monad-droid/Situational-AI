import Foundation

actor APIClient {
    static let shared = APIClient()

    #if DEBUG
    private let baseURL = "http://localhost:8000"
    #else
    private let baseURL = "https://api.situational-ai.app"
    #endif
    private var accessToken: String?

    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()

    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()

    func setAccessToken(_ token: String) {
        self.accessToken = token
    }

    // MARK: - Auth

    func signInWithApple(identityToken: String, userIdentifier: String, email: String?, fullName: String?) async throws -> AuthResponse {
        let body: [String: Any?] = [
            "identity_token": identityToken,
            "user_identifier": userIdentifier,
            "email": email,
            "full_name": fullName
        ]
        let response: AuthResponse = try await post("/api/auth/apple", body: body, authenticated: false)
        self.accessToken = response.accessToken
        return response
    }

    // MARK: - Samples

    func sendSamples(_ samples: [SampleInput]) async throws -> SamplesResponse {
        let request = SamplesRequest(samples: samples)
        return try await post("/api/samples", body: request)
    }

    // MARK: - Thresholds

    func getThresholds() async throws -> [ThresholdResponse] {
        return try await get("/api/thresholds")
    }

    func createThreshold(metricType: String, targetValue: Double, direction: String, unit: String) async throws -> ThresholdResponse {
        let request = ThresholdCreateRequest(
            metricType: metricType,
            targetValue: targetValue,
            direction: direction,
            unit: unit
        )
        return try await post("/api/thresholds", body: request)
    }

    // MARK: - Chat

    func sendChatMessage(_ message: String, sessionId: String? = nil) async throws -> ChatResponseModel {
        let request = ChatRequest(message: message, sessionId: sessionId)
        return try await post("/api/chat", body: request)
    }

    // MARK: - Push Token

    func updatePushToken(_ token: String) async throws {
        let _: [String: String] = try await post("/api/push-token", body: ["push_token": token])
    }

    // MARK: - HTTP Helpers

    private func get<T: Decodable>(_ path: String) async throws -> T {
        var request = URLRequest(url: URL(string: baseURL + path)!)
        request.httpMethod = "GET"
        addAuth(&request)

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response)
        return try decoder.decode(T.self, from: data)
    }

    private func post<T: Decodable>(_ path: String, body: Any, authenticated: Bool = true) async throws -> T {
        var request = URLRequest(url: URL(string: baseURL + path)!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if authenticated { addAuth(&request) }

        if let encodable = body as? Encodable {
            request.httpBody = try encoder.encode(AnyEncodable(encodable))
        } else if let dict = body as? [String: Any?] {
            request.httpBody = try JSONSerialization.data(withJSONObject: dict.compactMapValues { $0 })
        }

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response)
        return try decoder.decode(T.self, from: data)
    }

    private func addAuth(_ request: inout URLRequest) {
        if let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
    }

    private func validateResponse(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else { return }
        if http.statusCode == 429 {
            throw APIError.rateLimited
        }
        guard (200...299).contains(http.statusCode) else {
            throw APIError.httpError(http.statusCode)
        }
    }
}

enum APIError: LocalizedError {
    case httpError(Int)
    case rateLimited

    var errorDescription: String? {
        switch self {
        case .httpError(let code): return "Server error (\(code))"
        case .rateLimited: return "Daily chat limit reached. Try again tomorrow."
        }
    }
}

// Type-erased Encodable wrapper
private struct AnyEncodable: Encodable {
    private let _encode: (Encoder) throws -> Void

    init(_ wrapped: Encodable) {
        self._encode = { encoder in try wrapped.encode(to: encoder) }
    }

    func encode(to encoder: Encoder) throws {
        try _encode(encoder)
    }
}
