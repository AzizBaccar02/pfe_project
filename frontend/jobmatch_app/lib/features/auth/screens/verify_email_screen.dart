import 'package:flutter/material.dart';
import '../../../widgets/app_button.dart';
import '../../../widgets/otp_input.dart';
import '../services/auth_service.dart';
import 'login_screen.dart';

class VerifyEmailScreen extends StatefulWidget {
  final String email;
  const VerifyEmailScreen({super.key, required this.email});

  @override
  State<VerifyEmailScreen> createState() => _VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends State<VerifyEmailScreen> {
  String code = "";
  bool loading = false;
  bool resendLoading = false;

  Future<void> onVerify() async {
    if (code.length != 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Enter the 6-digit code.")),
      );
      return;
    }

    setState(() => loading = true);
    try {
      await AuthService.verifyEmail(email: widget.email, code: code);

      if (!mounted) return;

      // Verified => backend returns tokens => go to Login or Home
      // You can navigate to Home later. For now go to Login.
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (_) => false,
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> onResend() async {
    setState(() => resendLoading = true);
    try {
      await AuthService.resendCode(email: widget.email);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Code resent. Check your email/console.")),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
    } finally {
      if (mounted) setState(() => resendLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: Colors.black,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 22),
          child: Column(
            children: [
              const SizedBox(height: 18),

              const Text(
                "Email verification",
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF2D2D2D),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                "Enter your OTP code",
                style: TextStyle(fontSize: 14, color: Color(0xFF9E9E9E)),
              ),
              const SizedBox(height: 10),
              Text(
                widget.email,
                style: const TextStyle(fontSize: 13, color: Color(0xFF6E6E6E)),
              ),

              const SizedBox(height: 22),

              OtpInput(
                length: 6,
                onChanged: (v) => setState(() => code = v),
              ),

              const SizedBox(height: 18),

              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text(
                    "Didn't receive code? ",
                    style: TextStyle(color: Color(0xFF9E9E9E)),
                  ),
                  GestureDetector(
                    onTap: resendLoading ? null : onResend,
                    child: Text(
                      resendLoading ? "Resending..." : "Resend again",
                      style: const TextStyle(
                        color: Color(0xFF0A8F5A),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),

              const Spacer(),

              AppButton(
                text: "Verify",
                loading: loading,
                onPressed: onVerify,
              ),

              const SizedBox(height: 18),
            ],
          ),
        ),
      ),
    );
  }
}