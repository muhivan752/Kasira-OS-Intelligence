# FLUTTER SKILL

## State: Riverpod
final productsProvider = AsyncNotifierProvider(ProductsNotifier.new);
final products = ref.watch(productsProvider);

## Offline-First (WAJIB)
Future addOrder(Order order) async {
  await localDb.orders.insertOne(order);   // 1. local first
  await crdtQueue.push(OrderCreated(order)); // 2. queue
  unawaited(syncService.flush());            // 3. bg sync
}

## Struktur
lib/
⊃ core/        # constants, themes, errors
⊃ data/
  ⊃ local/    # drift db, daos, crdt
  ⊃ models/   # JSON serializable
  ⊃ repos/    # abstraction layer
⊃ domain/     # entities, usecases
⊃ presentation/ # screens, widgets, providers
⊃ services/   # sync, print, websocket

## Error Handling
try {
  final result = await api.createOrder(order);
} on DioException catch (e) {
  if (e.type == DioExceptionType.connectionTimeout) {
    await localQueue.add(order); // offline queue
  }
}
