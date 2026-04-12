'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Search,
  Filter,
  FileText,
  Clock,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { getSuperadminAuditLogs } from '@/app/actions/superadmin';

const ENTITIES = ['all', 'orders', 'products', 'tenants', 'users', 'payments', 'ingredients', 'recipes'] as const;

export default function AuditLogPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterEntity, setFilterEntity] = useState('all');
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const LIMIT = 30;

  const load = useCallback(async () => {
    setLoading(true);
    const params: any = { limit: LIMIT, skip: page * LIMIT };
    if (filterEntity !== 'all') params.entity = filterEntity;
    const result = await getSuperadminAuditLogs(params);
    setLogs(result.logs || []);
    setTotal(result.meta?.total || 0);
    setLoading(false);
  }, [filterEntity, page]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setPage(0);
  }, [filterEntity]);

  const totalPages = Math.ceil(total / LIMIT);

  const actionColor = (action: string) => {
    if (action.startsWith('CREATE') || action.startsWith('REGISTER')) return 'text-green-400 bg-green-500/10';
    if (action.startsWith('UPDATE') || action.startsWith('CHANGE')) return 'text-blue-400 bg-blue-500/10';
    if (action.startsWith('DELETE') || action.startsWith('SUSPEND')) return 'text-red-400 bg-red-500/10';
    return 'text-gray-400 bg-gray-800';
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Audit Log</h1>
        <p className="text-gray-500 text-sm mt-1">Riwayat semua perubahan data platform</p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-4 h-4 text-gray-500" />
          {ENTITIES.map((e) => (
            <button
              key={e}
              onClick={() => setFilterEntity(e)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                ${filterEntity === e ? 'bg-gray-700 text-white' : 'bg-gray-900 text-gray-500 hover:bg-gray-800'}`}
            >
              {e === 'all' ? 'Semua' : e.charAt(0).toUpperCase() + e.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Log List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="px-5 py-12 text-center text-gray-600 text-sm">Memuat...</div>
        ) : logs.length === 0 ? (
          <div className="px-5 py-12 text-center text-gray-600 text-sm">Tidak ada log ditemukan</div>
        ) : (
          <div className="divide-y divide-gray-800">
            {logs.map((log: any) => {
              const isExpanded = expandedId === log.id;
              return (
                <div key={log.id}>
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : log.id)}
                    className="w-full flex items-center gap-4 px-5 py-3 hover:bg-gray-800/30 transition-colors text-left"
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-gray-600 flex-shrink-0" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-600 flex-shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${actionColor(log.action)}`}>
                          {log.action}
                        </span>
                        <span className="text-xs text-gray-500">{log.entity}</span>
                        {log.tenant_name && (
                          <span className="text-xs text-gray-600">&middot; {log.tenant_name}</span>
                        )}
                      </div>
                      <div className="text-xs text-gray-600 mt-0.5">
                        {log.user_name || 'System'} &middot; {formatTime(log.created_at)}
                      </div>
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="px-5 pb-4 pl-14 space-y-2">
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div>
                          <div className="text-gray-500 mb-1">Entity ID</div>
                          <div className="text-gray-400 font-mono text-[10px] break-all">{log.entity_id}</div>
                        </div>
                        {log.request_id && (
                          <div>
                            <div className="text-gray-500 mb-1">Request ID</div>
                            <div className="text-gray-400 font-mono text-[10px] break-all">{log.request_id}</div>
                          </div>
                        )}
                      </div>
                      {log.before_state && (
                        <div>
                          <div className="text-gray-500 text-xs mb-1">Before</div>
                          <pre className="bg-gray-950 border border-gray-800 rounded-lg p-3 text-[11px] text-red-300 overflow-x-auto">
                            {JSON.stringify(log.before_state, null, 2)}
                          </pre>
                        </div>
                      )}
                      {log.after_state && (
                        <div>
                          <div className="text-gray-500 text-xs mb-1">After</div>
                          <pre className="bg-gray-950 border border-gray-800 rounded-lg p-3 text-[11px] text-green-300 overflow-x-auto">
                            {JSON.stringify(log.after_state, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-gray-800">
            <div className="text-xs text-gray-600">{total} total log</div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="px-3 py-1.5 text-xs bg-gray-800 text-gray-400 rounded-lg disabled:opacity-30 hover:bg-gray-700"
              >
                Prev
              </button>
              <span className="text-xs text-gray-500">{page + 1} / {totalPages}</span>
              <button
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={page >= totalPages - 1}
                className="px-3 py-1.5 text-xs bg-gray-800 text-gray-400 rounded-lg disabled:opacity-30 hover:bg-gray-700"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
