import SwiftUI

struct CoachChatView: View {
    @State private var messages: [ChatBubble] = []
    @State private var inputText = ""
    @State private var sessionId: String?
    @State private var isLoading = false
    @State private var messagesRemaining: Int?
    @FocusState private var isInputFocused: Bool

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Messages
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            if messages.isEmpty {
                                EmptyChatPlaceholder()
                            }

                            ForEach(messages) { message in
                                ChatBubbleView(bubble: message)
                                    .id(message.id)
                            }

                            if isLoading {
                                HStack {
                                    TypingIndicator()
                                    Spacer()
                                }
                                .padding(.horizontal)
                                .id("loading")
                            }
                        }
                        .padding()
                    }
                    .onChange(of: messages.count) { _, _ in
                        withAnimation {
                            proxy.scrollTo(messages.last?.id ?? "loading", anchor: .bottom)
                        }
                    }
                }

                Divider()

                // Input bar
                HStack(spacing: 12) {
                    TextField("Talk back to your coach...", text: $inputText, axis: .vertical)
                        .textFieldStyle(.plain)
                        .lineLimit(1...4)
                        .focused($isInputFocused)

                    Button {
                        Task { await sendMessage() }
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.title2)
                            .foregroundColor(inputText.isEmpty ? .gray : .red)
                    }
                    .disabled(inputText.isEmpty || isLoading)
                }
                .padding()
                .background(Color(.systemBackground))

                if let remaining = messagesRemaining {
                    Text("\(remaining) messages remaining today")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                        .padding(.bottom, 4)
                }
            }
            .navigationTitle("Coach")
        }
    }

    func sendMessage() async {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        let userBubble = ChatBubble(role: .user, content: text)
        messages.append(userBubble)
        inputText = ""
        isLoading = true

        do {
            let response = try await APIClient.shared.sendChatMessage(text, sessionId: sessionId)
            let coachBubble = ChatBubble(role: .coach, content: response.response)
            messages.append(coachBubble)
            sessionId = response.sessionId
            messagesRemaining = response.messagesRemainingToday
        } catch APIError.rateLimited {
            let errorBubble = ChatBubble(role: .system, content: "Daily chat limit reached. The coach will keep nudging you via notifications. Come back tomorrow.")
            messages.append(errorBubble)
        } catch {
            let errorBubble = ChatBubble(role: .system, content: "Connection error. Try again.")
            messages.append(errorBubble)
        }

        isLoading = false
    }
}

// MARK: - Chat Models

struct ChatBubble: Identifiable {
    let id = UUID()
    let role: ChatRole
    let content: String
    let timestamp = Date()

    enum ChatRole {
        case user, coach, system
    }
}

// MARK: - Subviews

struct ChatBubbleView: View {
    let bubble: ChatBubble

    var body: some View {
        HStack {
            if bubble.role == .user { Spacer() }

            VStack(alignment: bubble.role == .user ? .trailing : .leading, spacing: 4) {
                if bubble.role == .coach {
                    Text("Coach")
                        .font(.caption2)
                        .foregroundColor(.red)
                        .bold()
                }

                Text(bubble.content)
                    .padding(12)
                    .background(backgroundColor)
                    .foregroundColor(foregroundColor)
                    .cornerRadius(16)
            }
            .frame(maxWidth: 280, alignment: bubble.role == .user ? .trailing : .leading)

            if bubble.role != .user { Spacer() }
        }
    }

    var backgroundColor: Color {
        switch bubble.role {
        case .user: return .red
        case .coach: return Color(.systemGray5)
        case .system: return Color(.systemGray6)
        }
    }

    var foregroundColor: Color {
        bubble.role == .user ? .white : .primary
    }
}

struct EmptyChatPlaceholder: View {
    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "bubble.left.and.bubble.right")
                .font(.system(size: 40))
                .foregroundColor(.secondary)

            Text("Talk to your coach")
                .font(.headline)

            Text("Ask about meal plans, workout ideas, or just vent. Your coach will keep it real.")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(.top, 60)
    }
}

struct TypingIndicator: View {
    @State private var dots = 0

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3) { i in
                Circle()
                    .fill(Color.secondary)
                    .frame(width: 8, height: 8)
                    .opacity(dots == i ? 1 : 0.3)
            }
        }
        .padding(12)
        .background(Color(.systemGray5))
        .cornerRadius(16)
        .onAppear {
            Timer.scheduledTimer(withTimeInterval: 0.4, repeats: true) { _ in
                dots = (dots + 1) % 3
            }
        }
    }
}
