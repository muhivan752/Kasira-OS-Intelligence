import { HppSetup } from './setup';

export default async function HppPage({ searchParams }: { searchParams: Promise<{ product?: string }> }) {
  const { product } = await searchParams;
  return <HppSetup initialProduct={typeof product === 'string' ? product : ''} />;
}
