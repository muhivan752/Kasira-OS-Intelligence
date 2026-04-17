import 'package:flutter_riverpod/flutter_riverpod.dart';

enum PosMode { selection, takeaway, dineInTableSelect, dineInOrdering }

final posModeProvider = StateProvider<PosMode>((ref) => PosMode.selection);
