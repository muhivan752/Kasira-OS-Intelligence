import { HppChat } from './setup';

export default async function Page({ searchParams }: { searchParams: Promise<{ product?: string; outlet?: string }> }) {
  const { product, outlet } = await searchParams;
  return <HppChat initialProduct={product || ''} initialOutlet={outlet} />;
}
