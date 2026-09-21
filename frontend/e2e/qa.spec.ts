import { expect, test } from '@playwright/test';

test('快捷提问、问题收藏和问答日志形成闭环', async ({ page }) => {
  await page.goto('/qa');
  await page.getByRole('button', { name: '开启新对话' }).click();

  const input = page.getByRole('textbox', { name: '问题输入' });
  await page.getByRole('button', { name: '打开快捷提问' }).click();
  const quickPanel = page.locator('.quick-question-panel');
  await quickPanel.getByRole('button', { name: /2026年商业目标最高的5个经营单元/ }).click();
  await expect(input).toHaveValue('2026年商业目标最高的5个经营单元');
  await expect(quickPanel).toBeHidden();

  await page.getByRole('button', { name: '发送' }).click();
  await expect(page.getByText('北京代表处以7,950万元居首')).toBeVisible({ timeout: 10_000 });
  await page.getByRole('button', { name: '收藏问题' }).click();
  await expect(page.getByText('已收藏到快捷提问')).toBeVisible();

  await page.getByRole('button', { name: '打开快捷提问' }).click();
  await quickPanel.getByRole('tab', { name: '收藏' }).click();
  await expect(quickPanel.getByRole('button', { name: '2026年商业目标最高的5个经营单元', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '关闭快捷提问' }).click();

  await page.getByRole('menuitem', { name: '问答日志' }).click();
  await expect(page.getByRole('heading', { name: '问答日志' })).toBeVisible();
  const logScrollLayout = await page.evaluate(() => {
    const pageContent = document.querySelector<HTMLElement>('.app-content');
    const tableBody = document.querySelector<HTMLElement>('.qa-log-table .ant-table-body');
    const pagination = document.querySelector<HTMLElement>('.qa-log-pagination');
    if (!pageContent || !tableBody || !pagination) throw new Error('缺少问答日志滚动容器');
    return {
      pageClientHeight: pageContent.clientHeight,
      pageScrollHeight: pageContent.scrollHeight,
      tableOverflowY: getComputedStyle(tableBody).overflowY,
      paginationInsideTableBody: tableBody.contains(pagination),
    };
  });
  expect(logScrollLayout.pageScrollHeight).toBe(logScrollLayout.pageClientHeight);
  expect(logScrollLayout.tableOverflowY).toBe('scroll');
  expect(logScrollLayout.paginationInsideTableBody).toBe(false);
  await expect(page.getByText('2026年商业目标最高的5个经营单元').first()).toBeVisible();
  await page.getByRole('button', { name: /详情/ }).first().click();
  const drawer = page.getByRole('dialog', { name: '问答日志详情' });
  await expect(drawer.getByText('模型调用')).toBeVisible();
  await expect(drawer.getByText('节点轨迹')).toBeVisible();
  await expect(drawer.getByText('经营分析模型')).toBeVisible();
});

test('创建会话并完成一次智能问数', async ({ page }) => {
  await page.goto('/qa');
  const newConversationButton = page.getByRole('button', { name: '开启新对话' });
  await expect(newConversationButton).toBeVisible();
  await newConversationButton.click();
  await page.getByRole('button', { name: '2026年商业目标最高的5个经营单元' }).click();
  await page.getByRole('button', { name: '发送' }).click();
  await expect(page.getByRole('button', { name: '停止当前问数' })).toBeVisible();
  await expect(page.getByText('北京代表处以7,950万元居首')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText('已完成', { exact: true })).toHaveClass(/assistant-status-completed/);
  expect(await page.locator('.answer-summary').evaluate((element) => getComputedStyle(element, '::before').content)).toBe('none');
  await expect(page.getByText('安全校验通过')).toBeVisible();
  await expect(page.getByLabel('答案要点')).toContainText('北京代表处');
  await expect(page.getByText('继续探索')).toBeVisible();
  await page.getByText('为什么是这个答案').click();
  await expect(page.getByText('查询对象')).toBeVisible();
  const firstResultRow = page.locator('.result-section tbody .ant-table-row').first();
  await firstResultRow.hover();
  await expect(firstResultRow).toHaveClass(/result-row-highlighted/);
  const lineChartButton = page.getByRole('button', { name: '切换为折线图' });
  await lineChartButton.click();
  await expect(lineChartButton).toHaveAttribute('aria-pressed', 'true');
  const pieChartButton = page.getByRole('button', { name: '切换为饼图' });
  await pieChartButton.click();
  await expect(pieChartButton).toHaveAttribute('aria-pressed', 'true');

  const conversation = page.locator('.qa-scroll');
  await conversation.hover();
  await page.mouse.wheel(0, -1200);
  await expect(page.getByRole('button', { name: '回到底部' })).toBeVisible();
  const scrollMetrics = await page.evaluate(() => {
    const outer = document.querySelector('.app-content');
    const conversationElement = document.querySelector('.qa-scroll');
    if (!outer || !conversationElement) throw new Error('缺少滚动容器');
    return {
      outerClientHeight: outer.clientHeight,
      outerScrollHeight: outer.scrollHeight,
      conversationClientHeight: conversationElement.clientHeight,
      conversationScrollHeight: conversationElement.scrollHeight,
    };
  });
  expect(scrollMetrics.outerScrollHeight).toBe(scrollMetrics.outerClientHeight);
  expect(scrollMetrics.conversationScrollHeight).toBeGreaterThan(scrollMetrics.conversationClientHeight);
  await page.getByRole('button', { name: '回到底部' }).click();
  await expect.poll(() => page.evaluate(() => {
    const conversation = document.querySelector('.qa-scroll');
    if (!conversation) return false;
    return conversation.scrollHeight - conversation.scrollTop - conversation.clientHeight < 2;
  })).toBe(true);
});

test('常用桌面宽度下回答卡与图表不会横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 720 });
  await page.goto('/qa');
  await page.getByRole('button', { name: '开启新对话' }).click();
  await page.getByRole('button', { name: '2026年商业目标最高的5个经营单元' }).click();
  await page.getByRole('button', { name: '发送' }).click();
  await expect(page.getByText('北京代表处以7,950万元居首')).toBeVisible({ timeout: 10_000 });
  await expect(page.locator('.chart-canvas canvas')).toBeVisible();

  for (const viewport of [
    { width: 1024, height: 720 },
    { width: 1280, height: 720 },
    { width: 1440, height: 900 },
  ]) {
    await page.setViewportSize(viewport);
    await expect.poll(() => page.evaluate(() => {
      const selectors = ['.assistant-card', '.assistant-card .ant-card-body', '.chart-section', '.chart-canvas', '.echarts-for-react'];
      return selectors.flatMap((selector) => {
        const element = document.querySelector<HTMLElement>(selector);
        if (!element) throw new Error(`缺少布局元素：${selector}`);
        return element.scrollWidth > element.clientWidth + 1
          ? [{ selector, clientWidth: element.clientWidth, scrollWidth: element.scrollWidth }]
          : [];
      });
    }), { message: `${String(viewport.width)}x${String(viewport.height)} 下不应出现横向溢出` }).toEqual([]);
    const chartBounds = await page.evaluate(() => {
      const root = document.querySelector<HTMLElement>('.echarts-for-react');
      const canvas = root?.querySelector('canvas');
      if (!root || !canvas) throw new Error('缺少图表画布');
      const rootRect = root.getBoundingClientRect();
      const canvasRect = canvas.getBoundingClientRect();
      return { rootWidth: rootRect.width, canvasWidth: canvasRect.width, rootRight: rootRect.right, canvasRight: canvasRect.right };
    });
    expect(chartBounds.canvasWidth).toBeLessThanOrEqual(chartBounds.rootWidth + 1);
    expect(chartBounds.canvasRight).toBeLessThanOrEqual(chartBounds.rootRight + 1);
    const viewportWidths = await page.evaluate(() => ({ clientWidth: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth }));
    expect(viewportWidths.scrollWidth).toBe(viewportWidths.clientWidth);
  }
});

test('问题可编辑为新分支，回答可重新生成并查看版本', async ({ page }) => {
  await page.goto('/qa');
  await page.getByRole('button', { name: '开启新对话' }).click();
  const input = page.getByRole('textbox', { name: '问题输入' });
  await input.fill('2026年商业目标最高的5个经营单元');
  await page.getByRole('button', { name: '发送' }).click();
  await expect(page.getByText('北京代表处以7,950万元居首')).toBeVisible({ timeout: 10_000 });

  const firstTurn = page.locator('.message-turn').filter({ hasText: '2026年商业目标最高的5个经营单元' }).first();
  await firstTurn.getByRole('button', { name: '编辑问题' }).click();
  const editorArea = page.locator('.user-message-editor');
  const editor = editorArea.getByRole('textbox', { name: '编辑问题' });
  await editor.fill('2026年各产品线收入占比');
  await editorArea.getByRole('button', { name: '重新发送' }).click();
  await expect(page.getByText('2026年各产品线收入占比')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText('北京代表处以7,950万元居首')).toBeVisible();

  await page.getByRole('button', { name: '重新生成回答' }).last().click();
  await expect(page.getByText(/重新生成版本/)).toBeVisible({ timeout: 10_000 });
  await page.getByRole('button', { name: '查看回答版本' }).last().click();
  const versions = page.getByRole('dialog', { name: '回答版本' });
  await expect(versions.getByText('版本 1')).toBeVisible();
  await expect(versions.getByText('版本 2')).toBeVisible();
  await expect(versions.getByText('当前版本')).toBeVisible();
  await versions.getByRole('button', { name: '关闭' }).click();

  const pngDownloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出图表 PNG' }).last().click();
  const pngDownload = await pngDownloadPromise;
  expect(pngDownload.suggestedFilename()).toMatch(/\.png$/);

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出 CSV' }).last().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^execution-.+\.csv$/);
});

test('关键页面保持无控制台错误并支持键盘与弹窗保护', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') {
      const location = message.location();
      consoleErrors.push(`${message.text()} @ ${location.url}:${String(location.lineNumber)}`);
    }
  });

  await page.setViewportSize({ width: 800, height: 720 });
  await page.goto('/qa');
  const input = page.getByRole('textbox', { name: '问题输入' });
  await input.fill('第一行');
  await input.press('Shift+Enter');
  await input.pressSequentially('第二行');
  await expect(input).toHaveValue('第一行\n第二行');
  expect(await input.evaluate((element) => getComputedStyle(element).userSelect)).toBe('text');

  await page.goto('/settings/application');
  await expect(page.getByRole('heading', { name: '应用配置' })).toBeVisible();
  expect(await page.getByRole('heading', { name: '应用配置' }).evaluate((element) => getComputedStyle(element).userSelect)).toBe('none');
  const applicationScroll = await page.evaluate(() => {
    const pageContent = document.querySelector('.app-content');
    if (!pageContent) throw new Error('缺少应用配置滚动容器');
    return {
      contentClientHeight: pageContent.clientHeight,
      contentScrollHeight: pageContent.scrollHeight,
      contentClientWidth: pageContent.clientWidth,
      contentScrollWidth: pageContent.scrollWidth,
      documentClientHeight: document.documentElement.clientHeight,
      documentScrollHeight: document.documentElement.scrollHeight,
      documentClientWidth: document.documentElement.clientWidth,
      documentScrollWidth: document.documentElement.scrollWidth,
    };
  });
  expect(applicationScroll.contentScrollHeight).toBeGreaterThanOrEqual(applicationScroll.contentClientHeight);
  expect(applicationScroll.contentScrollWidth).toBe(applicationScroll.contentClientWidth);
  expect(applicationScroll.documentScrollHeight).toBe(applicationScroll.documentClientHeight);
  expect(applicationScroll.documentScrollWidth).toBe(applicationScroll.documentClientWidth);
  const speechSwitch = page.getByRole('switch', { name: '语音播放开关' });
  const firstAutoSave = page.waitForResponse((response) => response.url().endsWith('/api/v1/application-config') && response.request().method() === 'PUT');
  await speechSwitch.click();
  expect((await firstAutoSave).status()).toBe(200);
  await expect(page.getByText('已自动保存')).toBeVisible();
  expect(consoleErrors).toEqual([]);
  const restoreAutoSave = page.waitForResponse((response) => response.url().endsWith('/api/v1/application-config') && response.request().method() === 'PUT');
  await speechSwitch.click();
  expect((await restoreAutoSave).status()).toBe(200);
  await expect(page.getByText('已自动保存')).toBeVisible();
  expect(consoleErrors).toEqual([]);
  await page.getByRole('button', { name: '编辑对话开场白' }).click();
  await expect(page.getByRole('dialog', { name: '对话开场白' })).toBeVisible();
  await page.getByRole('button', { name: /完\s*成\s*编\s*辑/ }).click();
  await expect(page.getByRole('button', { name: '保存配置' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '取消修改' })).toHaveCount(0);
  await page.getByRole('button', { name: '编辑常问设置' }).click();
  await expect(page.getByRole('dialog', { name: '常问设置' })).toBeVisible();
  await page.getByRole('button', { name: /完\s*成/ }).click();

  await page.getByRole('button', { name: '打开模型配置' }).click();
  await expect(page.getByRole('dialog', { name: /模型配置/ })).toBeVisible();
  const createModelButton = page.getByRole('button', { name: '新增模型' });
  await expect(createModelButton).toBeVisible();
  await expect(page.getByRole('region', { name: '智能问数模型配置' })).toBeVisible();
  await createModelButton.click();
  await expect(page.getByLabel('接口协议')).toBeVisible();
  await expect(page.getByTitle('Responses API')).toBeVisible();
  await page.getByLabel('配置名称').fill('未保存配置');
  await page.getByRole('dialog', { name: '新增模型' }).getByRole('button', { name: /取\s*消/ }).click();
  await expect(page.locator('.ant-modal-confirm-title', { hasText: '放弃未保存的模型配置？' })).toBeVisible();
  await page.getByRole('button', { name: /继\s*续\s*编\s*辑/ }).click();
  await expect(page.getByRole('dialog', { name: '新增模型' })).toBeVisible();
  await page.getByRole('dialog', { name: '新增模型' }).getByRole('button', { name: /取\s*消/ }).click();
  await page.getByRole('button', { name: /放\s*弃\s*修\s*改/ }).click();

  await page.getByRole('button', { name: '编辑当前模型' }).click();
  const editModelDialog = page.getByRole('dialog', { name: '编辑模型' });
  await expect(editModelDialog.getByText('API Key 已安全保存')).toBeVisible();
  await expect(editModelDialog.getByLabel('新的 API Key')).toHaveCount(0);
  await editModelDialog.getByRole('button', { name: '更换 API Key' }).click();
  await expect(editModelDialog.getByLabel('新的 API Key')).toHaveAttribute('type', 'password');
  await expect(editModelDialog.getByLabel('新的 API Key')).toHaveValue('');
  await editModelDialog.getByRole('button', { name: /^取\s*消$/ }).click();

  await page.goto('/feedback');
  await expect(page.getByRole('heading', { name: '回复校对' })).toBeVisible();
  const widths = await page.evaluate(() => {
    const content = document.querySelector('.app-content');
    if (!content) throw new Error('缺少主内容区');
    return { client: content.clientWidth, scroll: content.scrollWidth };
  });
  expect(widths.scroll).toBe(widths.client);
  expect(consoleErrors).toEqual([]);
});

test('模糊问题可刷新恢复并在同一执行中完成澄清', async ({ page }) => {
  let clarificationRequests = 0;
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().includes('/clarifications')) clarificationRequests += 1;
  });

  await page.goto('/qa');
  await page.getByRole('button', { name: '开启新对话' }).click();
  const input = page.getByRole('textbox', { name: '问题输入' });
  await input.fill('达成情况');
  await page.getByRole('button', { name: '发送' }).click();

  await expect(page.getByText('待补充信息')).toBeVisible();
  await expect(page.getByText('请补充要查询的指标和分析维度。')).toBeVisible();
  await expect(page.getByText('第 1 / 2 轮')).toBeVisible();
  await page.reload();
  await expect(page.getByText('请补充要查询的指标和分析维度。')).toBeVisible();

  await page.getByRole('textbox', { name: '补充信息' }).fill('查询2026年各经营单元商业目标完成率，按完成率升序');
  const submit = page.getByRole('button', { name: '提交并继续' });
  await submit.evaluate((button: HTMLButtonElement) => { button.click(); button.click(); });
  await expect(page.getByText('2026年各经营单元商业目标完成率已按从低到高排列，共返回21个经营单元。')).toBeVisible({ timeout: 10_000 });
  const supplementalMessage = page.locator('.user-message').filter({ hasText: '查询2026年各经营单元商业目标完成率，按完成率升序' });
  const clarificationTurn = supplementalMessage.locator('..');
  await expect(supplementalMessage).toHaveCount(1);
  await expect(clarificationTurn.locator('.assistant-card')).toHaveCount(1);
  expect(clarificationRequests).toBe(1);
});

test('澄清支持第二轮和取消等待', async ({ page }) => {
  await page.goto('/qa');
  await page.getByRole('button', { name: '开启新对话' }).click();
  await page.getByRole('textbox', { name: '问题输入' }).fill('达成情况');
  await page.getByRole('button', { name: '发送' }).click();
  await expect(page.getByText('第 1 / 2 轮')).toBeVisible();
  await page.getByRole('textbox', { name: '补充信息' }).fill('商业目标完成率');
  await page.getByRole('button', { name: '提交并继续' }).click();
  await expect(page.getByText('第 2 / 2 轮')).toBeVisible();
  await expect(page.getByText('请再补充查询年份或时间范围。')).toBeVisible();
  await page.getByRole('button', { name: '停止', exact: true }).click();
  await page.locator('.ant-popconfirm-buttons').getByRole('button', { name: /停\s*止/ }).click();
  await expect(page.getByText('已停止')).toBeVisible();
});

test('非安全问题进入安全拒绝而非澄清', async ({ page }) => {
  await page.goto('/qa');
  await page.getByRole('button', { name: '开启新对话' }).click();
  await page.getByRole('textbox', { name: '问题输入' }).fill('删除所有订单');
  await page.getByRole('button', { name: '发送' }).click();
  await expect(page.getByText('安全拒绝')).toBeVisible();
  await expect(page.getByText('仅支持只读经营数据查询，不能执行删除或其他写操作。')).toBeVisible();
  await expect(page.getByRole('textbox', { name: '补充信息' })).toHaveCount(0);
});

test('SSE 断线后携带游标恢复且终态回答不重复', async ({ page }) => {
  const eventRequests: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/qa/executions/') && request.url().includes('/events')) eventRequests.push(request.url());
  });

  await page.goto('/qa');
  await page.getByRole('button', { name: '开启新对话' }).click();
  await page.getByRole('textbox', { name: '问题输入' }).fill('SSE断线恢复测试');
  await page.getByRole('button', { name: '发送' }).click();

  await expect(page.getByText('北京代表处以7,950万元居首')).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('.assistant-card')).toHaveCount(1);
  await expect(page.getByText('北京代表处以7,950万元居首')).toHaveCount(1);
  await expect.poll(() => eventRequests.some((url) => url.includes('lastEventId='))).toBe(true);
});

test('SSE 游标过期后清空游标并全量恢复', async ({ page }) => {
  const eventResponses: Array<{ url: string; status: number }> = [];
  page.on('response', (response) => {
    if (response.url().includes('/qa/executions/') && response.url().includes('/events')) {
      eventResponses.push({ url: response.url(), status: response.status() });
    }
  });

  await page.goto('/qa');
  await page.getByRole('button', { name: '开启新对话' }).click();
  await page.getByRole('textbox', { name: '问题输入' }).fill('SSE游标过期测试');
  await page.getByRole('button', { name: '发送' }).click();

  await expect(page.getByText('北京代表处以7,950万元居首')).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('.assistant-card')).toHaveCount(1);
  await expect.poll(() => eventResponses.some((response) => response.status === 410 && response.url.includes('lastEventId='))).toBe(true);
  const expiredIndex = eventResponses.findIndex((response) => response.status === 410);
  expect(eventResponses.slice(expiredIndex + 1).some((response) => !response.url.includes('lastEventId='))).toBe(true);
});

test('宽屏问答区扩展且模型配置在窄屏内保持场景选择布局', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 900 });
  await page.goto('/qa');
  await expect(page.locator('.qa-scroll')).toBeVisible();
  const qaLayout = await page.evaluate(() => {
    const scroll = document.querySelector<HTMLElement>('.qa-scroll');
    const composer = document.querySelector<HTMLElement>('.composer-wrap');
    if (!scroll || !composer) throw new Error('缺少问答布局容器');
    const scrollStyle = getComputedStyle(scroll);
    const composerStyle = getComputedStyle(composer);
    return {
      conversationWidth: scroll.clientWidth - Number.parseFloat(scrollStyle.paddingLeft) - Number.parseFloat(scrollStyle.paddingRight),
      composerWidth: composer.clientWidth - Number.parseFloat(composerStyle.paddingLeft) - Number.parseFloat(composerStyle.paddingRight),
    };
  });
  expect(qaLayout.conversationWidth).toBeGreaterThanOrEqual(1180);
  expect(qaLayout.composerWidth).toBeGreaterThanOrEqual(1180);

  await page.setViewportSize({ width: 1024, height: 720 });
  await page.goto('/settings/application');
  await page.getByRole('button', { name: '打开模型配置' }).click();
  await expect(page.locator('.model-scene-config')).toBeVisible();
  const cardLayout = await page.evaluate(() => {
    const pageContent = document.querySelector<HTMLElement>('.app-content');
    const scene = document.querySelector<HTMLElement>('.model-scene-config');
    if (!pageContent || !scene) throw new Error('缺少模型场景配置容器');
    return {
      pageClientWidth: pageContent.clientWidth,
      pageScrollWidth: pageContent.scrollWidth,
      sceneClientWidth: scene.clientWidth,
      sceneScrollWidth: scene.scrollWidth,
    };
  });
  expect(cardLayout.pageScrollWidth).toBe(cardLayout.pageClientWidth);
  expect(cardLayout.sceneScrollWidth).toBe(cardLayout.sceneClientWidth);
  await expect(page.getByRole('region', { name: '智能问数模型配置' })).toBeVisible();
  await expect(page.getByRole('region', { name: /模型 / })).toBeVisible();
  await expect(page.getByRole('button', { name: '编辑当前模型' })).toBeVisible();
  await expect(page.getByText('sk-****demo')).toHaveCount(0);
});
