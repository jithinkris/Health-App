import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest_all.dart' as tz;
import 'package:timezone/timezone.dart' as tz;
import 'package:intl/intl.dart';

// Android Notification.FLAG_INSISTENT — repeats sound/vibration until dismissed
const int _kFlagInsistent = 4;

class NotificationService {
  static final FlutterLocalNotificationsPlugin _notificationsPlugin =
      FlutterLocalNotificationsPlugin();

  // Callback for when a notification is tapped (set from main.dart)
  static void Function(NotificationResponse)? onNotificationTapped;

  // Stores payload if the app was launched from a notification
  static String? _launchPayload;

  static Future<void> init({
    void Function(NotificationResponse)? onTap,
  }) async {
    onNotificationTapped = onTap;

    tz.initializeTimeZones();
    tz.setLocalLocation(tz.getLocation('Asia/Kolkata'));

    const AndroidInitializationSettings initializationSettingsAndroid =
        AndroidInitializationSettings('@mipmap/ic_launcher');

    const InitializationSettings initializationSettings =
        InitializationSettings(
      android: initializationSettingsAndroid,
    );

    await _notificationsPlugin.initialize(
      settings: initializationSettings,
      onDidReceiveNotificationResponse: _onNotificationResponse,
    );

    final AndroidFlutterLocalNotificationsPlugin? androidImplementation =
        _notificationsPlugin.resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();

    if (androidImplementation != null) {
      await androidImplementation.requestNotificationsPermission();
      await androidImplementation.requestExactAlarmsPermission();
    }

    // Check if app was launched from a notification
    final launchDetails =
        await _notificationsPlugin.getNotificationAppLaunchDetails();
    if (launchDetails?.didNotificationLaunchApp == true &&
        launchDetails?.notificationResponse?.payload != null) {
      _launchPayload = launchDetails!.notificationResponse!.payload;
    }
  }

  /// Called when user taps on a notification or its action buttons.
  static void _onNotificationResponse(NotificationResponse response) {
    // Handle "Dismiss" action: notification is already cancelled via cancelNotification flag
    if (response.actionId == 'dismiss_action') {
      return;
    }

    // Handle "Snooze" action
    if (response.actionId == 'snooze_action') {
      final payload = response.payload;
      if (payload != null) {
        try {
          final data = jsonDecode(payload);
          snoozeAlarm(
            data['notificationId'] ?? 0,
            data['medicineName'] ?? 'Medicine',
            data['dosage'] ?? '',
          );
        } catch (_) {}
      }
      return;
    }

    // Default: user tapped the notification body → open alarm screen
    onNotificationTapped?.call(response);
  }

  /// Returns and clears any pending launch payload (from cold launch via notification).
  static String? consumeLaunchPayload() {
    final payload = _launchPayload;
    _launchPayload = null;
    return payload;
  }

  /// Builds alarm-style notification details: loud, vibrating, looping, full-screen.
  static AndroidNotificationDetails _alarmNotificationDetails(
      String medicineName, String dosage, int notificationId) {
    return AndroidNotificationDetails(
      'medicine_alarm_channel_v2', // New channel ID (Android caches channel settings)
      'Medicine Alarm',
      channelDescription: 'Loud alarm-style reminders for taking medicine',
      importance: Importance.max,
      priority: Priority.max,
      playSound: true,
      sound: const RawResourceAndroidNotificationSound('alarm_sound'),
      enableVibration: true,
      vibrationPattern: Int64List.fromList(
          [0, 500, 200, 500, 200, 500, 200, 500, 200, 500]),
      ongoing: true, // Cannot be swiped away
      autoCancel: false,
      fullScreenIntent: true, // Shows full-screen on locked devices
      category: AndroidNotificationCategory.alarm,
      audioAttributesUsage: AudioAttributesUsage.alarm, // Plays through alarm channel (loud)
      additionalFlags: Int32List.fromList([_kFlagInsistent]), // Loops sound/vibration
      visibility: NotificationVisibility.public, // Show on lock screen
      actions: <AndroidNotificationAction>[
        const AndroidNotificationAction(
          'dismiss_action',
          '✓  Dismiss',
          showsUserInterface: false,
          cancelNotification: true,
        ),
        const AndroidNotificationAction(
          'snooze_action',
          '⏰  Snooze 5 min',
          showsUserInterface: false,
          cancelNotification: true,
        ),
      ],
    );
  }

  static Future<void> scheduleMedicineAlarms({
    required int medicineId,
    required String medicineName,
    required String dosage,
    required String timeStr, // "HH:MM"
    required DateTime startDate,
    required DateTime endDate,
  }) async {
    // First, cancel any existing alarms for this medicine
    await cancelMedicineAlarms(medicineId);

    final timeParts = timeStr.split(':');
    final int hour = int.parse(timeParts[0]);
    final int minute = int.parse(timeParts[1]);

    // Schedule up to 30 days of alarms to avoid OS limits
    int daysScheduled = 0;
    for (DateTime d = startDate;
        d.isBefore(endDate.add(const Duration(days: 1)));
        d = d.add(const Duration(days: 1))) {
      if (daysScheduled >= 30) break;

      final scheduledDate = DateTime(d.year, d.month, d.day, hour, minute);

      // Don't schedule in the past
      if (scheduledDate.isBefore(DateTime.now())) continue;

      // Unique ID per day per medicine
      final int notificationId = medicineId * 100 + daysScheduled;

      // Payload with all info the alarm screen needs
      final String payload = jsonEncode({
        'medicineId': medicineId,
        'medicineName': medicineName,
        'dosage': dosage,
        'notificationId': notificationId,
        'scheduledTime': timeStr,
      });

      final alarmDetails =
          _alarmNotificationDetails(medicineName, dosage, notificationId);

      final NotificationDetails platformDetails =
          NotificationDetails(android: alarmDetails);

      try {
        await _notificationsPlugin.zonedSchedule(
          id: notificationId,
          title: '💊 Time to take $medicineName',
          body: 'Dosage: $dosage — Tap to open',
          payload: payload,
          scheduledDate: tz.TZDateTime.from(scheduledDate, tz.local),
          notificationDetails: platformDetails,
          androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
        );
      } catch (e) {
        print('Error scheduling alarm: $e');
      }
      daysScheduled++;
    }
  }

  /// Cancel a single notification by its ID.
  static Future<void> cancelNotification(int notificationId) async {
    await _notificationsPlugin.cancel(id: notificationId);
  }

  /// Cancel all alarms for a medicine.
  static Future<void> cancelMedicineAlarms(int medicineId) async {
    for (int i = 0; i < 30; i++) {
      await _notificationsPlugin.cancel(id: medicineId * 100 + i);
    }
    // Also cancel any snooze notifications for this medicine
    for (int i = 0; i < 30; i++) {
      await _notificationsPlugin.cancel(id: medicineId * 100 + i + 50000);
    }
  }

  /// Snooze: cancel current alarm and reschedule 5 minutes from now.
  static Future<void> snoozeAlarm(
      int notificationId, String medicineName, String dosage) async {
    await _notificationsPlugin.cancel(id: notificationId);

    final snoozeTime =
        tz.TZDateTime.now(tz.local).add(const Duration(minutes: 5));

    // Use a snooze-specific ID range to avoid conflicts
    final snoozeId = notificationId + 50000;

    final String payload = jsonEncode({
      'medicineName': medicineName,
      'dosage': dosage,
      'notificationId': snoozeId,
    });

    final alarmDetails =
        _alarmNotificationDetails(medicineName, dosage, snoozeId);

    final NotificationDetails platformDetails =
        NotificationDetails(android: alarmDetails);

    try {
      await _notificationsPlugin.zonedSchedule(
        id: snoozeId,
        title: '⏰ Snoozed: Take $medicineName',
        body: 'Dosage: $dosage — Snoozed reminder',
        payload: payload,
        scheduledDate: snoozeTime,
        notificationDetails: platformDetails,
        androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      );
    } catch (e) {
      print('Error scheduling snooze: $e');
    }
  }
}
