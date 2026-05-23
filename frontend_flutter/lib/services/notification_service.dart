import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest_all.dart' as tz;
import 'package:timezone/timezone.dart' as tz;
import 'package:intl/intl.dart';

class NotificationService {
  static final FlutterLocalNotificationsPlugin _notificationsPlugin = FlutterLocalNotificationsPlugin();

  static Future<void> init() async {
    tz.initializeTimeZones();
    // Assuming local timezone is what we want, ideally we'd use flutter_timezone package to get actual
    tz.setLocalLocation(tz.getLocation('Asia/Kolkata')); // fallback, mostly works

    const AndroidInitializationSettings initializationSettingsAndroid =
        AndroidInitializationSettings('@mipmap/ic_launcher');

    const InitializationSettings initializationSettings = InitializationSettings(
      android: initializationSettingsAndroid,
    );

    await _notificationsPlugin.initialize(settings: initializationSettings);

    final AndroidFlutterLocalNotificationsPlugin? androidImplementation =
        _notificationsPlugin.resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();

    if (androidImplementation != null) {
      await androidImplementation.requestNotificationsPermission();
      await androidImplementation.requestExactAlarmsPermission();
    }
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

    const AndroidNotificationDetails androidPlatformChannelSpecifics =
        AndroidNotificationDetails(
      'medicine_channel',
      'Medicine Reminders',
      channelDescription: 'Notifications for taking medicine',
      importance: Importance.max,
      priority: Priority.high,
    );
    const NotificationDetails platformChannelSpecifics =
        NotificationDetails(android: androidPlatformChannelSpecifics);

    // Schedule up to 30 days of notifications to avoid OS limits
    int daysScheduled = 0;
    for (DateTime d = startDate; d.isBefore(endDate.add(const Duration(days: 1))); d = d.add(const Duration(days: 1))) {
      if (daysScheduled >= 30) break; 
      
      final scheduledDate = DateTime(d.year, d.month, d.day, hour, minute);
      
      // Don't schedule in the past
      if (scheduledDate.isBefore(DateTime.now())) continue;

      // Unique ID per day per medicine
      final int notificationId = medicineId * 100 + daysScheduled;

      try {
        await _notificationsPlugin.zonedSchedule(
          id: notificationId,
          title: 'Time to take $medicineName',
          body: 'Dosage: $dosage',
          scheduledDate: tz.TZDateTime.from(scheduledDate, tz.local),
          notificationDetails: platformChannelSpecifics,
          androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        );
      } catch (e) {
        // Fallback or ignore if permissions fail
        print('Error scheduling alarm: $e');
      }
      daysScheduled++;
    }
  }

  static Future<void> cancelMedicineAlarms(int medicineId) async {
    // Cancel up to 30 IDs that might have been scheduled
    for (int i = 0; i < 30; i++) {
      await _notificationsPlugin.cancel(id: medicineId * 100 + i);
    }
  }
}
