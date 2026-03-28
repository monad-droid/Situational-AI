import AuthenticationServices
import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject var authManager: AuthManager

    var body: some View {
        VStack(spacing: 40) {
            Spacer()

            VStack(spacing: 16) {
                Text("Situational AI")
                    .font(.system(size: 36, weight: .black))

                Text("The coach that won't let you off the hook.")
                    .font(.title3)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }

            VStack(spacing: 12) {
                Feature(icon: "scalemass", title: "Set Your Threshold", subtitle: "Tell us the line you don't want to cross")
                Feature(icon: "bell.badge", title: "Get Coached", subtitle: "Real talk, not empty validation")
                Feature(icon: "target", title: "Hit Your Goal", subtitle: "The nagging stops when you're back on track")
            }
            .padding(.horizontal)

            Spacer()

            SignInWithAppleButton(.signIn) { request in
                request.requestedScopes = [.fullName, .email]
            } onCompletion: { result in
                Task {
                    await authManager.handleSignInWithApple(result: result)
                }
            }
            .signInWithAppleButtonStyle(.black)
            .frame(height: 55)
            .cornerRadius(12)
            .padding(.horizontal, 32)

            #if DEBUG
            Button {
                authManager.devLogin()
            } label: {
                Text("Dev Login (skip auth)")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .padding(.top, 8)
            #endif

            Text("No fluff. No excuses. Just results.")
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.bottom, 32)
        }
    }
}

struct Feature: View {
    let icon: String
    let title: String
    let subtitle: String

    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.red)
                .frame(width: 40)

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline)
                Text(subtitle)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding(.vertical, 8)
    }
}
