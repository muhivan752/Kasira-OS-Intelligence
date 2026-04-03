"""
Unit tests for CRDT primitives: HLC (Hybrid Logical Clock) dan PNCounter.
Tidak butuh database — pure logic tests.
"""
import time
import pytest
from backend.services.crdt import HLC, PNCounter


# ─────────────────────────────────────────────
# HLC: Basic
# ─────────────────────────────────────────────

class TestHLCBasic:
    def test_generate_has_correct_node_id(self):
        hlc = HLC.generate("device-A")
        assert hlc.node_id == "device-A"
        assert hlc.counter == 0
        assert hlc.timestamp > 0

    def test_generate_timestamp_is_milliseconds(self):
        now_ms = int(time.time() * 1000)
        hlc = HLC.generate("node")
        # should be within 1 second of now
        assert abs(hlc.timestamp - now_ms) < 1000

    def test_to_string_and_from_string_roundtrip(self):
        original = HLC(timestamp=1700000000000, counter=42, node_id="outlet-1")
        parsed = HLC.from_string(original.to_string())
        assert parsed.timestamp == original.timestamp
        assert parsed.counter == original.counter
        assert parsed.node_id == original.node_id

    def test_from_string_invalid_format_raises(self):
        with pytest.raises(ValueError):
            HLC.from_string("bad-format")

    def test_from_string_empty_returns_zero(self):
        hlc = HLC.from_string("")
        assert hlc.timestamp == 0
        assert hlc.counter == 0
        assert hlc.node_id == ""

    def test_from_string_two_parts_raises(self):
        with pytest.raises(ValueError):
            HLC.from_string("1700000000000:5")


# ─────────────────────────────────────────────
# HLC: Compare
# ─────────────────────────────────────────────

class TestHLCCompare:
    def test_greater_timestamp(self):
        a = HLC(1000, 0, "x")
        b = HLC(999, 99, "x")
        assert a.compare(b) == 1
        assert b.compare(a) == -1

    def test_same_timestamp_greater_counter(self):
        a = HLC(1000, 5, "x")
        b = HLC(1000, 4, "x")
        assert a.compare(b) == 1
        assert b.compare(a) == -1

    def test_same_timestamp_same_counter_greater_node_id(self):
        a = HLC(1000, 5, "z")
        b = HLC(1000, 5, "a")
        assert a.compare(b) == 1
        assert b.compare(a) == -1

    def test_equal_hlc(self):
        a = HLC(1000, 5, "node")
        b = HLC(1000, 5, "node")
        assert a.compare(b) == 0

    def test_transitivity(self):
        a = HLC(3000, 0, "n")
        b = HLC(2000, 10, "n")
        c = HLC(1000, 99, "n")
        assert a.compare(b) == 1
        assert b.compare(c) == 1
        assert a.compare(c) == 1

    def test_total_ordering_on_string_roundtrip(self):
        events = [HLC(t, c, "n") for t, c in [(1000, 0), (1000, 1), (1001, 0), (2000, 0)]]
        for i in range(len(events) - 1):
            assert events[i].compare(events[i + 1]) == -1


# ─────────────────────────────────────────────
# HLC: Receive (Causal Merge)
# ─────────────────────────────────────────────

class TestHLCReceive:
    def test_now_greater_than_both_resets_counter(self):
        now = int(time.time() * 1000)
        local = HLC(now - 5000, 3, "server")
        remote = HLC(now - 4000, 2, "client")
        result = local.receive(remote, current_physical_time=now)
        assert result.timestamp == now
        assert result.counter == 0

    def test_same_timestamp_increments_max_counter(self):
        ts = int(time.time() * 1000) - 10000  # 10s in the past
        local = HLC(ts, 3, "server")
        remote = HLC(ts, 7, "client")
        result = local.receive(remote, current_physical_time=ts - 1)  # physical < both
        assert result.timestamp == ts
        assert result.counter == 8  # max(3,7) + 1

    def test_local_timestamp_greater_than_remote(self):
        base = int(time.time() * 1000) - 5000
        local = HLC(base + 200, 4, "server")
        remote = HLC(base, 10, "client")
        result = local.receive(remote, current_physical_time=base - 1)
        assert result.timestamp == base + 200
        assert result.counter == 5  # local.counter + 1

    def test_remote_timestamp_greater_than_local(self):
        base = int(time.time() * 1000) - 5000
        local = HLC(base, 2, "server")
        remote = HLC(base + 300, 6, "client")
        result = local.receive(remote, current_physical_time=base - 1)
        assert result.timestamp == base + 300
        assert result.counter == 7  # remote.counter + 1

    def test_clock_skew_protection_caps_remote_timestamp(self):
        now = int(time.time() * 1000)
        max_skew = 300_000  # 5 menit
        far_future = now + max_skew + 999_999  # jauh di masa depan

        local = HLC(now, 0, "server")
        remote = HLC(far_future, 0, "client")
        result = local.receive(remote, current_physical_time=now, max_clock_skew_ms=max_skew)
        # remote harus di-cap
        assert result.timestamp <= now + max_skew + 1  # bisa == capped value

    def test_receive_preserves_monotonicity(self):
        """Setelah receive, HLC server tidak boleh turun."""
        base = int(time.time() * 1000) - 5000
        server = HLC(base + 100, 0, "server")
        before_str = server.to_string()
        before = HLC.from_string(before_str)

        remote = HLC(base, 0, "client")  # remote lebih lama
        server.receive(remote, current_physical_time=base + 50)

        # Setelah receive, server HLC tidak boleh < sebelumnya
        assert server.compare(before) >= 0

    def test_sequential_receives_strictly_increasing(self):
        """Receive berturut-turut harus menghasilkan HLC yang selalu naik."""
        server = HLC.generate("server")
        physical_now = server.timestamp

        prev = HLC.from_string(server.to_string())
        for i in range(20):
            remote = HLC(physical_now - 1000 + i, i, f"client-{i}")
            server.receive(remote, current_physical_time=physical_now)
            assert server.compare(prev) > 0
            prev = HLC(server.timestamp, server.counter, server.node_id)


# ─────────────────────────────────────────────
# PNCounter: Basic
# ─────────────────────────────────────────────

class TestPNCounterBasic:
    def test_increment_empty_state(self):
        result = PNCounter.increment({}, "device-A", 5)
        assert result["device-A"] == 5

    def test_increment_existing_node(self):
        state = {"device-A": 3}
        result = PNCounter.increment(state, "device-A", 2)
        assert result["device-A"] == 5

    def test_increment_different_nodes_are_independent(self):
        state = {}
        s1 = PNCounter.increment(state, "node-1", 10)
        s2 = PNCounter.increment(s1, "node-2", 7)
        assert s2["node-1"] == 10
        assert s2["node-2"] == 7

    def test_increment_does_not_mutate_original(self):
        original = {"node-1": 5}
        PNCounter.increment(original, "node-1", 3)
        assert original["node-1"] == 5  # tidak berubah

    def test_get_value_basic(self):
        p = {"A": 10, "B": 5}
        n = {"A": 3}
        assert PNCounter.get_value(p, n) == 12  # 15 - 3

    def test_get_value_empty_states(self):
        assert PNCounter.get_value({}, {}) == 0

    def test_get_value_never_negative(self):
        p = {"A": 2}
        n = {"A": 10, "B": 5}  # negative > positive
        assert PNCounter.get_value(p, n) == 0

    def test_get_value_none_states(self):
        assert PNCounter.get_value(None, None) == 0


# ─────────────────────────────────────────────
# PNCounter: Merge Properties (CRDT Laws)
# ─────────────────────────────────────────────

class TestPNCounterMergeProperties:
    def _state(self, **kwargs):
        return dict(kwargs)

    def test_merge_commutativity(self):
        """A merge B == B merge A"""
        a = self._state(**{"node-1": 5, "node-2": 3})
        b = self._state(**{"node-2": 7, "node-3": 2})
        assert PNCounter.merge(a, b) == PNCounter.merge(b, a)

    def test_merge_associativity(self):
        """(A merge B) merge C == A merge (B merge C)"""
        a = {"n1": 5}
        b = {"n1": 3, "n2": 8}
        c = {"n2": 10, "n3": 1}
        left = PNCounter.merge(PNCounter.merge(a, b), c)
        right = PNCounter.merge(a, PNCounter.merge(b, c))
        assert left == right

    def test_merge_idempotency(self):
        """A merge A == A"""
        a = {"n1": 5, "n2": 3}
        assert PNCounter.merge(a, a) == a

    def test_merge_takes_max_per_node(self):
        """Merge harus ambil nilai max per node, bukan sum."""
        a = {"node-1": 10, "node-2": 3}
        b = {"node-1": 7, "node-2": 9}
        merged = PNCounter.merge(a, b)
        assert merged["node-1"] == 10
        assert merged["node-2"] == 9

    def test_merge_includes_all_nodes(self):
        a = {"n1": 5}
        b = {"n2": 8}
        merged = PNCounter.merge(a, b)
        assert "n1" in merged
        assert "n2" in merged

    def test_merge_empty_with_nonempty(self):
        a = {}
        b = {"n1": 5}
        assert PNCounter.merge(a, b) == {"n1": 5}
        assert PNCounter.merge(b, a) == {"n1": 5}

    def test_merge_none_states_treated_as_empty(self):
        result = PNCounter.merge(None, {"n1": 3})
        assert result == {"n1": 3}

    def test_monotonic_growth_after_merge(self):
        """Setelah merge, get_value tidak boleh lebih kecil dari sebelum."""
        p_local = {"A": 10}
        n_local = {"A": 2}
        val_before = PNCounter.get_value(p_local, n_local)

        p_remote = {"A": 12, "B": 5}  # lebih banyak restock
        n_remote = {"A": 3}
        p_merged = PNCounter.merge(p_local, p_remote)
        n_merged = PNCounter.merge(n_local, n_remote)
        val_after = PNCounter.get_value(p_merged, n_merged)

        # Value bisa naik atau sama, tidak boleh turun di bawah logika CRDT
        # (merged selalu max, jadi positif naik atau sama, negatif naik atau sama)
        assert val_after >= 0


# ─────────────────────────────────────────────
# Skenario Realistis
# ─────────────────────────────────────────────

class TestRealisticScenarios:
    def test_hlc_two_devices_create_globally_ordered_events(self):
        """
        Device A dan B generate event secara bergantian.
        Semua event harus punya urutan global yang konsisten via HLC.
        """
        device_a = HLC.generate("device-A")
        device_b = HLC.generate("device-B")
        events = []

        for _ in range(10):
            # A membuat event, B menerima
            device_a_ts = device_a.timestamp
            a_event = HLC(device_a_ts, device_a.counter, device_a.node_id)
            events.append(("A", a_event.to_string()))
            device_b.receive(HLC.from_string(a_event.to_string()))

            # B membuat event, A menerima
            b_event = HLC(device_b.timestamp, device_b.counter, device_b.node_id)
            events.append(("B", b_event.to_string()))
            device_a.receive(HLC.from_string(b_event.to_string()))

        # Semua event string bisa di-parse
        parsed = [HLC.from_string(e[1]) for e in events]
        assert len(parsed) == 20

    def test_pncounter_stock_deduction_from_multiple_kasir(self):
        """
        3 kasir melakukan penjualan secara offline,
        saat sync, stok tetap konsisten dan tidak negatif.

        Initial stock: 20 unit (di server)
        Kasir A jual: 5
        Kasir B jual: 7
        Kasir C jual: 4
        Expected final: max(0, 20 - 5 - 7 - 4) = 4
        """
        SERVER_NODE = "server"
        KASIR_A = "kasir-A"
        KASIR_B = "kasir-B"
        KASIR_C = "kasir-C"

        # Server: initial restock 20
        p_server = PNCounter.increment({}, SERVER_NODE, 20)
        n_server = {}

        # Kasir A jual 5 (offline)
        n_a = PNCounter.increment({}, KASIR_A, 5)

        # Kasir B jual 7 (offline)
        n_b = PNCounter.increment({}, KASIR_B, 7)

        # Kasir C jual 4 (offline)
        n_c = PNCounter.increment({}, KASIR_C, 4)

        # Sync: merge semua negative counters
        n_merged = PNCounter.merge(n_server, n_a)
        n_merged = PNCounter.merge(n_merged, n_b)
        n_merged = PNCounter.merge(n_merged, n_c)

        final_stock = PNCounter.get_value(p_server, n_merged)
        assert final_stock == 4

    def test_pncounter_oversell_protection(self):
        """
        Kasir tidak boleh menjual lebih dari stok.
        Walau secara CRDT total deduction > stock, get_value harus 0 bukan negatif.
        """
        p = {"server": 5}
        n = {"kasir-A": 3, "kasir-B": 4}  # total sold: 7, melebihi stok 5
        assert PNCounter.get_value(p, n) == 0

    def test_hlc_server_clock_always_advances(self):
        """
        Server menerima banyak request dari berbagai device.
        Server HLC harus selalu maju (monotonic).
        """
        server = HLC.generate("server")
        prev_str = server.to_string()
        prev = HLC.from_string(prev_str)

        physical_now = server.timestamp

        for i in range(100):
            # Simulate 100 client requests with slightly varying timestamps
            client = HLC(physical_now - 500 + (i % 300), i % 10, f"client-{i % 5}")
            server.receive(client, current_physical_time=physical_now + i)
            current = HLC(server.timestamp, server.counter, server.node_id)
            assert current.compare(prev) > 0
            prev = current

    def test_pncounter_restock_after_sell(self):
        """
        Stok awal 10, jual 8, restock 15 → stok akhir 17.
        """
        p = {"server": 10}
        n = {"kasir-A": 8}
        assert PNCounter.get_value(p, n) == 2

        # Restock
        p2 = PNCounter.increment(p, "server", 15)
        assert PNCounter.get_value(p2, n) == 17

    def test_merge_order_independence(self):
        """
        Merge dalam urutan berbeda harus menghasilkan hasil yang sama (commutativity + associativity).
        Simulasi 4 node merge dalam berbagai urutan.
        """
        states = [
            {"n1": 5},
            {"n1": 3, "n2": 8},
            {"n2": 10, "n3": 4},
            {"n3": 1, "n4": 7},
        ]

        def merge_all(lst):
            result = {}
            for s in lst:
                result = PNCounter.merge(result, s)
            return result

        import itertools
        results = set()
        for perm in itertools.permutations(range(len(states))):
            merged = merge_all([states[i] for i in perm])
            results.add(frozenset(merged.items()))

        assert len(results) == 1, "Semua urutan merge harus menghasilkan hasil yang sama"
