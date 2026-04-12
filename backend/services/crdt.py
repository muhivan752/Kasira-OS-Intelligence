import time
from typing import Dict, Any, Tuple

class HLC:
    """
    Hybrid Logical Clock (HLC)
    Format: timestamp:counter:node_id
    """
    def __init__(self, timestamp: int, counter: int, node_id: str):
        self.timestamp = timestamp
        self.counter = counter
        self.node_id = node_id

    @classmethod
    def generate(cls, node_id: str) -> 'HLC':
        """Generate a new HLC based on current physical time."""
        # Current time in milliseconds
        now = int(time.time() * 1000)
        return cls(timestamp=now, counter=0, node_id=node_id)

    @classmethod
    def from_string(cls, hlc_str: str) -> 'HLC':
        """Parse HLC from string."""
        if not hlc_str:
            return cls(0, 0, "")
        parts = hlc_str.split(':', 2)
        if len(parts) < 3:
            raise ValueError(f"Invalid HLC string format: {hlc_str}")
        return cls(int(parts[0]), int(parts[1]), parts[2])

    def to_string(self) -> str:
        """Convert HLC to string."""
        return f"{self.timestamp}:{self.counter}:{self.node_id}"

    def compare(self, other: 'HLC') -> int:
        """
        Compare two HLCs.
        Returns:
            1 if self > other
           -1 if self < other
            0 if self == other
        """
        if self.timestamp > other.timestamp:
            return 1
        if self.timestamp < other.timestamp:
            return -1
        
        if self.counter > other.counter:
            return 1
        if self.counter < other.counter:
            return -1
            
        if self.node_id > other.node_id:
            return 1
        if self.node_id < other.node_id:
            return -1
            
        return 0

    def receive(self, remote: 'HLC', current_physical_time: int = None, max_clock_skew_ms: int = 300000) -> 'HLC':
        now = current_physical_time or int(time.time() * 1000)
        
        # Clock Skew Protection: If remote timestamp is too far in the future,
        # cap it to the maximum allowed skew to prevent the server clock from being dragged forward.
        if remote.timestamp > now + max_clock_skew_ms:
            remote.timestamp = now + max_clock_skew_ms
            
        max_ts = max(self.timestamp, remote.timestamp)
        if now > max_ts:
            self.timestamp = now
            self.counter = 0
        elif self.timestamp == remote.timestamp:
            self.counter = max(self.counter, remote.counter) + 1
        elif self.timestamp > remote.timestamp:
            self.counter = self.counter + 1
        else:
            self.timestamp = remote.timestamp
            self.counter = remote.counter + 1
        return self


class PNCounter:
    """
    Positive-Negative Counter (PN-Counter) CRDT.
    Uses two G-Counters (Grow-only Counters): one for increments (positive), one for decrements (negative).
    Stored as JSONB in the database: {"node_id": count}
    """
    @staticmethod
    def merge(local_state: Dict[str, int], remote_state: Dict[str, int]) -> Dict[str, int]:
        """
        Merge two G-Counters by taking the maximum value for each node.
        """
        if not local_state:
            local_state = {}
        if not remote_state:
            remote_state = {}
            
        merged = dict(local_state)
        for node_id, count in remote_state.items():
            if node_id in merged:
                merged[node_id] = max(merged[node_id], count)
            else:
                merged[node_id] = count
        return merged

    @staticmethod
    def get_value(positive_state: Dict[str, int], negative_state: Dict[str, int]) -> int:
        """
        Calculate the current value of the PN-Counter.
        Value = sum(positive) - sum(negative)
        """
        p_sum = sum(positive_state.values()) if positive_state else 0
        n_sum = sum(negative_state.values()) if negative_state else 0
        return max(0, p_sum - n_sum)

    @staticmethod
    def increment(state: Dict[str, int], node_id: str, amount: int = 1) -> Dict[str, int]:
        """
        Increment the counter for a specific node.
        """
        if not state:
            state = {}
        new_state = dict(state)
        new_state[node_id] = new_state.get(node_id, 0) + amount
        return new_state
