// H5 E2E: 覆盖“注册/建档/投喂/选择奶粉/喂奶设置/数据页/退出登录”关键路径
import { test, expect } from '@playwright/test';
import fs from 'node:fs';

function genPhone() {
  // 生成 11 位中国手机号：13 + 9 位（满足前端正则 ^1[3-9]\\d{9}$）
  const t = Date.now().toString();
  return '13' + t.slice(-9);
}

async function waitForHash(page, includes, timeout = 15000) {
  // uni-h5 某些场景下 URL hash 可能不更新（内部路由为准），因此同时用 getCurrentPages() 兜底。
  const target = String(includes || '').replace(/^#/, '').replace(/^\//, '');
  await page.waitForFunction(
    ({ includes, target }) => {
      try {
        if (typeof location !== 'undefined' && String(location.hash || '').includes(includes)) return true;
        if (typeof getCurrentPages === 'function') {
          const pages = getCurrentPages() || [];
          const last = pages[pages.length - 1];
          const route = (last && (last.route || last.$page?.route)) || '';
          return typeof route === 'string' && route.includes(target);
        }
      } catch {}
      return false;
    },
    { includes, target },
    { timeout }
  );
}

// 默认 30s 不足以覆盖真实浏览器 channel 启动 + uni-h5 首屏加载
test.describe.configure({ mode: 'serial', timeout: 180000 });

// 兼容本机没有把 Chrome 安装在 /Applications 的情况（例如放在外挂盘 tools/）。
// 优先走环境变量，便于 CI/他人机器覆盖。
function pickChromeBin() {
  const candidates = [
    process.env.CHROME_BIN,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ].filter(Boolean);
  for (const p of candidates) {
    try {
      if (fs.existsSync(p)) return p;
    } catch {}
  }
  return null;
}

const CHROME_BIN = pickChromeBin();

test.use({
  // 使用系统 Chrome（executablePath），避免依赖 Playwright 自带浏览器下载状态
  launchOptions: CHROME_BIN ? { executablePath: CHROME_BIN } : {},
  viewport: { width: 390, height: 844 }
});

test('H5 关键用户旅程', async ({ page }) => {
  const base = 'http://127.0.0.1:5173';
  const phone = genPhone();
  const password = 'pass1234';
  let babyId = null;

  await page.goto(`${base}/#/pages/login/index`, { waitUntil: 'domcontentloaded' });
  await waitForHash(page, '/pages/login/index');

  // 登录页基础可见
  await expect(page.getByText('奶宝')).toBeVisible();

  // 去注册
  await page.getByText('立即注册').click();
  await waitForHash(page, '/pages/register/index');

  // 注册
  // uni-h5 会把 <input> 编译成 <uni-input> + 内部真实 input（placeholder 不以 attribute 形式存在）
  await page.locator('input.uni-input-input[type="number"]').first().fill(phone);
  await page.locator('input.uni-input-input[type="text"]').first().fill('E2E');
  await page.locator('input.uni-input-input[type="password"]').nth(0).fill(password);
  await page.locator('input.uni-input-input[type="password"]').nth(1).fill(password);

  // 注册按钮（避免点到顶部标题）
  await page.waitForSelector('uni-button.register-btn:not([disabled])', { timeout: 15000 });
  await page.locator('uni-button.register-btn').click();

  // 注册后：home 或 baby-info
  await page.waitForFunction(
    () => location.hash.includes('/pages/home/index') || location.hash.includes('/pages/baby-info/index'),
    null,
    { timeout: 20000 }
  );

  // 为了减少跨端差异（尤其是 H5 picker 交互），E2E 直接用 API 建档，UI 流程从首页开始覆盖
  await page.waitForFunction(() => typeof uni !== 'undefined' && !!uni.getStorageSync('token'), null, { timeout: 15000 });
  babyId = await page.evaluate(async () => {
    const token = uni.getStorageSync('token');
    const res = await fetch('/api/babies', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        nickname: '元宝',
        avatar_url: '/static/avatars/avatar_1.png',
        birth_date: '2025-01-01',
        birth_time: '12:00:00',
        gender: 'male',
        current_weight: 4.5,
        current_height: 55,
      }),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`create baby failed: ${res.status} ${t}`);
    }
    const data = await res.json();
    const babyId = data?.baby?.id ?? null;
    uni.reLaunch({ url: '/pages/home/index' });
    return babyId;
  });
  await waitForHash(page, '/pages/home/index', 20000);

  // 首页可见 & 投喂（避免提示文案里也包含“投喂”导致 strict 模式冲突）
  await expect(page.locator('.feed-button-large')).toBeVisible();
  await page.locator('.feed-button-large').click();
  await expect(page.locator('.undo-toast')).toBeVisible({ timeout: 20000 });

  // 科学顾问回归：分钟级频繁喂奶必须给出明确警示（避免“警示但正文仍说正常”的误导）
  // 这里直接用 API 追加两条记录，避免依赖 uni.showModal 的 E2E 交互细节。
  await page.evaluate(async ({ babyId }) => {
    if (!babyId) throw new Error('missing babyId');
    const token = uni.getStorageSync('token');
    for (let i = 0; i < 2; i += 1) {
      const res = await fetch('/api/feedings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          baby_id: Number(babyId),
          amount: 100,
        }),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`create feeding failed: ${res.status} ${t}`);
      }
      await res.json();
    }
  }, { babyId });

  await page.goto(`${base}/#/pages/home/index`, { waitUntil: 'domcontentloaded' });
  await waitForHash(page, '/pages/home/index', 20000);
  // 频繁喂奶提示：收敛到首页状态 pill（更像产品，而不是每页一个提示框）
  await expect(page.locator('.health-pill-text')).toContainText('记录过密', { timeout: 20000 });

  // 打开“今日喂奶记录”抽屉：列表不应空白（历史回归）
  await page.locator('.ft24-track').first().click();
  await expect(page.getByText('今日喂奶记录')).toBeVisible({ timeout: 20000 });
  await expect(page.locator('.today-item').first()).toBeVisible({ timeout: 20000 });
  // 回归：未左滑时，不应露出“编辑/删除”操作区（避免与内容重叠）
  await expect(page.locator('.today-swipe-actions')).toHaveCount(0);
  await page.getByText('关闭').click();
  await waitForHash(page, '/pages/home/index', 20000);

  // 宝宝资料：更换宝宝头像（覆盖 avatar-select 全链路）
  await page.locator('.baby-avatar-large').click();
  await waitForHash(page, '/pages/baby-info/index', 20000);
  await page.locator('.baby-avatar').click();
  await waitForHash(page, '/pages/avatar-select/index', 20000);
  await expect(page.getByText('选择头像')).toBeVisible();
  await page.locator('.avatar-item').first().click();
  await page.locator('uni-button.confirm-btn').click();
  await waitForHash(page, '/pages/baby-info/index', 20000);

  // 回归：体重/身高编辑弹窗输入不应“点一下就消失”（历史 bug）
  await page.locator('.info-item', { hasText: '体重' }).click();
  await expect(page.getByText('编辑体重')).toBeVisible();
  await page.locator('.edit-modal-content input.uni-input-input').first().fill('4.8');
  await expect(page.getByText('编辑体重')).toBeVisible();
  await page.locator('.edit-modal-content uni-button.confirm-btn').click();

  await page.goBack();
  await waitForHash(page, '/pages/home/index', 20000);

  // 入口收敛：菜单只进入“设置”，再下钻到具体功能
  await page.locator('.menu-icon').click();
  await waitForHash(page, '/pages/settings/index', 20000);
  await page.getByText('奶粉').click();
  await waitForHash(page, '/pages/formula-select/index', 20000);

  await expect(page.getByText('购买偏好')).toBeVisible();
  await page.locator('.brand-cell').first().click();
  await page.waitForSelector('uni-button.formula-save-btn:not([disabled])', { timeout: 20000 });
  await page.locator('uni-button.formula-save-btn').click();
  // 从“设置 -> 奶粉”进入，保存后应回到设置页
  await waitForHash(page, '/pages/settings/index', 20000);

  // 再次切换到另一个品牌：应提示开启 7 天转奶期（交替喂次，不混合）
  await page.getByText('奶粉').click();
  await waitForHash(page, '/pages/formula-select/index', 20000);
  await page.locator('.brand-cell').nth(1).click();
  await page.waitForSelector('uni-button.formula-save-btn:not([disabled])', { timeout: 20000 });
  await page.locator('uni-button.formula-save-btn').click();
  await expect(page.getByText('开始转奶期？')).toBeVisible({ timeout: 20000 });
  await page.getByText('开始 7 天转奶').click();
  await waitForHash(page, '/pages/settings/index', 20000);

  // 回到首页：应展示转奶 pill & 投喂按钮旧/新标记
  await page.goBack();
  await waitForHash(page, '/pages/home/index', 20000);
  await expect(page.locator('.weaning-pill-text')).toContainText('转奶', { timeout: 20000 });
  await expect(page.locator('.feed-badge-text')).toBeVisible({ timeout: 20000 });

  // 再进设置页继续后续流程
  await page.locator('.menu-icon').click();
  await waitForHash(page, '/pages/settings/index', 20000);

  // 投喂偏好：选择并保存（高价值低风险能力补齐回归）
  await page.getByText('投喂偏好').click();
  await waitForHash(page, '/pages/preference/index', 20000);
  await expect(page.getByText('投喂默认量')).toBeVisible();
  await page.locator('.seg', { hasText: '偏多' }).click();
  await page.waitForSelector('uni-button.save-btn:not([disabled])', { timeout: 20000 });
  await page.locator('uni-button.save-btn').click();
  await expect(page.locator('uni-button.save-btn')).toContainText('已保存', { timeout: 20000 });
  await page.goBack();
  await waitForHash(page, '/pages/settings/index', 20000);

  // 喂奶设置（修改并保存）
  await page.getByText('喂奶间隔').click();
  await waitForHash(page, '/pages/feeding-settings/index', 20000);

  // 点几个数字（可能不唯一，这里用 contains 文本定位）
  await page.locator('.number-item', { hasText: '2' }).first().click();
  await page.locator('.number-item', { hasText: '6' }).first().click();

  await page.locator('.save-btn').click();

  // 返回设置页
  await page.goBack();
  await waitForHash(page, '/pages/settings/index', 20000);

  // 常见问题：帮助入口可用（内容可见）
  await page.getByText('常见问题').click();
  await waitForHash(page, '/pages/help/index', 20000);
  await expect(page.getByText('推荐奶量是怎么来的？')).toBeVisible();
  await page.goBack();
  await waitForHash(page, '/pages/settings/index', 20000);

  // 数据详情
  await page.getByText('数据详情').click();
  await waitForHash(page, '/pages/data-detail/index', 20000);
  await expect(page.locator('.dd-help')).toBeVisible();

  // 回归：数据页录入体重/身高弹窗输入不应“点一下就消失”
  const t = new Date();
  const todayMD = `${String(t.getMonth() + 1).padStart(2, '0')}.${String(t.getDate()).padStart(2, '0')}`;
  const todayRow = page
    .locator('.record-cell')
    .filter({ has: page.locator('.record-date', { hasText: todayMD }) })
    .first();
  await todayRow.click();
  await expect(page.locator('.edit-modal-content')).toBeVisible();
  await page.locator('.edit-modal-content input.uni-input-input').first().fill('4.9');
  await expect(page.locator('.edit-modal-content')).toBeVisible();
  await page.locator('.edit-modal-content uni-button.confirm-btn').click();

  // 回到设置页，继续下钻到数据报告
  await page.goBack();
  await waitForHash(page, '/pages/settings/index', 20000);

  await page.getByText('数据报告').click();
  await waitForHash(page, '/pages/report/index', 20000);
  await expect(page.locator('.range-card').getByText('生成报告')).toBeVisible();
  await page.locator('.range-card').getByText('生成报告').click();
  await expect(page.getByText('每日明细')).toBeVisible({ timeout: 20000 });

  // 退出登录
  await page.goBack();
  await waitForHash(page, '/pages/settings/index', 20000);
  await page.locator('.settings-page .avatar').first().click();
  await waitForHash(page, '/pages/account/index', 20000);

  // 账号资料：一层完成编辑（昵称/头像）
  const nick = `E2E_${Date.now()}`;
  await page.locator('.account-page .cell.tappable').first().click();
  await expect(page.getByText('账号资料')).toBeVisible({ timeout: 20000 });
  await page.locator('input.uni-input-input[type="text"]').first().fill(nick);
  await page.locator('.avatar-item').nth(1).click();
  await page.locator('uni-button.primary-btn:not([disabled])').click();
  await expect(page.getByText('账号资料')).toBeHidden({ timeout: 20000 });
  await expect(page.locator('.account-page .cell.tappable .cell-title').first()).toContainText(nick);

  await page.getByText('退出登录').click();
  await waitForHash(page, '/pages/login/index', 20000);

  // 重新登录（覆盖登录链路）
  await page.locator('input.uni-input-input[type="number"]').first().fill(phone);
  await page.locator('input.uni-input-input[type="password"]').first().fill(password);
  await page.waitForSelector('uni-button.login-btn:not([disabled])', { timeout: 15000 });
  await page.locator('uni-button.login-btn').click();
  await waitForHash(page, '/pages/home/index', 20000);

  await page.screenshot({ path: '/tmp/naibao-e2e.png', fullPage: true });
});
