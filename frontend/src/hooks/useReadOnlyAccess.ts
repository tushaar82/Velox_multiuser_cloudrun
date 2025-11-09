import { useAppSelector } from '../store/hooks';
import { UserRole } from '../types';

/**
 * Hook to determine if the current user has read-only access
 * Investors have read-only access to accounts they're invited to
 */
export function useReadOnlyAccess(): boolean {
  const { user } = useAppSelector((state) => state.auth);
  return user?.role === UserRole.INVESTOR;
}

/**
 * Hook to check if user can perform trader actions
 * Only traders and admins can modify strategies and execute trades
 */
export function useCanTrade(): boolean {
  const { user } = useAppSelector((state) => state.auth);
  return user?.role === UserRole.TRADER || user?.role === UserRole.ADMIN;
}

/**
 * Hook to check if user is an admin
 */
export function useIsAdmin(): boolean {
  const { user } = useAppSelector((state) => state.auth);
  return user?.role === UserRole.ADMIN;
}
