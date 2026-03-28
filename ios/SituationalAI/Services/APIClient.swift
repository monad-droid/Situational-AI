import Foundation

actor APIClient {
    static let shared = APIClient()

    #if DEBUG
    // Use your Mac's local IP so both simulator and real iPhone can reach the backend
    private let baseURL = "http://192.168.1.16:8000"
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

    func devLogin() async throws -> AuthResponse {
        let response: AuthResponse = try await post("/api/auth/dev", body: EmptyBody(), authenticated: false)
        self.accessToken = response.accessToken
        return response
    }

    func signInWithApple(identityToken: String, userIdentifier: String, email: String?, fullName: String?) async throws -> AuthResponse {
        let body = AppleSignInBody(
            identityToken: identityToken,
            userIdentifier: userIdentifier,
            email: email,
            fullName: fullName
        )
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
        let request = ChatRequestBody(message: message, sessionId: sessionId)
        return try await post("/api/chat", body: request)
    }

    // MARK: - Coach Personas

    func getCoachPersonas() async throws -> [CoachPersona] {
        let response: CoachPersonasResponse = try await get("/api/coach-personas")
        return response.personas
    }

    func updateCoachPersona(_ personaId: String) async throws {
        let body = UserSettingsBody(coachPersona: personaId, timezone: nil, quietHours: nil)
        let _: StatusResponse = try await post("/api/user/settings", body: body)
    }

    // MARK: - Push Token

    func updatePushToken(_ token: String) async throws {
        let body = PushTokenBody(pushToken: token)
        let _: StatusResponse = try await post("/api/push-token", body: body)
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

    private func post<B: Encodable, T: Decodable>(_ path: String, body: B, authenticated: Bool = true) async throws -> T {
        var request = URLRequest(url: URL(string: baseURL + path)!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if authenticated { addAuth(&request) }

        request.httpBody = try encoder.encode(body)

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

// MARK: - Request Body Types

private struct EmptyBody: Encodable {}
private struct StatusResponse: Decodable { let status: String }
private struct PushTokenBody: Encodable {
    let pushToken: String
    enum CodingKeys: String, CodingKey { case pushToken = "push_token" }
}
private struct AppleSignInBody: Encodable {
    let identityToken: String
    let userIdentifier: String
    let email: String?
    let fullName: String?
    enum CodingKeys: String, CodingKey {
        case identityToken = "identity_token"
        case userIdentifier = "user_identifier"
        case email
        case fullName = "full_name"
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
