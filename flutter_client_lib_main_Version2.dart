import 'dart:async';
import 'package:flutter/material.dart';
import 'conversation_model.dart';
import 'api_client.dart';
import 'widgets/message_bubble.dart';
import 'widgets/input_bar.dart';
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
  final api = ApiClient("https://YOUR_CLOUD_RUN_URL"); // Replace
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
    String built = "";
    try {
      await for (final chunk in api.sendMessage(
        userId: userId,
        sessionId: sessionId,
        message: text,
      )) {
        built += chunk;
        setState(() {
          messages[assistantIndex] = Message("assistant", built);
        });
      }
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