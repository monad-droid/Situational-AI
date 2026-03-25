import HealthKit
import SwiftUI

@MainActor
class HealthKitManager: ObservableObject {
    private let store = HKHealthStore()
    private var anchor: HKQueryAnchor?

    @Published var latestWeight: Double?
    @Published var isAuthorized = false

    private let anchorKey = "healthkit_weight_anchor"

    init() {
        // Restore persisted anchor
        if let data = UserDefaults.standard.data(forKey: anchorKey) {
            anchor = try? NSKeyedUnarchiver.unarchivedObject(ofClass: HKQueryAnchor.self, from: data)
        }
    }

    // MARK: - Authorization

    func requestAuthorization() async {
        guard HKHealthStore.isHealthDataAvailable() else { return }

        let types: Set<HKSampleType> = [
            HKQuantityType(.bodyMass)
        ]

        do {
            try await store.requestAuthorization(toShare: [], read: types)
            isAuthorized = true
            startBackgroundDelivery()
        } catch {
            print("HealthKit authorization failed: \(error)")
        }
    }

    // MARK: - Background Delivery

    /// Register for background delivery — iOS wakes the app when new samples arrive.
    /// IMPORTANT: Background delivery is throttled by iOS. For bodyMass, expect
    /// hourly wake-ups at best. Do NOT promise real-time notifications.
    func startBackgroundDelivery() {
        let weightType = HKQuantityType(.bodyMass)

        store.enableBackgroundDelivery(for: weightType, frequency: .immediate) { success, error in
            if let error = error {
                print("Background delivery setup failed: \(error)")
            }
        }

        // Set up observer query — triggers on new data
        let observerQuery = HKObserverQuery(sampleType: weightType, predicate: nil) { [weak self] _, completionHandler, error in
            guard error == nil else {
                completionHandler()
                return
            }

            Task {
                await self?.fetchNewSamples()
                // CRITICAL: Always call the completion handler or iOS won't deliver future updates
                completionHandler()
            }
        }

        store.execute(observerQuery)
    }

    // MARK: - Anchored Object Query

    /// Fetch only NEW samples since the last sync using an anchor.
    /// This handles edits, deletions, and avoids reprocessing old data.
    func fetchNewSamples() async {
        let weightType = HKQuantityType(.bodyMass)

        await withCheckedContinuation { continuation in
            let query = HKAnchoredObjectQuery(
                type: weightType,
                predicate: nil,
                anchor: anchor,
                limit: HKObjectQueryNoLimit
            ) { [weak self] _, addedSamples, _, newAnchor, error in
                guard let self = self, error == nil else {
                    continuation.resume()
                    return
                }

                if let newAnchor = newAnchor {
                    self.anchor = newAnchor
                    // Persist anchor
                    if let data = try? NSKeyedArchiver.archivedData(withRootObject: newAnchor, requiringSecureCoding: true) {
                        UserDefaults.standard.set(data, forKey: self.anchorKey)
                    }
                }

                guard let samples = addedSamples as? [HKQuantitySample], !samples.isEmpty else {
                    continuation.resume()
                    return
                }

                // Convert to API format and send to backend
                let sampleInputs = samples.map { sample in
                    SampleInput(
                        metricType: "bodyMass",
                        value: sample.quantity.doubleValue(for: .pound()),
                        unit: "lb",
                        recordedAt: sample.endDate,
                        source: "healthkit"
                    )
                }

                // Update latest weight for UI
                if let latest = samples.sorted(by: { $0.endDate > $1.endDate }).first {
                    Task { @MainActor in
                        self.latestWeight = latest.quantity.doubleValue(for: .pound())
                    }
                }

                // Send to backend — backend handles dedup, threshold eval, nudges
                Task {
                    do {
                        _ = try await APIClient.shared.sendSamples(sampleInputs)
                    } catch {
                        print("Failed to send samples to backend: \(error)")
                    }
                    continuation.resume()
                }
            }

            store.execute(query)
        }
    }

    // MARK: - Manual Fetch (for UI)

    func fetchLatestWeight() async {
        let weightType = HKQuantityType(.bodyMass)
        let sort = NSSortDescriptor(key: HKSampleSortIdentifierEndDate, ascending: false)
        let query = HKSampleQuery(sampleType: weightType, predicate: nil, limit: 1, sortDescriptors: [sort]) { [weak self] _, results, _ in
            guard let sample = results?.first as? HKQuantitySample else { return }
            Task { @MainActor in
                self?.latestWeight = sample.quantity.doubleValue(for: .pound())
            }
        }
        store.execute(query)
    }
}
