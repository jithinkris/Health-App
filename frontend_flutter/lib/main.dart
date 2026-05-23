import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:smart_health/theme.dart';
import 'package:smart_health/screens/welcome_screen.dart';
import 'package:smart_health/screens/dashboard_screen.dart';
import 'package:smart_health/services/notification_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await NotificationService.init();
  runApp(const SmartHealthApp());
}

class SmartHealthApp extends StatelessWidget {
  const SmartHealthApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // Dummy provider placeholder for now
        Provider<int>.value(value: 1),
      ],
      child: MaterialApp(
        title: 'Smart Health AI',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.lightTheme,
        home: const SplashScreen(),
      ),
    );
  }
}

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    // Wait for the system (network, rendering engine) to fully stabilize.
    // This fixes the emulator cold-start bug where API calls fail silently.
    await Future.delayed(const Duration(seconds: 2));

    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access');
    final isLoggedIn = token != null && token.isNotEmpty;

    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => isLoggedIn
              ? const DashboardScreen()
              : const WelcomeScreen(),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [AppTheme.bgSurface, AppTheme.primaryBlue.withOpacity(0.15)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.health_and_safety, size: 100, color: AppTheme.primaryBlue),
              const SizedBox(height: 24),
              Text(
                'Smart Health AI',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppTheme.primaryBlue,
                ),
              ),
              const SizedBox(height: 32),
              const CircularProgressIndicator(color: AppTheme.primaryBlue),
            ],
          ),
        ),
      ),
    );
  }
}
