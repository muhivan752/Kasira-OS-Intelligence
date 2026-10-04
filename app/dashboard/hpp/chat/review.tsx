import type { HppChatPreview, HppChatSession } from '@/lib/hpp-chat';
import { hppMoney, hppNumber } from '@/lib/hpp';

const labels: Record<string, string> = { user: 'Dari cerita kamu', estimate: 'Estimasi', existing: 'Data toko', unknown: 'Belum diisi' };
const actions = { create: 'Bahan baru', reuse: 'Pakai bahan toko', update_price: 'Ubah harga bahan toko' };
const format = (value: string | null) => value === null ? 'Belum diisi' : hppNumber(Number(value));
const cost = (value: string) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: 8 }).format(Number(value));

type Props = {
  session: HppChatSession; preview: HppChatPreview; busy: boolean; hasUnsent: boolean; hasError: boolean;
  confirmed: boolean; replacing: boolean; onConfirmed: (value: boolean) => void;
  onReplacing: (value: boolean) => void; onApprove: () => void;
};

export function HppReview({ session, preview, busy, hasUnsent, hasError, confirmed, replacing, onConfirmed, onReplacing, onApprove }: Props) {
  const blocked = busy || !preview.ready || session.pending || hasError || hasUnsent;
  return <div className="hpp-chat-review">
    <div className="hpp-chat-review-total">
      <p>{preview.is_estimated ? 'Estimasi HPP bahan per porsi' : 'HPP bahan per porsi'}</p>
      <p className="hpp-chat-price" data-testid="hpp-review-total">{preview.total_cost !== null ? hppMoney(Number(preview.total_cost)) : 'Belum lengkap'}</p>
      <p className="text-muted">Belum termasuk gas, gaji, sewa, dan biaya operasional lainnya.</p>
    </div>
    <p>Resep untuk {format(preview.servings)} porsi · Revisi {session.revision}</p>
    <details><summary className="hpp-chat-evidence">Sumber jumlah porsi</summary>
      <p>{labels[preview.servings_source]}</p>{preview.servings_evidence && <p>{preview.servings_evidence}</p>}</details>
    {preview.notes && <p>{preview.notes}</p>}
    {preview.new_product && <p>Menu baru akan disimpan nonaktif. Atur harga jual dan aktifkan melalui Menu.</p>}
    <ol className="hpp-chat-review-lines">{preview.lines.map((line, index) => <li key={index}>
      <div className="hpp-chat-review-line-heading"><h3>{line.name}{line.is_optional && ' (opsional)'}</h3><span>{line.line_cost === null ? 'Belum lengkap' : hppMoney(Number(line.line_cost))}</span></div>
      <p>{format(line.quantity)} {line.unit} per porsi · {actions[line.action]}</p>
      {line.basis === 'batch' && <p className="text-muted">Dari {format(line.input_quantity)} {line.input_unit} per batch, dibagi {format(preview.servings)} porsi.</p>}
      <p>Takaran: {labels[line.quantity_source]}. Harga: {labels[line.price_source]}.</p>
      <p className="text-muted">Biaya satuan: {line.unit_cost === null ? 'Belum diisi' : cost(line.unit_cost) + ' Rp/' + line.unit}.</p>
      {line.old_unit_cost !== null && <p>Sebelumnya {cost(line.old_unit_cost)} Rp/{line.unit}.</p>}
      {line.action !== 'reuse' && line.buy_price !== null && <p>Pembelian: {hppMoney(Number(line.buy_price))} untuk {format(line.buy_qty)} {line.unit}.</p>}
      {line.purchase_description && <p className="text-muted">Dari {line.purchase_description}.</p>}
      {line.affected_products.length > 0 && <p>Harga baru juga mengubah HPP: {line.affected_products.join(', ')}.</p>}
      {line.notes && <p className="text-muted">{line.notes}</p>}
      {(line.quantity_evidence || line.price_evidence) && <details><summary className="hpp-chat-evidence">Lihat sumber dari cerita</summary><p className="hpp-chat-quote">{[line.quantity_evidence, line.price_evidence].filter(Boolean).join('\n')}</p></details>}
    </li>)}</ol>
    {preview.missing.length > 0 && <div><h3>Masih perlu dilengkapi</h3><ul className="hpp-chat-missing">{preview.missing.map((item, index) => <li key={index}>{item}</li>)}</ul><p>Lengkapi atau koreksi lewat obrolan.</p></div>}
    <details><summary className="hpp-chat-evidence">Lihat rumus HPP</summary><p>Biaya satuan = total harga beli ÷ jumlah beli dalam satuan bahan. Biaya bahan = takaran per porsi × biaya satuan. HPP = jumlah biaya bahan wajib. Takaran batch dibagi jumlah porsi. Biaya satuan disimpan hingga 8 desimal; total tampilan dibulatkan ke 2 desimal.</p></details>
    {session.status !== 'applied' && <div className="hpp-chat-approval">
      {preview.is_estimated && <p>Harga atau takaran perkiraan tetap diberi label estimasi setelah disimpan.</p>}
      <label className="hpp-chat-choice"><input type="checkbox" checked={confirmed} disabled={blocked} onChange={event => onConfirmed(event.target.checked)} /><span>Bahan, harga, takaran, dan jumlah porsi sudah sesuai.</span></label>
      {preview.replaces_recipe && <label className="hpp-chat-choice"><input type="checkbox" checked={replacing} disabled={blocked} onChange={event => onReplacing(event.target.checked)} /><span>Ganti resep aktif produk ini dengan resep di atas.</span></label>}
      <button className="hpp-button hpp-primary" disabled={blocked || !confirmed || (preview.replaces_recipe && !replacing)} onClick={onApprove}>{busy ? 'Menyimpan...' : preview.replaces_recipe ? 'Approve dan ganti resep' : 'Approve dan simpan resep'}</button>
      {hasUnsent && <p>Kirim pesan yang belum diproses dulu sebelum approve.</p>}
      <p className="text-muted">Yang disimpan bahan dan resep. Stok fisik dicatat terpisah di Bahan Baku.</p>
    </div>}
  </div>;
}
