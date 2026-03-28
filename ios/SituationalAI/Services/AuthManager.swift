import AuthenticationServices
import SwiftUI

@MainActor
@Observable
class AuthManager {
    var isAuthenticated = false
    var userId: String?

    private let tokenKey = "access_token"
    private let userIdKey = "user_id"

    init() {
        if let token = UserDefaults.standard.string(forKey: tokenKey) {
            Task {
                await APIClient.shared.setAccessToken(token)
            }
            self.userId = UserDefaults.standard.string(forKey: userIdKey)
            self.isAuthenticated = true
        }
    }

    func handleSignInWithApple(result: Result<ASAuthorization, Error>) async {
        switch result {
        case .success(let authorization):
            guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                  let identityTokenData = credential.identityToken,
                  let identityToken = String(data: identityTokenData, encoding: .utf8) else {
                return
            }

            let email = credential.email
            let fullName = [credential.fullName?.givenName, credential.fullName?.familyName]
                .compactMap { $0 }
                .joined(separator: " ")

            do {
                let response = try await APIClient.shared.signInWithApple(
                    identityToken: identityToken,
                    userIdentifier: credential.user,
                    email: email,
                    fullName: fullName.isEmpty ? nil : fullName
                )

                UserDefaults.standard.set(response.accessToken, forKey: tokenKey)
                UserDefaults.standard.set(response.userId, forKey: userIdKey)

                self.userId = response.userId
                self.isAuthenticated = true
            } catch {
                print("Sign in failed: \(error)")
            }

        case .failure(let error):
            print("Apple Sign In error: \(error)")
        }
    }

    #if DEBUG
    func devLogin() {
        self.userId = "dev-user"
        self.isAuthenticated = true
    }
    #endif

    func signOut() {
        UserDefaults.standard.removeObject(forKey: tokenKey)
        UserDefaults.standard.removeObject(forKey: userIdKey)
        isAuthenticated = false
        userId = nil
    }
}
