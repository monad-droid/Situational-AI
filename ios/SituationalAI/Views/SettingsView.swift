import SwiftUI

struct SettingsView: View {
    @Environment(AuthManager.self) var authManager
    @Environment(HealthKitManager.self) var healthKitManager

    @State private var quietHoursEnabled = true
    @State private var quietStart = DateComponents(hour: 22, minute: 0)
    @State private var quietEnd = DateComponents(hour: 7, minute: 0)
    @State private var personas: [CoachPersona] = []
    @State private var selectedPersonaId: String = "tough_love"

    var body: some View {
        NavigationStack {
            List {
                Section("Coach Persona") {
                    ForEach(personas) { persona in
                        Button {
                            selectedPersonaId = persona.id
                            Task { await selectPersona(persona.id) }
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(persona.name)
                                        .font(.headline)
                                        .foregroundColor(.primary)
                                    Text(persona.description)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                    Text("\"\(persona.preview)\"")
                                        .font(.caption2)
                                        .foregroundColor(.secondary)
                                        .italic()
                                        .padding(.top, 2)
                                }
                                Spacer()
                                if selectedPersonaId == persona.id {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundColor(.red)
                                }
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }

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

                        Text("No push notifications during quiet hours.")
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
            .task {
                await loadPersonas()
            }
        }
    }

    func loadPersonas() async {
        do {
            personas = try await APIClient.shared.getCoachPersonas()
        } catch {
            print("Failed to load personas: \(error)")
        }
    }

    func selectPersona(_ id: String) async {
        do {
            try await APIClient.shared.updateCoachPersona(id)
        } catch {
            print("Failed to update persona: \(error)")
        }
    }
}
