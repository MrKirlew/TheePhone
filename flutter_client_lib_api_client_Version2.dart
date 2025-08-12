import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiClient {
  final String baseUrl;
  ApiClient(this.baseUrl);

  Stream<String> sendMessage({
    required String userId,
    required String sessionId,
    required String message,
    String? imageBase64,
    String? weatherLocation,
  }) async* {
    final uri = Uri.parse("$baseUrl/chat");
    final body = {
      "user_id": userId,
      "session_id": sessionId,
      "message": message,
    };
    if (imageBase64 != null) body["image_base64"] = imageBase64;
    if (weatherLocation != null) body["weather_location"] = weatherLocation;

    final req = http.Request("POST", uri);
    req.headers["Content-Type"] = "application/json";
    req.body = jsonEncode(body);

    final streamed = await req.send();

    if (streamed.statusCode != 200) {
      throw Exception("Chat failed: ${streamed.statusCode}");
    }

    await for (final chunk in streamed.stream.transform(utf8.decoder)) {
      for (final line in const LineSplitter().convert(chunk)) {
        if (line.trim().isEmpty) continue;
        final map = jsonDecode(line);
        if (map["type"] == "chunk" || map["type"] == "final") {
          yield map["data"];
        }
      }
    }
  }

  Future<void> sendFeedback(String userId, String sessionId, int rating, {String notes = ""}) async {
    final resp = await http.post(Uri.parse("$baseUrl/feedback"),
        headers: {"Content-Type":"application/json"},
        body: jsonEncode({
          "user_id": userId,
          "session_id": sessionId,
          "turn_id": "latest",
          "rating": rating,
          "notes": notes
        }));
    if (resp.statusCode != 200) throw Exception("Feedback failed");
  }
}