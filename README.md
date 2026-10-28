# AdOff — 安卓去广告

用一根数据线，在 **DNS 层**把广告请求掐断：不 root、不刷机、不改系统。

打开 App 的那一刻，它就已经连不上广告服务器了。

```
python adoff.py           # 菜单式操作，跟着提示走
```

---

## 它做了什么

绝大多数手机广告是通过 **广告 SDK** 拉取的。App 启动时，SDK 会去请求
`pgdt.gtimg.cn`、`ad.oceanengine.com` 这类域名拿广告素材。

AdOff 做的事情很简单：

1. 装一个 AdAway（开源，走系统 VPN 接口，不需要 root）
2. 给它喂一份 **18 万条**的广告域名黑名单
3. AdAway 接管手机的 DNS 解析，黑名单里的域名一律返回「不存在」

SDK 拿不到广告 → 广告位空着 → 你看不到广告。

> DNS 拦截在**请求阶段**就拒绝了，不是等弹出来再关。

---

## 准备工作

### 1. 电脑装 Python

Python 3.10 或更高。Windows 在 [python.org](https://www.python.org/downloads/) 下载，
安装时**一定要勾选 `Add Python to PATH`**。

装好后在终端验证：

```bash
python --version
```

### 2. 手机打开 USB 调试

以小米 / 红米（HyperOS）为例：

1. 设置 → 我的设备 → 全部参数与信息 → 连点「OS 版本」7 次
2. 设置 → 更多设置 → 开发者选项 → 打开「USB 调试」
3. **小米还要额外打开「USB 调试（安全设置）」**，需要登录小米账号并插卡

其他品牌路径类似，搜「开发者选项」就行。

### 3. 连接数据线

插上后手机会弹窗，勾选 **「始终允许」**，点 **「允许」**。

---

## 开始使用

```bash
git clone https://github.com/<your-name>/AdOff.git
cd AdOff
python adoff.py
```

第一次运行会看到菜单：

```
  AdOff — 安卓去广告

  1. 检查手机连接
  2. 输入手机型号
  3. 开始去广告
  4. 验证拦截效果
  5. 还原所有改动
  0. 退出
```

### 推荐顺序

| 步骤 | 做什么 |
|---|---|
| 1 | 检查手机是否连上 |
| 2 | 输入型号（不填则自动读取手机上报的型号） |
| 3 | 开始去广告，按提示走完 |
| 4 | 验证广告域名是否真的被拦截 |

### 如果电脑没有 adb

```bash
python adoff.py --install-adb
```

会自动下载 Google 官方的 platform-tools 并解压到项目目录。

---

## 第 3 步会经历什么

脚本会自动完成：

- 下载 anti-AD 广告域名库，生成 hosts 文件
- 把文件推到手机 `/sdcard/.xlDownload/anti-ad.log`
- 下载并安装 AdAway
- 把 AdAway 加进电池优化白名单（防止被系统杀掉）

然后需要你在手机上点几下（没有 root 时这是唯一可靠的方式）：

1. 打开 AdAway，点右下角 **+**
2. 标签填 `AdOff`
3. 类型选 **文件**
4. 位置选 **内部存储 → .xlDownload → anti-ad.log**
5. 返回后点底部的 **应用**
6. 看到「已成功更新 VPN 配置」就好了

> 为什么文件名是 `.log`？
> 小米的文件选择器会隐藏 `.hosts` 和 `.txt`，只显示它认识的类型。
> 改成 `.log` 才能在列表里看到。

---

## 支持哪些手机

**DNS 拦截对所有安卓手机都有效**，不挑品牌。

型号只影响「系统自带广告组件」的处理：

| 品牌 | 系统广告组件 | 实测状态 |
|---|---|---|
| 小米 / 红米（HyperOS） | `com.miui.systemAdSolution` 可挂起 | ✅ 已实测 |
| 其他品牌 | 不做系统改动，只做 DNS 拦截 | 通用逻辑，未逐台实测 |

想加新品牌？改 `adoff/profiles.py` 里的 `BUILTIN_PROFILES` 即可。

---

## 验证效果

```bash
python adoff.py verify
```

会依次测试几个广告域名：

```
✓ gdt.qq.com 已拦截
✓ pgdt.gtimg.cn 已拦截
✓ ad.oceanengine.com 已拦截
✓ alimama.com 已拦截
✓ 测试域名 4/4 全部被拦截
```

也可以自己在手机上测（需要连电脑）：

```bash
adb shell ping -c 1 gdt.qq.com
```

返回 `unknown host` 就是拦住了。

---

## 常见问题

### 明明显示成功，广告又回来了

**清理后台时把 AdAway 也杀了。** 这时 AdAway 进程可能还活着，
但 VPN 隧道已经断开 —— 看规则数一切正常，实际全放行。

检查：

```bash
adb shell ip addr show | grep tun0
```

有 `tun0` 才算真的在拦截。没的话，打开 AdAway 让它重建隧道。

**彻底解决**：小米/红米去设置里给 AdAway 开「自启动」，省电策略改成「无限制」。

### 某个 App 的广告还在

可能是这三种情况之一：

1. **广告已经缓存在手机里了** —— 断网也显示，清 App 缓存或等过期
2. **App 用了 HTTPDNS / 直连 IP** —— 不走系统 DNS，拦不到（大厂常见）
3. **是 App 自己的推广** —— 会员、优惠券、自家其他 App 的弹窗，不经过广告 SDK

第 3 种可以用 [Gkd](https://github.com/gkd-kit/gkd) 自动点掉，
它靠无障碍服务识别并点击「跳过」按钮。

### 手机提示 VPN 被占用

AdAway 和其他 VPN 类 App（比如某些加速器）不能同时开。
关掉另一个即可。

---

## 还原

```bash
python adoff.py restore
```

会做三件事：

- 恢复被挂起的系统广告组件（`pm unsuspend`）
- 把 AdAway 移出电池优化白名单
- **询问后**才卸载 AdAway

---

## 能拦什么，拦不住什么

| 广告类型 | DNS 层能拦吗 |
|---|---|
| 第三方广告 SDK（穿山甲、优量汇、百度联盟…） | ✅ 能 |
| 广告归因 / 监测域名 | ✅ 能 |
| 推送 SDK 拉取的营销通知 | 部分能 |
| 已缓存的广告素材 | ❌ 不能 |
| 使用 HTTPDNS / 直连 IP 的广告 | ❌ 不能 |
| 和业务共用域名的广告 | ❌ 不能（拦了会坏功能） |
| App 自家推广弹窗 | ❌ 不能，也不该拦 |

**诚实的预期**：接入第三方广告 SDK 的中小 App，效果很明显；
大厂自建的广告体系，DNS 只能拦掉一部分。

---

## 项目结构

```
AdOff/
├── adoff.py              入口
├── adoff/
│   ├── cli.py            菜单与子命令
│   ├── adb.py            adb 封装
│   ├── hosts.py          名单下载与转换
│   ├── adaway.py         AdAway 安装、保活、验证
│   ├── system.py         挂起、白名单
│   ├── profiles.py       型号配置
│   ├── restore.py        还原
│   └── ui.py             终端输出
├── data/sdk-domains.txt  广告 SDK 补充域名
└── docs/                 详细说明
```

---

## 免责声明

本项目通过公开的 adb 接口和开源软件（AdAway、anti-AD）工作，
不修改系统分区、不 root、不破解任何付费内容。

只应用于**你自己拥有或有权管理的设备**。

部分广告域名可能同时承载业务功能，如遇到某个 App 功能异常，
请运行 `restore` 还原后再逐步排查。

---

## 参考

- [AdAway](https://github.com/AdAway/AdAway) —— 开源广告拦截器
- [anti-AD](https://github.com/privacy-protection-tools/anti-AD) —— 中文广告域名库
- [Gkd](https://github.com/gkd-kit/gkd) —— 无障碍自动点击
