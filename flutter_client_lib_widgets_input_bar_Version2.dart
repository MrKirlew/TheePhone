import 'package:flutter/material.dart';

class InputBar extends StatefulWidget {
  final void Function(String) onSend;
  const InputBar({super.key, required this.onSend});

  @override
  State<InputBar> createState() => _InputBarState();
}

class _InputBarState extends State<InputBar> {
  final controller = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Expanded(
        child: TextField(
          controller: controller,
          decoration: const InputDecoration(
            hintText: "Say something...",
          ),
        ),
      ),
      IconButton(
        icon: const Icon(Icons.send),
        onPressed: () {
          final text = controller.text.trim();
            if (text.isNotEmpty) {
              widget.onSend(text);
              controller.clear();
            }
        },
      )
    ]);
  }
}