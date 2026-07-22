'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

export type CartItem = {
  /**
   * Identitas BARIS keranjang, bukan id produk.
   *
   * Sejak ada varian, "Kopi Susu (Panas)" dan "Kopi Susu (Dingin)" itu produk
   * yang sama tapi dua baris dengan harga berbeda. Kalau keranjang masih
   * dikunci per id produk, pilih Dingin sesudah Panas cuma nambah qty baris
   * Panas — pelanggan bayar harga yang salah dan dapat minuman yang salah.
   *
   * Formatnya `productId::variantId` (variantId kosong kalau tanpa varian),
   * dibikin di `cartLineId()`. Field ini tetap dinamai `id` supaya semua
   * pemakai lama (removeItem / updateQuantity / key React) nggak perlu ikut
   * berubah.
   */
  id: string;
  /** Id produk asli — INI yang dikirim ke API pas checkout, bukan `id`. */
  productId: string;
  variantId?: string;
  variantName?: string;
  name: string;
  price: number;
  quantity: number;
  image_url?: string;
};

/** Kunci baris keranjang. Satu-satunya tempat formatnya ditentukan. */
export function cartLineId(productId: string, variantId?: string): string {
  return `${productId}::${variantId ?? ''}`;
}

type CartContextType = {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, quantity: number) => void;
  clearCart: () => void;
  totalItems: number;
  totalPrice: number;
  tableId: string | null;
  tableName: string | null;
  setTable: (id: string | null, name: string | null) => void;
};

const CartContext = createContext<CartContextType | undefined>(undefined);

export function CartProvider({ children, slug }: { children: React.ReactNode; slug: string }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [tableId, setTableId] = useState<string | null>(null);
  const [tableName, setTableName] = useState<string | null>(null);

  const setTable = (id: string | null, name: string | null) => {
    setTableId(id);
    setTableName(name);
  };

  useEffect(() => {
    const saved = localStorage.getItem(`kasira_cart_${slug}`);
    if (saved) {
      try {
        // Keranjang yang kesimpan SEBELUM fitur varian ada nggak punya
        // `productId` — dulu `id` memang id produk. Kalau dibiarkan, pelanggan
        // yang balik lagi bakal ngirim `product_id: undefined` pas checkout
        // dan kena 422 tanpa penjelasan. Dinaikkan bentuknya di sini, sekali,
        // pas dibaca.
        const parsed = JSON.parse(saved) as CartItem[];
        setItems(
          parsed.map((i) =>
            i.productId
              ? i
              : { ...i, productId: i.id, id: cartLineId(i.id, undefined) },
          ),
        );
      } catch (e) {
        console.error('Failed to parse cart', e);
      }
    }
    // Check URL for table param
    const params = new URLSearchParams(window.location.search);
    const tId = params.get('table');
    const tName = params.get('table_name');
    if (tId) {
      setTableId(tId);
      setTableName(tName || `Meja`);
    }
    setIsLoaded(true);
  }, [slug]);

  useEffect(() => {
    if (isLoaded) {
      localStorage.setItem(`kasira_cart_${slug}`, JSON.stringify(items));
    }
  }, [items, isLoaded, slug]);

  const addItem = (newItem: CartItem) => {
    setItems((prev) => {
      const existing = prev.find((i) => i.id === newItem.id);
      if (existing) {
        return prev.map((i) =>
          i.id === newItem.id ? { ...i, quantity: i.quantity + newItem.quantity } : i
        );
      }
      return [...prev, newItem];
    });
  };

  const removeItem = (id: string) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  const updateQuantity = (id: string, quantity: number) => {
    if (quantity <= 0) {
      removeItem(id);
      return;
    }
    setItems((prev) =>
      prev.map((i) => (i.id === id ? { ...i, quantity } : i))
    );
  };

  const clearCart = () => {
    setItems([]);
  };

  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);
  const totalPrice = items.reduce((sum, item) => sum + item.price * item.quantity, 0);

  return (
    <CartContext.Provider
      value={{
        items,
        addItem,
        removeItem,
        updateQuantity,
        clearCart,
        totalItems,
        totalPrice,
        tableId,
        tableName,
        setTable,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (context === undefined) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
}
