import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

// Handler for background messages
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Initialize Firebase if needed
  await Firebase.initializeApp();
  
  // Handle background message
  print('Background message received: ${message.messageId}');
  
  // You can show a notification here or store the message for later display
}

Future<void> initFirebase() async {
  try {
    // Initialize Firebase
    await Firebase.initializeApp();
    
    // Set the background messaging handler
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
    
    // Get the token
    final fcmToken = await FirebaseMessaging.instance.getToken();
    print('FCM Token: $fcmToken');
    
    // Request permission for notifications (iOS)
    await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    
    // Handle foreground messages
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      print('Foreground message received: ${message.messageId}');
      
      // Handle the message (show notification, update UI, etc.)
      if (message.notification != null) {
        print('Message notification: ${message.notification!.title}');
        print('Message body: ${message.notification!.body}');
      }
    });
    
    // Handle when app is opened from terminated state
    RemoteMessage? initialMessage = await FirebaseMessaging.instance.getInitialMessage();
    if (initialMessage != null) {
      print('App opened from terminated state with message: ${initialMessage.messageId}');
    }
    
    // Handle when app is in background and opened from notification
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      print('App opened from background with message: ${message.messageId}');
    });
  } catch (e) {
    print('Error initializing Firebase: $e');
  }
}
