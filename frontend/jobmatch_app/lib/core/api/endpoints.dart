class Endpoints {
  // Android emulator must use 10.0.2.2 to reach your PC localhost
  static const baseUrl = "http://10.0.2.2:8000";

  static const signup = "/api/users/signup/";
  static const verifyEmail = "/api/users/verify-email/";
  static const resendCode = "/api/users/resend-code/";
  static const login = "/api/auth/login/";
  static const forgotPassword = "/api/users/forgot-password/";
  static const resetPassword = "/api/users/reset-password/";
  static const logout = "/api/auth/logout/";
}