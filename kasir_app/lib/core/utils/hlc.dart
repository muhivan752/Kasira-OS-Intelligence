class HLC {
  final int timestamp;
  final int counter;
  final String nodeId;

  HLC(this.timestamp, this.counter, this.nodeId);

  static HLC now(String nodeId) {
    return HLC(DateTime.now().millisecondsSinceEpoch, 0, nodeId);
  }

  static HLC parse(String hlcString) {
    final parts = hlcString.split(':');
    if (parts.length != 3) {
      throw FormatException('Invalid HLC format: $hlcString');
    }
    return HLC(
      int.parse(parts[0]),
      int.parse(parts[1]),
      parts[2],
    );
  }

  @override
  String toString() {
    return '$timestamp:$counter:$nodeId';
  }

  int compareTo(HLC other) {
    if (timestamp != other.timestamp) {
      return timestamp.compareTo(other.timestamp);
    }
    if (counter != other.counter) {
      return counter.compareTo(other.counter);
    }
    return nodeId.compareTo(other.nodeId);
  }

  HLC increment() {
    final now = DateTime.now().millisecondsSinceEpoch;
    if (now > timestamp) {
      return HLC(now, 0, nodeId);
    }
    return HLC(timestamp, counter + 1, nodeId);
  }

  HLC receive(HLC remote) {
    final now = DateTime.now().millisecondsSinceEpoch;
    final maxTime = timestamp > remote.timestamp ? timestamp : remote.timestamp;
    
    if (now > maxTime) {
      return HLC(now, 0, nodeId);
    } else if (timestamp == remote.timestamp) {
      final maxCounter = counter > remote.counter ? counter : remote.counter;
      return HLC(maxTime, maxCounter + 1, nodeId);
    } else {
      return HLC(maxTime, (maxTime == timestamp ? counter : remote.counter) + 1, nodeId);
    }
  }
}
