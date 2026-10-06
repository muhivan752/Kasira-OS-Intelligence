import { HppSetup } from './setup';

export default async function HppPage({ searchParams }: { searchParams: Promise<{ product?: string; outlet?: string }> }) {
  const { product, outlet } = await searchParams;
  return <HppSetup initialProduct={typeof product === 'string' ? product : ''} initialOutlet={typeof outlet === 'string' ? outlet : ''} />;
}
