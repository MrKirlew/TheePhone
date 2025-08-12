import 'dart:async';
import 'package:flutter/material.dart';
import 'conversation_model.dart';
import 'api_client.dart';
import 'message_bubble.dart';
import 'input_bar.dart';
import 'conversation_cache.dart';
import 'firebase_push.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initFirebase();
  runApp(const ADKApp());
}

class ADKApp extends StatefulWidget {
  const ADKApp({super.key});
  @override
  State<ADKApp> createState() => _ADKAppState();
}

class _ADKAppState extends State<ADKApp> {
  final api = ApiClient("https://adk-mobile-service-7v7fbrn4va-uc.a.run.app");
  final List<Message> messages = [];
  final cache = ConversationCache();
  bool streaming = false;
  String userId = "user123";
  String sessionId = "session1";

  @override
  void initState() {
    super.initState();
    _loadCached();
  }

  Future<void> _loadCached() async {
    final cached = await cache.loadMessages(sessionId);
    setState(() { messages.addAll(cached); });
  }

  void sendMessage(String text) async {
    setState(() {
      messages.add(Message("user", text));
      streaming = true;
      messages.add(Message("assistant", ""));
    });
    int assistantIndex = messages.length - 1;
    
    try {
      final response = await api.sendMessage(
        userId: userId,
        sessionId: sessionId,
        message: text,
      );
      setState(() {
        messages[assistantIndex] = Message("assistant", response);
      });
    } catch (e) {
      setState(() {
        messages[assistantIndex] = Message("assistant","Error: $e");
      });
    } finally {
      streaming = false;
      await cache.saveMessages(sessionId, messages.take(100).toList()); // keep recent 100
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "ADK Conversational AI",
      home: Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(title: const Text("ADK AI")),
        body: Column(
          children: [
            Expanded(
              child: ListView.builder(
                itemCount: messages.length,
                itemBuilder: (_, i) => MessageBubble(message: messages[i]),
              ),
            ),
            if (streaming) const LinearProgressIndicator(),
            InputBar(onSend: sendMessage),
          ],
        ),
      ),
    );
  }
}
