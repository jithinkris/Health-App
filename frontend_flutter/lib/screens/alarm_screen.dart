import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:smart_health/services/notification_service.dart';

class AlarmScreen extends StatefulWidget {
  final String payload;

  const AlarmScreen({super.key, required this.payload});

  @override
  State<AlarmScreen> createState() => _AlarmScreenState();
}

class _AlarmScreenState extends State<AlarmScreen>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _ringController;
  late AnimationController _shimmerController;
  late Map<String, dynamic> _alarmData;
  String _currentTime = '';
  late final String _medicineName;
  late final String _dosage;
  late final int _notificationId;

  @override
  void initState() {
    super.initState();
    _alarmData = jsonDecode(widget.payload);
    _medicineName = _alarmData['medicineName'] ?? 'Medicine';
    _dosage = _alarmData['dosage'] ?? '';
    _notificationId = _alarmData['notificationId'] ?? 0;
    _currentTime = DateFormat('hh:mm a').format(DateTime.now());

    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    )..repeat(reverse: true);

    _ringController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    )..repeat();

    _shimmerController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _ringController.dispose();
    _shimmerController.dispose();
    super.dispose();
  }

  void _dismiss() {
    NotificationService.cancelNotification(_notificationId);
    if (mounted) Navigator.of(context).pop();
  }

  void _snooze() {
    NotificationService.snoozeAlarm(
      _notificationId,
      _medicineName,
      _dosage,
    );
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false, // Prevent back button dismissal without stopping alarm
      child: Scaffold(
        body: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFF0A0E21),
                Color(0xFF1A1A3E),
                Color(0xFF0D1B2A),
              ],
            ),
          ),
          child: SafeArea(
            child: Stack(
              children: [
                // Animated concentric rings background
                Center(
                  child: AnimatedBuilder(
                    animation: _ringController,
                    builder: (context, child) {
                      return CustomPaint(
                        size: Size(
                          MediaQuery.of(context).size.width,
                          MediaQuery.of(context).size.width,
                        ),
                        painter: _RingPainter(
                          progress: _ringController.value,
                          color: const Color(0xFF4FC3F7),
                        ),
                      );
                    },
                  ),
                ),
                // Main content
                Center(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Spacer(flex: 2),
                        // Pulsing bell icon
                        AnimatedBuilder(
                          animation: _pulseController,
                          builder: (context, child) {
                            return Transform.scale(
                              scale: 1.0 + 0.12 * _pulseController.value,
                              child: Transform.rotate(
                                angle: 0.15 *
                                    sin(_pulseController.value * pi * 2),
                                child: Container(
                                  width: 100,
                                  height: 100,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    gradient: RadialGradient(
                                      colors: [
                                        const Color(0xFF4FC3F7)
                                            .withOpacity(0.3),
                                        const Color(0xFF4FC3F7)
                                            .withOpacity(0.05),
                                      ],
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: const Color(0xFF4FC3F7)
                                            .withOpacity(
                                                0.4 * _pulseController.value),
                                        blurRadius: 30,
                                        spreadRadius: 10,
                                      ),
                                    ],
                                  ),
                                  child: const Icon(
                                    Icons.alarm,
                                    color: Color(0xFF4FC3F7),
                                    size: 50,
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                        const SizedBox(height: 24),
                        // "MEDICINE REMINDER" title
                        Text(
                          'MEDICINE REMINDER',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 4,
                          ),
                        ),
                        const SizedBox(height: 8),
                        // Current time
                        Text(
                          _currentTime,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 48,
                            fontWeight: FontWeight.w200,
                            letterSpacing: 2,
                          ),
                        ),
                        const SizedBox(height: 40),
                        // Medicine info card (glassmorphism)
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(24),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(24),
                            color: Colors.white.withOpacity(0.08),
                            border: Border.all(
                              color: Colors.white.withOpacity(0.15),
                              width: 1,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.3),
                                blurRadius: 20,
                              ),
                            ],
                          ),
                          child: Column(
                            children: [
                              Container(
                                width: 56,
                                height: 56,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(16),
                                  gradient: const LinearGradient(
                                    colors: [
                                      Color(0xFF4FC3F7),
                                      Color(0xFF29B6F6),
                                    ],
                                  ),
                                ),
                                child: const Icon(
                                  Icons.medication_rounded,
                                  color: Colors.white,
                                  size: 30,
                                ),
                              ),
                              const SizedBox(height: 16),
                              Text(
                                _medicineName,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 24,
                                  fontWeight: FontWeight.w700,
                                ),
                                textAlign: TextAlign.center,
                              ),
                              if (_dosage.isNotEmpty) ...[
                                const SizedBox(height: 8),
                                Text(
                                  'Dosage: $_dosage',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.6),
                                    fontSize: 16,
                                    fontWeight: FontWeight.w400,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                        const Spacer(flex: 2),
                        // Dismiss button (large, primary)
                        SizedBox(
                          width: double.infinity,
                          height: 60,
                          child: AnimatedBuilder(
                            animation: _shimmerController,
                            builder: (context, child) {
                              return Container(
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(30),
                                  gradient: LinearGradient(
                                    colors: const [
                                      Color(0xFF4FC3F7),
                                      Color(0xFF0288D1),
                                      Color(0xFF4FC3F7),
                                    ],
                                    stops: [
                                      0.0,
                                      _shimmerController.value,
                                      1.0,
                                    ],
                                  ),
                                  boxShadow: [
                                    BoxShadow(
                                      color: const Color(0xFF4FC3F7)
                                          .withOpacity(0.4),
                                      blurRadius: 15,
                                      offset: const Offset(0, 4),
                                    ),
                                  ],
                                ),
                                child: ElevatedButton.icon(
                                  onPressed: _dismiss,
                                  icon: const Icon(Icons.check_circle_outline,
                                      size: 26),
                                  label: const Text(
                                    'DISMISS',
                                    style: TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.w700,
                                      letterSpacing: 2,
                                    ),
                                  ),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.transparent,
                                    foregroundColor: Colors.white,
                                    shadowColor: Colors.transparent,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(30),
                                    ),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                        const SizedBox(height: 16),
                        // Snooze button (secondary)
                        SizedBox(
                          width: double.infinity,
                          height: 52,
                          child: OutlinedButton.icon(
                            onPressed: _snooze,
                            icon: const Icon(Icons.snooze_rounded, size: 22),
                            label: const Text(
                              'SNOOZE  5 MIN',
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w600,
                                letterSpacing: 1.5,
                              ),
                            ),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Colors.white.withOpacity(0.8),
                              side: BorderSide(
                                color: Colors.white.withOpacity(0.25),
                                width: 1.5,
                              ),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(30),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 48),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Paints animated concentric rings that expand outward
class _RingPainter extends CustomPainter {
  final double progress;
  final Color color;

  _RingPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width * 0.45;

    for (int i = 0; i < 4; i++) {
      final ringProgress = (progress + i * 0.25) % 1.0;
      final radius = maxRadius * ringProgress;
      final opacity = (1.0 - ringProgress) * 0.15;

      final paint = Paint()
        ..color = color.withOpacity(opacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0;

      canvas.drawCircle(center, radius, paint);
    }
  }

  @override
  bool shouldRepaint(_RingPainter oldDelegate) =>
      oldDelegate.progress != progress;
}
