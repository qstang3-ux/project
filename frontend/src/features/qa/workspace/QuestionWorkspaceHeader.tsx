interface QuestionWorkspaceHeaderProps {
  title: string;
  selectedSourceCount: number;
}

export function QuestionWorkspaceHeader({ title, selectedSourceCount }: QuestionWorkspaceHeaderProps) {
  return (
    <header className="qa-title">
      <div><span className="qa-eyebrow">智能问数</span><h1>{title}</h1></div>
      <div className="qa-context"><span>只读查询</span><span>{selectedSourceCount} 个数据源</span></div>
    </header>
  );
}
