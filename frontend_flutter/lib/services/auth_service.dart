import 'dart:convert';
import 'dart:io' show Platform;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:google_sign_in/google_sign_in.dart';

import 'package:smart_health/services/api_service.dart';

class AuthService {
  static String get baseUrl => ApiService.baseUrl;

  static Future<String?> googleLogin() async {
    try {
      await GoogleSignIn.instance.initialize(
        serverClientId: '543013705253-i35d9ipst9b40sc4c4g50a86v4emvlci.apps.googleusercontent.com',
      );

      final GoogleSignInAccount account = await GoogleSignIn.instance.authenticate(
        scopeHint: [
          'email',
          'https://www.googleapis.com/auth/fitness.activity.read',
          'https://www.googleapis.com/auth/fitness.blood_oxygen.read',
          'https://www.googleapis.com/auth/fitness.sleep.read',
          'https://www.googleapis.com/auth/fitness.heart_rate.read',
        ],
      );

      final GoogleSignInAuthentication auth = account.authentication;
      final String? idToken = auth.idToken;

      if (idToken == null) return "Failed to retrieve ID Token from Google.";

      final response = await http.post(
        Uri.parse('$baseUrl/google-login/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'id_token': idToken}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access', data['access']);
        await prefs.setString('refresh', data['refresh']);
        
        if (data['is_new'] == true) {
          return "NEW_USER";
        }
        return null;
      }
      return "Backend verification failed (${response.statusCode}): ${response.body}";
    } catch (e) {
      return "Exception: $e";
    }
  }

  static Future<bool> register({
    required String name,
    required String email,
    required String password,
    required String age,
    required String gender,
    required String height,
    required String weight,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/register/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': email,
          'email': email,
          'name': name,
          'password': password,
          'age': int.tryParse(age) ?? 0,
          'gender': gender,
          'height': double.tryParse(height) ?? 0.0,
          'weight': double.tryParse(weight) ?? 0.0,
        }),
      );
      if (response.statusCode == 201) return true;
      return false;
    } catch (e) {
      return false;
    }
  }

  static Future<bool> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/login/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': email, // Using email as username per backend registration setup
          'password': password,
        }),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access', data['access']);
        await prefs.setString('refresh', data['refresh']);
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }
}
