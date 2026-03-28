import SwiftUI

struct SettingsView: View {
    @Environment(AuthManager.self) var authManager
    @Environment(HealthKitManager.self) var healthKitManager

    @State private var quietHoursEnabled = true
    @State private var quietStart = DateComponents(hour: 22, minute: 0)
    @State private var quietEnd = DateComponents(hour: 7, minute: 0)

    var body: some View {
        NavigationStack {
            List {
                Section("Health Data") {
                    HStack {
                        Label("HealthKit", systemImage: "heart.fill")
                        Spacer()
                        Text(healthKitManager.isAuthorized ? "Connected" : "Not Connected")
                            .foregroundColor(healthKitManager.isAuthorized ? .green : .secondary)
                    }

                    if !healthKitManager.isAuthorized {
                        Button("Connect HealthKit") {
                            Task { await healthKitManager.requestAuthorization() }
                        }
                    }
                }

                Section("Quiet Hours") {
                    Toggle("Quiet Hours", isOn: $quietHoursEnabled)

                    if quietHoursEnabled {
                        DatePicker(
                            "Start",
                            selection: Binding(
                                get: { Calendar.current.date(from: quietStart) ?? Date() },
                                set: { quietStart = Calendar.current.dateComponents([.hour, .minute], from: $0) }
                            ),
                            displayedComponents: .hourAndMinute
                        )

                        DatePicker(
                            "End",
                            selection: Binding(
                                get: { Calendar.current.date(from: quietEnd) ?? Date() },
                                set: { quietEnd = Calendar.current.dateComponents([.hour, .minute], from: $0) }
                            ),
                            displayedComponents: .hourAndMinute
                        )

                        Text("No push notifications during quiet hours. Queued nudges are delivered when quiet hours end — but only if you're still over threshold.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("0.1.0")
                            .foregroundColor(.secondary)
                    }

                    HStack {
                        Text("Company")
                        Spacer()
                        Text("CMD Loop Holdings LLC")
                            .foregroundColor(.secondary)
                    }
                }

                Section {
                    Button("Sign Out", role: .destructive) {
                        authManager.signOut()
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}
