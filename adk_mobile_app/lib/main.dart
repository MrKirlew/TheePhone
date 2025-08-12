import 'dart:async';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'conversation_model.dart';
import 'api_client.dart';
import 'message_bubble.dart';
import 'input_bar.dart';
import 'conversation_cache.dart';
import 'package:flutter_tts/flutter_tts.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
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

  final FirebaseAuth _auth = FirebaseAuth.instance;
  User? _user;
  FlutterTts flutterTts = FlutterTts();

  @override
  void initState() {
    super.initState();
    _auth.authStateChanges().listen((User? user) {
      setState(() {
        _user = user;
      });
    });
    _loadCached();
  }

  Future<void> _speak(String text) async {
    await flutterTts.speak(text);
  }

  Future<void> _loadCached() async {
    final cached = await cache.loadMessages(sessionId);
    setState(() { messages.addAll(cached); });
  }

  void sendMessage(String text, {bool getContacts = false, String? accessToken}) async {
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
        getContacts: getContacts,
        accessToken: accessToken,
      );
      setState(() {
        messages[assistantIndex] = Message("assistant", response);
      });
      _speak(response);
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

  Future<void> _handleSignIn() async {
    try {
      // Use the signInWithProvider method directly
      final provider = GoogleAuthProvider();
      // Add scopes if needed
      provider.addScope('email');
      provider.addScope('https://www.googleapis.com/auth/contacts.readonly');
      
      await _auth.signInWithProvider(provider);
    } catch (error) {
      print('Sign in error: $error');
      // Handle the error appropriately
    }
  }

  Future<void> _handleSignOut() async {
    try {
      await _auth.signOut();
    } catch (error) {
      print('Sign out error: $error');
    }
  }

  Widget _buildSignIn() {
    return Center(
      child: ElevatedButton(
        onPressed: _handleSignIn,
        child: const Text('SIGN IN WITH GOOGLE'),
      ),
    );
  }

  Widget _buildChat() {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text("ADK AI"),
        actions: [
          if (_user != null) ...[
            IconButton(
              icon: const Icon(Icons.logout),
              onPressed: _handleSignOut,
            ),
          ],
        ],
      ),
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
    );
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "ADK Conversational AI",
      home: _user == null ? _buildSignIn() : _buildChat(),
    );
  }
}
