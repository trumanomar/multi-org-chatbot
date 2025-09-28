import 'package:flutter/material.dart';

class UploadButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final bool loading;
  final String? error;
  final String? success;

  const UploadButton({
    super.key,
    this.onPressed,
    this.loading = false,
    this.error,
    this.success,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (loading) const LinearProgressIndicator(),
        if (error != null) ...[
          const SizedBox(height: 8),
          Text(
            error!,
            style: const TextStyle(color: Colors.red),
          ),
        ],
        if (success != null) ...[
          const SizedBox(height: 8),
          Text(
            success!,
            style: const TextStyle(color: Colors.green),
          ),
        ],
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: loading ? null : onPressed,
          icon: const Icon(Icons.upload_file),
          label: const Text('Pick & upload'),
        ),
      ],
    );
  }
}
