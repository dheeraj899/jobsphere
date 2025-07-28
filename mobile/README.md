# JobSphere Mobile App

## Introduction
The JobSphere Mobile App is a Flutter-based cross-platform client for iOS and Android that provides a seamless job search and application experience. It integrates with the JobSphere backend APIs to deliver real-time data and functionality.

## Technical Stack
- Flutter 3.x & Dart 2.x
- HTTP package for REST API calls
- flutter_secure_storage for secure token management
- Provider (or Riverpod) for state management
- Shared Preferences for local persistence
- Geolocator for location-based features
- flutter_dotenv for environment configuration

## Prerequisites
- Flutter SDK installed (https://flutter.dev/docs/get-started/install)
- Xcode (for iOS) and Android Studio (for Android) installed
- A configured backend API URL
- Device emulator or physical device connected

## Features
- User authentication (login, registration, password reset)
- Profile creation and updates
- Job listings with search, filter, and map view
- Apply for jobs and save favorite jobs
- Real-time messaging and notifications
- Activity dashboard with analytics insights
- Offline caching for improved performance

## Steps to Start
1. Clone the repository:
   ```bash
   git clone <REPO_URL>
   cd jobsphere/mobile
   ```
2. Install Flutter dependencies:
   ```bash
   flutter pub get
   ```
3. Configure environment:
   - Copy `.env.example` to `.env` (if using flutter_dotenv)
   - Or create `lib/config.dart` with:
     ```dart
     const String API_BASE_URL = 'http://localhost:8000/api/v1/';
     ```
4. Run the app:
   - iOS Simulator: `flutter run`
   - Android Emulator: `flutter run`

## Backend API Access
- Base URL: `http://<BACKEND_HOST>/api/v1/`
- Authentication endpoints:
  - `POST /auth/register/`
  - `POST /auth/login/`
  - `POST /auth/password/reset/`
- Include header `Authorization: Bearer <ACCESS_TOKEN>` for protected endpoints
- Swagger UI: `http://<BACKEND_HOST>/swagger/`

## Environment Configuration
If using `flutter_dotenv`, create a `.env` file in the `mobile/` folder:
```
API_BASE_URL=http://localhost:8000/api/v1/
```

## Testing
- Unit tests:
  ```bash
  flutter test
  ```
- Integration tests (driver):
  ```bash
  flutter drive --target=test_driver/app.dart
  ```

---
Enjoy developing with JobSphere Mobile! 🚀
