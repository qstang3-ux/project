export async function enableMocking(): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK !== 'true') return;
  const { worker } = await import('./browser');
  await worker.start({ onUnhandledRequest: 'bypass', quiet: true });
}
