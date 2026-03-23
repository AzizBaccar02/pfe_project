import 'package:flutter/material.dart';

import '../../../widgets/app_button.dart';
import 'login_screen.dart';
import 'signup_screen.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            children: [
              const Spacer(flex: 2),

              Image.asset(
                'assets/images/welcome.png',
                height: 280,
                fit: BoxFit.contain,
              ),

              const SizedBox(height: 28),

              const Text(
                'Welcome',
                style: TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF2D2D2D),
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                'Have a better sharing experience',
                style: TextStyle(
                  fontSize: 14,
                  color: Color(0xFF9E9E9E),
                ),
              ),

              const Spacer(flex: 3),

              AppButton(
                text: 'Create an account',
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) =>  SignupScreen()),
                  );
                },
              ),
              const SizedBox(height: 14),
              AppOutlineButton(
                text: 'Log In',
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) =>  LoginScreen()),
                  );
                },
              ),

              const SizedBox(height: 18),
            ],
          ),
        ),
      ),
    );
  }
}