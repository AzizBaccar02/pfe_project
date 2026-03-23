import 'package:flutter/material.dart';

import '../../../widgets/app_button.dart';
import '../../../widgets/app_text_field.dart';
import '../../../widgets/otp_input.dart';
import '../services/auth_service.dart';
import 'login_screen.dart';

class ResetPasswordScreen extends StatefulWidget {
  final String email;
  const ResetPasswordScreen({super.key, required this.email});

  @override
  State<ResetPasswordScreen> createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends State<ResetPasswordScreen> {
  String code = "";
  final passCtrl = TextEditingController();
  bool loading = false;

  @override
  void dispose() {
    passCtrl.dispose();
    super.dispose();
  }

  Future<void> onReset() async {
    final newPassword = passCtrl.text;

    if (code.length != 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Enter the 6-digit code.")),
      );
      return;
    }

    if (newPassword.length < 8) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Password must be at least 8 characters.")),
      );
      return;
    }

    setState(() => loading = true);
    try {
      await AuthService.resetPassword(
        email: widget.email,
        code: code,
        newPassword: newPassword,
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Password updated. Please login.")),
      );

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
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 6),
              const Text(
                "Reset password",
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF2D2D2D),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                "Enter the code you received and choose a new password.",
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

              AppTextField(
                controller: passCtrl,
                label: "New Password",
                hint: "New Password",
                obscure: true,
              ),

              const Spacer(),

              AppButton(
                text: "Reset",
                loading: loading,
                onPressed: onReset,
              ),

              const SizedBox(height: 18),
            ],
          ),
        ),
      ),
    );
  }
}