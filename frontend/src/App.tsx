import React, { useState, useEffect } from 'react';

export default function App() {
  const [stock, setStock] = useState<number>(100);
  const [statusLogs, setStatusLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/updates');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatusLogs((prev) => [`Order ${data.order_id} -> ${data.status}`, ...prev]);
    };
    return () => ws.close();
  }, []);

  const handleInitStock = async () => {
    await fetch('http://localhost:8000/api/v1/products/init', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: 'prod_phone_123', stock: 100 }),
    });
    setStock(100);
    setStatusLogs((prev) => ['Initialized product stock to 100', ...prev]);
  };

  const handleBuy = async () => {
    setLoading(true);
    const idempotencyKey = crypto.randomUUID();
    const userId = `usr_${Math.floor(Math.random() * 10000)}`;

    try {
      const res = await fetch('http://localhost:8000/api/v1/orders/reserve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify({
          product_id: 'prod_phone_123',
          user_id: userId,
          quantity: 1,
        }),
      });

      if (res.ok) {
        setStock((prev) => Math.max(0, prev - 1));
        setStatusLogs((prev) => [`Reserved by ${userId}`, ...prev]);
      } else {
        setStatusLogs((prev) => ['Purchase failed: Sold Out!', ...prev]);
      }
    } catch (err) {
      setStatusLogs((prev) => ['Network error', ...prev]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: 650, margin: '40px auto', padding: 20 }}>
      <h1>Distributed Flash-Sale Engine</h1>
      <div style={{ border: '1px solid #ddd', padding: 20, borderRadius: 8, marginBottom: 20 }}>
        <h2>Flagship Smartphone 15 Pro</h2>
        <p>Real-Time In-Memory Stock: <strong>{stock}</strong></p>
        <button 
          onClick={handleBuy} 
          disabled={loading || stock === 0}
          style={{ padding: '10px 20px', background: stock === 0 ? '#ccc' : '#0070f3', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
        >
          {loading ? 'Reserving...' : stock === 0 ? 'Out of Stock' : 'Flash Buy Now'}
        </button>
        <button 
          onClick={handleInitStock} 
          style={{ marginLeft: 10, padding: '10px 15px', background: '#333', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
        >
          Reset Stock (100)
        </button>
      </div>

      <div style={{ border: '1px solid #ddd', padding: 15, borderRadius: 8, height: 250, overflowY: 'auto' }}>
        <h3>Live Event Stream (Redis Pub/Sub & WebSocket)</h3>
        {statusLogs.map((log, idx) => (
          <div key={idx} style={{ fontSize: 13, borderBottom: '1px solid #f0f0f0', padding: '4px 0' }}>{log}</div>
        ))}
      </div>
    </div>
  );
}