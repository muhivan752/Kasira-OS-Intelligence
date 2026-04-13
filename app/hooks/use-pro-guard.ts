'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser } from '@/app/actions/api';

export function useProGuard(featureName?: string) {
  const [allowed, setAllowed] = useState(false);
  const router = useRouter();

  useEffect(() => {
    async function check() {
      const user = await getCurrentUser();
      if (!user) {
        router.push('/login');
        return;
      }
      const tier = user.subscription_tier || 'starter';
      if (['pro', 'business', 'enterprise'].includes(tier)) {
        setAllowed(true);
      } else {
        const param = featureName ? `?feature=${encodeURIComponent(featureName)}` : '';
        router.push(`/dashboard/pro${param}`);
      }
    }
    check();
  }, [router, featureName]);

  return allowed;
}
