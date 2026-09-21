export function chartPngFilename(title?: string | null): string {
  const safeTitle = (title ?? '经营分析图表').replace(/[\\/:*?"<>|]/g, '-').trim();
  return `${safeTitle || '经营分析图表'}.png`;
}
