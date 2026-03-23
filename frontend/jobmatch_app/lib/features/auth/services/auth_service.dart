import '../../../core/api/api_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../core/storage/token_storage.dart';

class AuthService {
  static Future<void> signup({
    required String email,
    required String username,
    required String password,
    required String role,
  }) async {
    await ApiClient.post(
      Endpoints.signup,
      body: {
        "email": email,
        "username": username,
        "password": password,
        "role": role,
      },
    );
  }

  static Future<void> verifyEmail({
    required String email,
    required String code,
  }) async {
    final res = await ApiClient.post(
      Endpoints.verifyEmail,
      body: {"email": email, "code": code},
    );

    final tokens = res["tokens"];
    await TokenStorage.saveTokens(
      access: tokens["access"],
      refresh: tokens["refresh"],
    );
  }

  static Future<void> resendCode({required String email}) async {
    await ApiClient.post(Endpoints.resendCode, body: {"email": email});
  }

  static Future<void> login({
    required String email,
    required String password,
  }) async {
    final res = await ApiClient.post(
      Endpoints.login,
      body: {"email": email, "password": password}, 
    );

    await TokenStorage.saveTokens(
      access: res["access"],
      refresh: res["refresh"],
    );
  }

  static Future<void> forgotPassword({required String email}) async {
  await ApiClient.post(Endpoints.forgotPassword, body: {"email": email});
}

static Future<void> resetPassword({
  required String email,
  required String code,
  required String newPassword,
}) async {
  await ApiClient.post(
    Endpoints.resetPassword,
    body: {"email": email, "code": code, "new_password": newPassword},
  );
}

  static Future<void> logout() async {
    final refresh = await TokenStorage.getRefresh();

    // If I have no refresh, just clear local
    if (refresh == null) {
      await TokenStorage.clear();
      return;
    }

    // Call backend logout (blacklist refresh)
    await ApiClient.post(
      Endpoints.logout,
      body: {"refresh": refresh},
      headers: {
        "Authorization": "Bearer ${await TokenStorage.getAccess() ?? ""}",
      },
    );

    // Clear local tokens
    await TokenStorage.clear();
  }
}