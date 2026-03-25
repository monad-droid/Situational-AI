import Foundation

// MARK: - API Request/Response Models

struct AuthResponse: Codable {
    let accessToken: String
    let userId: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case userId = "user_id"
    }
}

struct ThresholdResponse: Codable, Identifiable {
    let id: String
    let metricType: String
    let targetValue: Double
    let direction: String
    let unit: String
    let isActive: Bool
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case metricType = "metric_type"
        case targetValue = "target_value"
        case direction
        case unit
        case isActive = "is_active"
        case createdAt = "created_at"
    }
}

struct ThresholdCreateRequest: Codable {
    let metricType: String
    let targetValue: Double
    let direction: String
    let unit: String

    enum CodingKeys: String, CodingKey {
        case metricType = "metric_type"
        case targetValue = "target_value"
        case direction
        case unit
    }
}

struct SampleInput: Codable {
    let metricType: String
    let value: Double
    let unit: String
    let recordedAt: Date
    let source: String

    enum CodingKeys: String, CodingKey {
        case metricType = "metric_type"
        case value
        case unit
        case recordedAt = "recorded_at"
        case source
    }
}

struct SamplesRequest: Codable {
    let samples: [SampleInput]
}

struct SamplesResponse: Codable {
    let ingested: Int
    let duplicatesSkipped: Int

    enum CodingKeys: String, CodingKey {
        case ingested
        case duplicatesSkipped = "duplicates_skipped"
    }
}

struct ChatRequest: Codable {
    let message: String
    let sessionId: String?

    enum CodingKeys: String, CodingKey {
        case message
        case sessionId = "session_id"
    }
}

struct ChatResponseModel: Codable {
    let response: String
    let sessionId: String
    let messagesRemainingToday: Int

    enum CodingKeys: String, CodingKey {
        case response
        case sessionId = "session_id"
        case messagesRemainingToday = "messages_remaining_today"
    }
}
