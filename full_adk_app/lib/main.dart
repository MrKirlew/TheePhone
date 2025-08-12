import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';
import 'conversation_model.dart';
import 'api_client.dart';
import 'message_bubble.dart';
import 'conversation_cache.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ADKApp());
}

class ADKApp extends StatelessWidget {
  const ADKApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ADK AI Chat',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const ChatScreen(),
    );
  }
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final api = ApiClient("https://adk-mobile-service-843267258954.us-central1.run.app");
  final List<Message> messages = [];
  final cache = ConversationCache();
  final TextEditingController controller = TextEditingController();
  final ImagePicker picker = ImagePicker();
  
  bool streaming = false;
  String userId = "user123";
  String sessionId = "session1";
  File? selectedImage;

  @override
  void initState() {
    super.initState();
    _loadCached();
    _requestPermissions();
  }

  Future<void> _requestPermissions() async {
    await [
      Permission.camera,
      Permission.storage,
    ].request();
  }

  Future<void> _loadCached() async {
    final cached = await cache.loadMessages(sessionId);
    setState(() { 
      messages.addAll(cached); 
    });
  }

  Future<void> _pickImage() async {
    final XFile? image = await picker.pickImage(source: ImageSource.gallery);
    if (image != null) {
      setState(() {
        selectedImage = File(image.path);
      });
    }
  }

  Future<void> _takePhoto() async {
    final XFile? image = await picker.pickImage(source: ImageSource.camera);
    if (image != null) {
      setState(() {
        selectedImage = File(image.path);
      });
    }
  }

  void _clearImage() {
    setState(() {
      selectedImage = null;
    });
  }

  void sendMessage(String text) async {
    if (text.trim().isEmpty && selectedImage == null) return;

    String? imageBase64;
    if (selectedImage != null) {
      final bytes = await selectedImage!.readAsBytes();
      imageBase64 = base64Encode(bytes);
    }

    setState(() {
      messages.add(Message("user", text.isEmpty ? "[Image sent]" : text));
      streaming = true;
      messages.add(Message("assistant", ""));
      selectedImage = null; // Clear image after sending
    });

    int assistantIndex = messages.length - 1;
    
    try {
      final response = await api.sendMessage(
        userId: userId,
        sessionId: sessionId,
        message: text.isEmpty ? "What do you see in this image?" : text,
        imageBase64: imageBase64,
      );
      
      setState(() {
        messages[assistantIndex] = Message("assistant", response);
      });
    } catch (e) {
      setState(() {
        messages[assistantIndex] = Message("assistant", "Error: $e");
      });
    } finally {
      streaming = false;
      await cache.saveMessages(sessionId, messages.take(100).toList());
      setState(() {});
      controller.clear();
    }
  }

  void _showImageOptions() {
    showModalBottomSheet(
      context: context,
      builder: (BuildContext context) {
        return SafeArea(
          child: Wrap(
            children: [
              ListTile(
                leading: const Icon(Icons.camera_alt),
                title: const Text('Take Photo'),
                onTap: () {
                  Navigator.pop(context);
                  _takePhoto();
                },
              ),
              ListTile(
                leading: const Icon(Icons.photo_library),
                title: const Text('Choose from Gallery'),
                onTap: () {
                  Navigator.pop(context);
                  _pickImage();
                },
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("ADK AI Chat"),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.delete),
            onPressed: () {
              setState(() {
                messages.clear();
              });
              cache.clearMessages(sessionId);
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Image preview
          if (selectedImage != null)
            Container(
              height: 120,
              width: double.infinity,
              margin: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Stack(
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Image.file(
                      selectedImage!,
                      width: double.infinity,
                      height: 120,
                      fit: BoxFit.cover,
                    ),
                  ),
                  Positioned(
                    top: 4,
                    right: 4,
                    child: IconButton(
                      onPressed: _clearImage,
                      icon: const Icon(Icons.close, color: Colors.white),
                      style: IconButton.styleFrom(
                        backgroundColor: Colors.black54,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          
          // Messages
          Expanded(
            child: ListView.builder(
              itemCount: messages.length,
              itemBuilder: (_, i) => MessageBubble(message: messages[i]),
            ),
          ),
          
          // Loading indicator
          if (streaming) const LinearProgressIndicator(),
          
          // Input area
          Container(
            padding: const EdgeInsets.all(8),
            child: Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.photo_camera),
                  onPressed: _showImageOptions,
                ),
                Expanded(
                  child: TextField(
                    controller: controller,
                    decoration: const InputDecoration(
                      hintText: 'Type a message...',
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: sendMessage,
                    maxLines: null,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: () => sendMessage(controller.text),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}