"""
Stress tests untuk CRDT sync engine Kasira.
Mensimulasikan skenario concurrent, offline partition, dan convergence
tanpa koneksi database (pure logic).
"""
import time
import uuid
import random
import threading
import pytest
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.services.crdt import HLC, PNCounter


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_hlc(node_id: str, offset_ms: int = 0) -> HLC:
    now = int(time.time() * 1000) + offset_ms
    return HLC(timestamp=now, counter=0, node_id=node_id)


def simulate_device_session(device_id: str, base_ts: int, num_events: int):
    """
    Simulasi satu device yang generate N events berturut-turut.
    Returns list of HLC strings in creation order.
    """
    hlc = HLC(base_ts, 0, device_id)
    events = []
    for i in range(num_events):
        hlc.receive(HLC(base_ts + i, 0, "server"), current_physical_time=base_ts + i)
        events.append(hlc.to_string())
    return events


# ─────────────────────────────────────────────
# Stress: HLC Monotonicity
# ─────────────────────────────────────────────

class TestHLCMonotonicityStress:
    def test_10k_events_strictly_increasing(self):
        """10.000 event dari 1 device harus selalu naik."""
        server = HLC.generate("server")
        base = server.timestamp
        prev = HLC(server.timestamp, server.counter, server.node_id)

        for i in range(10_000):
            # Simulasi client dengan timestamp yang bervariasi (bisa sama, lebih lama, dll)
            jitter = random.randint(-200, 50)  # client bisa sedikit di belakang
            client = HLC(base + jitter, random.randint(0, 5), f"client-{i % 10}")
            server.receive(client, current_physical_time=base + i)
            current = HLC(server.timestamp, server.counter, server.node_id)
            assert current.compare(prev) > 0, (
                f"Monotonicity violation at i={i}: {current.to_string()} <= {prev.to_string()}"
            )
            prev = current

    def test_50_concurrent_devices_all_events_parseable(self):
        """
        50 device generate event concurrent via threading.
        Semua event harus bisa di-parse dan valid.
        """
        results = []
        errors = []
        lock = threading.Lock()

        def device_work(device_id):
            try:
                base = int(time.time() * 1000)
                events = simulate_device_session(device_id, base, 200)
                with lock:
                    results.extend(events)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=device_work, args=(f"device-{i}",)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors in threads: {errors}"
        assert len(results) == 50 * 200

        # Semua event harus parseable
        for ev in results:
            hlc = HLC.from_string(ev)
            assert hlc.timestamp > 0

    def test_hlc_node_id_tiebreaker_deterministic(self):
        """
        Dua HLC dengan ts dan counter yang sama → node_id menentukan urutan.
        Urutan harus deterministik.
        """
        ts = 1_700_000_000_000
        nodes = [f"outlet-{chr(ord('a') + i)}" for i in range(26)]
        hlcs = [HLC(ts, 0, n) for n in nodes]

        # Sort ascending menggunakan compare
        sorted_hlcs = sorted(hlcs, key=lambda h: (h.timestamp, h.counter, h.node_id))

        for i in range(len(sorted_hlcs) - 1):
            assert sorted_hlcs[i].compare(sorted_hlcs[i + 1]) == -1


# ─────────────────────────────────────────────
# Stress: PNCounter Convergence
# ─────────────────────────────────────────────

class TestPNCounterConvergenceStress:
    def test_100_devices_converge_to_correct_stock(self):
        """
        100 device masing-masing jual 1 unit secara offline.
        Initial stock = 120. Expected final = 20.
        """
        INITIAL_STOCK = 120
        NUM_DEVICES = 100

        p_server = {"server": INITIAL_STOCK}
        negative_states = []

        for i in range(NUM_DEVICES):
            n = PNCounter.increment({}, f"device-{i}", 1)
            negative_states.append(n)

        # Merge semua
        n_merged = {}
        for n in negative_states:
            n_merged = PNCounter.merge(n_merged, n)

        final = PNCounter.get_value(p_server, n_merged)
        assert final == 20

    def test_concurrent_pncounter_merge_thread_safe(self):
        """
        50 thread merge ke dict yang sama secara bersamaan.
        Karena PNCounter.merge tidak mutate, harus aman.
        """
        base_state = {"server": 500}
        increments = [{"device-" + str(i): i + 1} for i in range(50)]

        results = []
        errors = []
        lock = threading.Lock()

        def merge_work(inc):
            try:
                # PNCounter.merge returns new dict, tidak mutate
                merged = PNCounter.merge(deepcopy(base_state), inc)
                with lock:
                    results.append(merged)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=merge_work, args=(inc,)) for inc in increments]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 50

        # Semua hasil merge harus mengandung "server"
        for r in results:
            assert r["server"] == 500

    def test_partial_sync_eventual_consistency(self):
        """
        Simulasi partial sync: 3 node sync dalam beberapa tahap.
        Setelah semua sync selesai, state harus konsisten (convergence).

        Node A: jual 3
        Node B: jual 5
        Node C: jual 2
        Initial stock: 15
        Expected final: 5
        """
        p_shared = {"server": 15}

        # Setiap node punya state lokal sendiri
        n_a = PNCounter.increment({}, "A", 3)
        n_b = PNCounter.increment({}, "B", 5)
        n_c = PNCounter.increment({}, "C", 2)

        # Tahap 1: A dan B sync dulu
        n_ab = PNCounter.merge(n_a, n_b)
        assert PNCounter.get_value(p_shared, n_ab) == 7  # 15-3-5

        # Tahap 2: C sync dengan AB
        n_abc = PNCounter.merge(n_ab, n_c)
        assert PNCounter.get_value(p_shared, n_abc) == 5  # 15-3-5-2

        # Tahap 3: Jika C sync langsung dengan B dulu (urutan berbeda)
        n_bc = PNCounter.merge(n_b, n_c)
        n_abc2 = PNCounter.merge(n_a, n_bc)
        assert PNCounter.get_value(p_shared, n_abc2) == 5  # sama, apapun urutannya

    def test_no_negative_stock_under_heavy_deduction(self):
        """
        Stok sangat kecil (5 unit) tapi banyak device jual (tiap jual 1).
        Stock tidak boleh < 0.
        """
        p = {"server": 5}
        n = {}
        for i in range(50):  # 50 device jual 1 masing-masing
            n = PNCounter.merge(n, {f"dev-{i}": 1})

        assert PNCounter.get_value(p, n) == 0

    def test_restock_propagation(self):
        """
        Stock habis → restock di server → sync ke semua device → stock naik.
        """
        p = {"server": 10}
        n = {"kasir": 10}  # jual semua
        assert PNCounter.get_value(p, n) == 0

        # Restock 20 di server
        p2 = PNCounter.increment(p, "server", 20)
        assert PNCounter.get_value(p2, n) == 20


# ─────────────────────────────────────────────
# Stress: Conflict Resolution (LWW via HLC)
# ─────────────────────────────────────────────

class TestConflictResolutionStress:
    def _make_record(self, record_id: str, ts_offset_ms: int, counter: int, node: str, name: str):
        """Helper: buat record dengan HLC attached."""
        now = int(time.time() * 1000)
        hlc = HLC(now + ts_offset_ms, counter, node)
        return {
            "id": record_id,
            "name": name,
            "hlc": hlc.to_string(),
        }

    def test_lww_newer_hlc_wins(self):
        """Record dengan HLC lebih baru harus menang (Last Write Wins)."""
        rec_id = str(uuid.uuid4())
        old_record = self._make_record(rec_id, -5000, 0, "client-A", "Kopi Lama")
        new_record = self._make_record(rec_id, 0, 0, "client-B", "Kopi Baru")

        old_hlc = HLC.from_string(old_record["hlc"])
        new_hlc = HLC.from_string(new_record["hlc"])

        winner = new_record if new_hlc.compare(old_hlc) > 0 else old_record
        assert winner["name"] == "Kopi Baru"

    def test_lww_same_timestamp_counter_tiebreaker(self):
        """Timestamp sama → counter lebih tinggi menang."""
        now = int(time.time() * 1000)
        rec_id = str(uuid.uuid4())

        hlc_low = HLC(now, 2, "client").to_string()
        hlc_high = HLC(now, 9, "client").to_string()

        rec_low = {"id": rec_id, "name": "Low", "hlc": hlc_low}
        rec_high = {"id": rec_id, "name": "High", "hlc": hlc_high}

        winner = rec_high if HLC.from_string(hlc_high).compare(HLC.from_string(hlc_low)) > 0 else rec_low
        assert winner["name"] == "High"

    def test_lww_same_ts_same_counter_node_tiebreaker(self):
        """Timestamp dan counter sama → node_id lexicographic menentukan."""
        now = int(time.time() * 1000)
        hlc_z = HLC(now, 0, "z-node").to_string()
        hlc_a = HLC(now, 0, "a-node").to_string()

        assert HLC.from_string(hlc_z).compare(HLC.from_string(hlc_a)) > 0

    def test_100_concurrent_edits_single_winner(self):
        """
        100 device edit record yang sama di waktu berbeda.
        Hanya 1 yang menang (HLC terbaru).
        """
        rec_id = str(uuid.uuid4())
        base_ts = int(time.time() * 1000)
        records = []

        for i in range(100):
            hlc = HLC(base_ts + i * 10, i % 5, f"device-{i}")
            records.append({
                "id": rec_id,
                "name": f"Edit by device-{i}",
                "hlc": hlc.to_string(),
                "device_idx": i,
            })

        # Sort by HLC descending → first is winner
        winner = max(records, key=lambda r: (
            HLC.from_string(r["hlc"]).timestamp,
            HLC.from_string(r["hlc"]).counter,
            HLC.from_string(r["hlc"]).node_id
        ))

        # Winner harus device dengan ts terbesar (device-99)
        assert winner["device_idx"] == 99

    def test_financial_strict_server_wins_on_final_status(self):
        """
        Jika record di server sudah status 'paid'/'completed',
        update dari client harus diabaikan (financial_strict strategy).
        Simulasi logic dari sync.py process_table_sync.
        """
        FINAL_STATUSES = {"paid", "completed", "refunded", "cancelled"}

        server_record = {
            "id": str(uuid.uuid4()),
            "status": "paid",
            "total": 50000,
        }

        client_update = {
            "id": server_record["id"],
            "status": "pending",  # client coba ubah ke pending
            "total": 50000,
            "hlc": HLC(int(time.time() * 1000), 0, "client").to_string(),
        }

        # Simulasi financial_strict: server menang jika status final
        if server_record["status"] in FINAL_STATUSES:
            final_record = server_record  # skip client update
        else:
            final_record = client_update

        assert final_record["status"] == "paid"

    def test_financial_strict_client_can_update_pending(self):
        """
        Record server status 'pending' → client boleh update.
        """
        FINAL_STATUSES = {"paid", "completed", "refunded", "cancelled"}

        server_record = {
            "id": str(uuid.uuid4()),
            "status": "pending",
            "total": 50000,
        }

        client_update = {
            "id": server_record["id"],
            "status": "preparing",
            "total": 50000,
            "hlc": HLC(int(time.time() * 1000), 0, "client").to_string(),
        }

        if server_record["status"] in FINAL_STATUSES:
            final_record = server_record
        else:
            final_record = client_update

        assert final_record["status"] == "preparing"


# ─────────────────────────────────────────────
# Stress: Network Partition + Rejoin
# ─────────────────────────────────────────────

class TestNetworkPartitionStress:
    def test_two_groups_partition_then_merge_converge(self):
        """
        Simulasi network partition:
        Grup A (3 kasir) dan Grup B (3 kasir) offline terpisah,
        masing-masing jual stok, lalu reconnect dan merge.
        Hasil akhir harus sama dari kedua arah.
        """
        INITIAL = 50

        # Grup A: jual 5+3+4 = 12
        p_a = {"server": INITIAL}
        n_a = {}
        for dev, qty in [("kasir-A1", 5), ("kasir-A2", 3), ("kasir-A3", 4)]:
            n_a = PNCounter.merge(n_a, PNCounter.increment({}, dev, qty))

        # Grup B: jual 6+2+7 = 15
        p_b = {"server": INITIAL}
        n_b = {}
        for dev, qty in [("kasir-B1", 6), ("kasir-B2", 2), ("kasir-B3", 7)]:
            n_b = PNCounter.merge(n_b, PNCounter.increment({}, dev, qty))

        # Rejoin: merge kedua grup
        p_final = PNCounter.merge(p_a, p_b)  # sama saja karena satu server node
        n_final = PNCounter.merge(n_a, n_b)

        final = PNCounter.get_value(p_final, n_final)
        assert final == INITIAL - 12 - 15  # 50 - 27 = 23

        # Cek commutative: merge B+A == merge A+B
        n_final2 = PNCounter.merge(n_b, n_a)
        assert PNCounter.get_value(p_final, n_final2) == final

    def test_delayed_sync_still_converges(self):
        """
        Device C lama offline (banyak sekali transaksi), akhirnya sync.
        Convergence harus tetap benar.
        """
        p = {"server": 1000}
        n_server = {}

        # Server & A langsung sync: 200 transaksi (10 device x 20 transaksi masing-masing)
        for i in range(200):
            n_server = PNCounter.increment(n_server, f"regular-device-{i % 10}", 1)

        val_after_200 = PNCounter.get_value(p, n_server)
        assert val_after_200 == 800

        # Device C offline lama, baru sync: 50 transaksi
        n_c = {}
        for i in range(50):
            n_c = PNCounter.increment(n_c, "device-C", 1)

        # Nilai di device C sebelum sync
        val_c_local = PNCounter.get_value(p, n_c)
        assert val_c_local == 950

        # Final merge
        n_final = PNCounter.merge(n_server, n_c)
        val_final = PNCounter.get_value(p, n_final)
        assert val_final == 750  # 1000 - 200 - 50

    def test_hlc_partition_groups_have_independent_clocks(self):
        """
        2 grup terpisah, masing-masing develop HLC sendiri.
        Saat rejoin, merge harus menghasilkan HLC yang tidak kurang dari keduanya.
        """
        ts = int(time.time() * 1000)

        group_a_hlc = HLC(ts, 0, "group-A")
        group_b_hlc = HLC(ts, 0, "group-B")

        # Grup A berjalan 100 event
        for i in range(100):
            r = HLC(ts + i, i % 10, f"device-A-{i % 5}")
            group_a_hlc.receive(r, current_physical_time=ts + i)

        # Grup B berjalan 80 event dengan timestamp yang berbeda
        for i in range(80):
            r = HLC(ts + i * 2, i % 7, f"device-B-{i % 3}")
            group_b_hlc.receive(r, current_physical_time=ts + i * 2)

        # Rejoin: server hlc harus >= max dari keduanya
        server_hlc = HLC(ts + 200, 0, "server")
        # A sync ke server
        server_hlc.receive(
            HLC(group_a_hlc.timestamp, group_a_hlc.counter, group_a_hlc.node_id),
            current_physical_time=ts + 200
        )
        # B sync ke server
        server_hlc.receive(
            HLC(group_b_hlc.timestamp, group_b_hlc.counter, group_b_hlc.node_id),
            current_physical_time=ts + 200
        )

        server_as_hlc = HLC(server_hlc.timestamp, server_hlc.counter, server_hlc.node_id)
        assert server_as_hlc.compare(
            HLC(group_a_hlc.timestamp, group_a_hlc.counter, group_a_hlc.node_id)
        ) >= 0
        assert server_as_hlc.compare(
            HLC(group_b_hlc.timestamp, group_b_hlc.counter, group_b_hlc.node_id)
        ) >= 0


# ─────────────────────────────────────────────
# Stress: High Volume + ThreadPoolExecutor
# ─────────────────────────────────────────────

class TestHighVolumeStress:
    def test_1000_pncounter_operations_correct_total(self):
        """
        1000 operasi increment (positif dan negatif) dari 50 device.
        Total harus sesuai kalkulasi manual.
        """
        NUM_DEVICES = 50
        OPS_PER_DEVICE = 20  # setiap device increment negative 1 kali
        INITIAL_STOCK = 2000

        p = {"server": INITIAL_STOCK}
        n = {}

        for dev in range(NUM_DEVICES):
            for op in range(OPS_PER_DEVICE):
                n = PNCounter.increment(n, f"device-{dev}", 1)

        # Total deduction = 50 * 20 = 1000
        final = PNCounter.get_value(p, n)
        assert final == INITIAL_STOCK - (NUM_DEVICES * OPS_PER_DEVICE)
        assert final == 1000

    def test_threadpool_hlc_generation_no_duplicate_strings(self):
        """
        100 thread masing-masing generate 100 HLC.
        Tidak boleh ada duplicate HLC string dari node yang sama.
        (Karena jika same ts + same counter + same node → duplicate → ordering problem)
        """
        results = []
        lock = threading.Lock()

        def gen_hlcs(node_id):
            base = int(time.time() * 1000)
            hlc = HLC(base, 0, node_id)
            local = []
            for i in range(100):
                # receive dari diri sendiri untuk advance counter
                hlc.receive(HLC(base + i, 0, "trigger"), current_physical_time=base + i)
                local.append(hlc.to_string())
            with lock:
                results.extend(local)

        with ThreadPoolExecutor(max_workers=100) as ex:
            futs = [ex.submit(gen_hlcs, f"device-{i}") for i in range(100)]
            for f in as_completed(futs):
                f.result()  # raise jika ada exception

        assert len(results) == 100 * 100
        # Per-node tidak boleh ada duplikat
        per_node = {}
        for hlc_str in results:
            hlc = HLC.from_string(hlc_str)
            per_node.setdefault(hlc.node_id, []).append(hlc_str)

        for node_id, node_events in per_node.items():
            dupes = len(node_events) - len(set(node_events))
            assert dupes == 0, f"Node {node_id} punya {dupes} duplicate HLC strings"

    def test_pncounter_large_scale_merge_associativity(self):
        """
        Merge 500 state kecil harus sama hasilnya apapun urutannya.
        Test dengan 3 urutan berbeda.
        """
        states = [{"device-" + str(i): (i % 10) + 1} for i in range(500)]

        def merge_all(lst):
            result = {}
            for s in lst:
                result = PNCounter.merge(result, s)
            return result

        # Urutan 1: sequential
        r1 = merge_all(states)

        # Urutan 2: reversed
        r2 = merge_all(list(reversed(states)))

        # Urutan 3: shuffled
        shuffled = deepcopy(states)
        random.shuffle(shuffled)
        r3 = merge_all(shuffled)

        assert r1 == r2, "Sequential vs reversed berbeda!"
        assert r1 == r3, "Sequential vs shuffled berbeda!"

    def test_hlc_receive_stress_clock_skew_resilience(self):
        """
        Beberapa client mengirim timestamp sangat jauh di masa depan (clock skew).
        Server HLC harus tetap wajar (tidak terlalu maju).
        """
        now = int(time.time() * 1000)
        server = HLC(now, 0, "server")
        MAX_SKEW = 300_000  # 5 menit

        # 100 client dengan clock skew ekstrem
        for i in range(100):
            crazy_ts = now + MAX_SKEW + random.randint(1_000, 10_000_000)
            client = HLC(crazy_ts, i, f"bad-clock-{i}")
            server.receive(client, current_physical_time=now + i * 10, max_clock_skew_ms=MAX_SKEW)

        # Server ts tidak boleh lebih dari now + MAX_SKEW + buffer kecil
        assert server.timestamp <= now + MAX_SKEW + 1000, (
            f"Server clock maju terlalu jauh: {server.timestamp - now}ms dari now"
        )
