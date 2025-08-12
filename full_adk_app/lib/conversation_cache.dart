import 'dart:io';
import 'dart:convert';
import 'package:path_provider/path_provider.dart';
import 'conversation_model.dart';

class ConversationCache {
  Future<String> get _localPath async {
    final directory = await getApplicationDocumentsDirectory();
    return directory.path;
  }

  Future<File> get _localFile async {
    final path = await _localPath;
    return File('$path/conversations.json');
  }

  Future<void> saveMessages(String sessionId, List<Message> messages) async {
    try {
      final file = await _localFile;
      
      // Load existing data
      Map<String, dynamic> data = {};
      if (await file.exists()) {
        final contents = await file.readAsString();
        data = json.decode(contents);
      }
      
      // Save messages for this session
      data[sessionId] = messages.map((m) => {
        'sender': m.sender,
        'text': m.text,
        'timestamp': DateTime.now().toIso8601String()
      }).toList();
      
      // Keep only recent sessions (limit to 10)
      if (data.length > 10) {
        final keys = data.keys.toList();
        while (data.length > 10) {
          data.remove(keys.removeAt(0));
        }
      }
      
      await file.writeAsString(json.encode(data));
    } catch (e) {
      // Handle error silently to not break the app
      print('Error saving messages to cache: $e');
    }
  }

  Future<List<Message>> loadMessages(String sessionId) async {
    try {
      final file = await _localFile;
      
      if (await file.exists()) {
        final contents = await file.readAsString();
        final data = json.decode(contents);
        
        if (data.containsKey(sessionId)) {
          final List<dynamic> messagesJson = data[sessionId];
          return messagesJson.map((json) => Message(
            json['sender'] as String,
            json['text'] as String,
          )).toList();
        }
      }
    } catch (e) {
      // Handle error silently to not break the app
      print('Error loading messages from cache: $e');
    }
    
    return [];
  }

  Future<void> clearMessages(String sessionId) async {
    try {
      final file = await _localFile;
      if (await file.exists()) {
        final contents = await file.readAsString();
        final data = json.decode(contents);
        data.remove(sessionId);
        await file.writeAsString(json.encode(data));
      }
    } catch (e) {
      print('Error clearing messages for session: $e');
    }
  }

  Future<void> clearCache() async {
    try {
      final file = await _localFile;
      if (await file.exists()) {
        await file.delete();
      }
    } catch (e) {
      // Handle error silently to not break the app
      print('Error clearing cache: $e');
    }
  }
}
