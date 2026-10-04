import { HppChat } from './setup';

export default async function Page({ searchParams }: { searchParams: Promise<{ product?: string }> }) {
  const { product } = await searchParams;
  return <HppChat initialProduct={product || ''} />;
}
