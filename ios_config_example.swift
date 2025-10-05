// iOS Configuration Example
// Add this to your iOS project to handle different environments

import Foundation

struct APIConfig {
    static let shared = APIConfig()
    
    private init() {}
    
    var baseURL: String {
        #if targetEnvironment(simulator)
        // Use localhost for iOS Simulator
        return "http://localhost:8000"
        #else
        // Use your Mac's IP for physical devices
        // Update this IP when your network changes
        return "http://192.168.1.138:8000"
        #endif
    }
    
    var websocketURL: String {
        return baseURL.replacingOccurrences(of: "http://", with: "ws://")
    }
}

// Usage in your iOS app:
// let apiURL = APIConfig.shared.baseURL
// let wsURL = APIConfig.shared.websocketURL

