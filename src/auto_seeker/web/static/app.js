(() => {
  const root = document.querySelector(".collect-progress");
  if (!root) return;
  const bar = document.getElementById("collect-progress-bar");
  const text = document.getElementById("collect-progress-text");
  const poll = async () => {
    try {
      const response = await fetch(root.dataset.statusUrl, {cache: "no-store"});
      const state = await response.json();
      const total = state.pages_requested || 0;
      const completed = state.pages_completed || 0;
      const percent = total ? Math.min(100, completed / total * 100) : 0;
      bar.style.width = `${percent}%`;
      text.textContent = state.stopping
        ? `正在停止… 已完成 ${completed}/${total} 页，匹配 ${state.matched_count} 个职位`
        : `正在采集 ${completed}/${total} 页，匹配 ${state.matched_count} 个职位`;
      if (state.running) setTimeout(poll, 1000);
      else window.location.href = `/jobs?collect_status=${encodeURIComponent(state.status)}`;
    } catch (_) {
      text.textContent = "暂时无法获取采集进度，正在重试…";
      setTimeout(poll, 2000);
    }
  };
  poll();
})();
