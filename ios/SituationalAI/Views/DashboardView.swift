import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var healthKitManager: HealthKitManager
    @State private var thresholds: [ThresholdResponse] = []
    @State private var showSetup = false
    @State private var targetWeight = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    // Current weight card
                    if let weight = healthKitManager.latestWeight {
                        WeightCard(weight: weight, threshold: thresholds.first)
                    } else {
                        SetupCard(
                            title: "Connect Health Data",
                            subtitle: "We need HealthKit access to track your weight",
                            action: "Enable HealthKit"
                        ) {
                            Task {
                                await healthKitManager.requestAuthorization()
                                await healthKitManager.fetchLatestWeight()
                            }
                        }
                    }

                    // Threshold setup
                    if thresholds.isEmpty {
                        SetupCard(
                            title: "Set Your Threshold",
                            subtitle: "What weight triggers the coach?",
                            action: "Set Threshold"
                        ) {
                            showSetup = true
                        }
                    } else if let threshold = thresholds.first {
                        ThresholdStatusCard(threshold: threshold, currentWeight: healthKitManager.latestWeight)
                    }
                }
                .padding()
            }
            .navigationTitle("Dashboard")
            .task {
                await loadThresholds()
            }
            .sheet(isPresented: $showSetup) {
                ThresholdSetupSheet(targetWeight: $targetWeight) {
                    await createThreshold()
                }
            }
        }
    }

    func loadThresholds() async {
        do {
            thresholds = try await APIClient.shared.getThresholds()
        } catch {
            print("Failed to load thresholds: \(error)")
        }
    }

    func createThreshold() async {
        guard let value = Double(targetWeight) else { return }
        do {
            let threshold = try await APIClient.shared.createThreshold(
                metricType: "bodyMass",
                targetValue: value,
                direction: "above",
                unit: "lb"
            )
            thresholds = [threshold]
            showSetup = false
        } catch {
            print("Failed to create threshold: \(error)")
        }
    }
}

struct WeightCard: View {
    let weight: Double
    let threshold: ThresholdResponse?

    var isOverThreshold: Bool {
        guard let t = threshold else { return false }
        return weight >= t.targetValue
    }

    var body: some View {
        VStack(spacing: 8) {
            Text("Current Weight")
                .font(.subheadline)
                .foregroundColor(.secondary)

            Text("\(weight, specifier: "%.1f") lb")
                .font(.system(size: 48, weight: .bold, design: .rounded))
                .foregroundColor(isOverThreshold ? .red : .green)

            if let t = threshold {
                Text(isOverThreshold ? "Over threshold (\(t.targetValue, specifier: "%.0f") lb)" : "Under threshold")
                    .font(.caption)
                    .foregroundColor(isOverThreshold ? .red : .green)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(32)
        .background(Color(.systemGray6))
        .cornerRadius(20)
    }
}

struct ThresholdStatusCard: View {
    let threshold: ThresholdResponse
    let currentWeight: Double?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "target")
                    .foregroundColor(.red)
                Text("Threshold")
                    .font(.headline)
                Spacer()
                Text(threshold.isActive ? "Active" : "Inactive")
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(threshold.isActive ? Color.red.opacity(0.15) : Color.gray.opacity(0.15))
                    .cornerRadius(8)
            }

            HStack {
                Text("Coach activates above")
                Spacer()
                Text("\(threshold.targetValue, specifier: "%.0f") \(threshold.unit)")
                    .bold()
            }
            .font(.subheadline)
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(16)
    }
}

struct SetupCard: View {
    let title: String
    let subtitle: String
    let action: String
    let onTap: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text(title)
                .font(.headline)
            Text(subtitle)
                .font(.subheadline)
                .foregroundColor(.secondary)
            Button(action: onTap) {
                Text(action)
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.red)
                    .cornerRadius(12)
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(16)
    }
}

struct ThresholdSetupSheet: View {
    @Binding var targetWeight: String
    let onCreate: () async -> Void
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Text("What weight triggers the coach?")
                    .font(.title2)
                    .bold()

                Text("When you go above this number, the coaching starts. It won't stop until you're back under.")
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)

                TextField("170", text: $targetWeight)
                    .font(.system(size: 48, weight: .bold, design: .rounded))
                    .multilineTextAlignment(.center)
                    .keyboardType(.decimalPad)

                Text("pounds")
                    .foregroundColor(.secondary)

                Button {
                    Task {
                        await onCreate()
                        dismiss()
                    }
                } label: {
                    Text("Set Threshold")
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.red)
                        .cornerRadius(12)
                }
                .disabled(targetWeight.isEmpty)

                Spacer()
            }
            .padding()
            .navigationTitle("Set Threshold")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}
