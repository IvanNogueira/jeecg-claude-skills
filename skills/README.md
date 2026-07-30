# JeecgBoot Skills — AI 驱动 · 一句话生成全套工件

> 在 **Claude Code** 中，用一句话生成 **代码 · 表单 · 流程 · 报表 · 图表 · 大屏 · 仪表盘**。
> 覆盖 **JeecgBoot 低代码平台** 与 **JimuReport 积木报表** 两大产品的企业级开发全场景。

<p>
  <a href="https://jeecg.com/skills"><img src="https://img.shields.io/badge/官方主页-jeecg.com%2Fskills-1677ff?style=flat-square"></a>
  <a href="https://github.com/jeecgboot/skills"><img src="https://img.shields.io/badge/GitHub-jeecgboot%2Fskills-181717?style=flat-square&logo=github"></a>
  <a href="https://help.jeecg.com/java/ai/skills/skill-comparison"><img src="https://img.shields.io/badge/在线文档-Skills使用指南-13c2c2?style=flat-square"></a>
  <a href="https://www.bilibili.com/video/BV1KKwTzJEbX/"><img src="https://img.shields.io/badge/视频教程-Bilibili-fb7299?style=flat-square&logo=bilibili"></a>
  <img src="https://img.shields.io/badge/License-Apache%202.0-52c41a?style=flat-square">
</p>

|         |                            |
| ------- | -------------------------- |
| **11**  | 官方 Skills 全量上架       |
| **8+**  | 低代码场景一句话直达       |
| **100%**| 开源 · Apache 2.0          |

---

## 🚀 一键安装

> 两种方案任选其一，**幂等运行**，可重复执行。

### 方案 A · Claude Code + DeepSeek v4 一键全栈（推荐 · 无需翻墙）

国内镜像加速，一行命令装齐 **Node.js · Python · Git · Claude Code · JEECG Skills**，并写入 DeepSeek v4 作为模型后端，**跑完即可使用**。

**Windows（PowerShell）**

```powershell
irm https://www.qiaoqiaoyun.com/claude/boot.ps1 | iex
```

> 请在 **PowerShell（建议管理员）** 中执行。若提示脚本被禁，先运行：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**macOS / Linux（Bash / Zsh）**

```bash
curl -fsSL https://www.qiaoqiaoyun.com/claude/install-claude-code.sh | bash
```

> 如需 root 权限，前缀加 `sudo`。

**脚本做了什么**

- 安装 **Node.js 22 LTS · Python 3.12 · Git · Claude Code · JEECG Skills 全量**（华为云 / npmmirror 国内镜像加速）
- 克隆 [gitee.com/jeecg/skills](https://gitee.com/jeecg/skills) 到 `~/.claude/skills/`（已存在则自动 `git pull` 增量更新）
- 写入用户级环境变量 `ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_MODEL=deepseek-v4-pro`
- 幂等运行，重复执行只补缺；重装/换 Key 使用 `--force`

> ⚠️ DeepSeek 按 token 计费，需自备 API Key：[DeepSeek 开放平台 申请 API Key](https://platform.deepseek.com/api_keys)

**安装完成**

```bash
claude
> 帮我生成一个订单管理功能
```

Windows 安装完成后请**新开一个 PowerShell 窗口**让环境变量生效；Linux / macOS 执行 `source ~/.bashrc && claude`。

### 方案 B · 已有 Claude Code · 手工装 JEECG Skills

不跑安装脚本，直接 `git clone` 仓库到 `~/.claude/skills`：

```bash
git clone https://github.com/jeecgboot/skills.git ~/.claude/skills
```

已存在则增量更新：

```bash
cd ~/.claude/skills && git pull
```

**只装部分 Skill（局部复制）**

```bash
# macOS / Linux
cp -r jeecg-codegen ~/.claude/skills/
cp -r jimureport   ~/.claude/skills/

# Windows
xcopy jeecg-codegen %USERPROFILE%\.claude\skills\jeecg-codegen\ /E /I
xcopy jimureport   %USERPROFILE%\.claude\skills\jimureport\   /E /I
```

**前置依赖**

- **Python 3.12+**（部分 Skill 通过 Python 脚本调用后端 API）：[python.org/downloads](https://www.python.org/downloads/)
- 安装后请确保 `python` / `python3` 命令在终端可用（`python --version`）

> 安装后需根据实际项目修改 Skill 中的路径和数据库连接配置，详见各 Skill 的 `SKILL.md`。

---

## 📦 Skills 列表

### JeecgBoot 低代码技能（8）

| #   | 技能                  | 一句话能力                                                                       | 触发关键词                              | 产出物                |
| --- | --------------------- | -------------------------------------------------------------------------------- | --------------------------------------- | --------------------- |
| 1   | **jeecg-codegen**     | 自然语言描述业务需求，自动生成 JeecgBoot 全套 CRUD 代码，支持单表 / 树表 / 主子表 | 代码生成、创建模块、新增功能、加字段    | Java + Vue3 + SQL     |
| 2   | **jeecg-codegen-new** | 新一代 Freemarker 模板驱动代码生成器，速度更快，支持 ERP / Tab / 内嵌子表多种布局 | 代码生成、创建模块、建表、加字段        | Java + Vue3 + SQL     |
| 3   | **jeecg-onlform**     | 元数据驱动，一句话创建 Online 表单，30+ 控件类型，自动同步数据库 + 菜单 SQL       | 创建 Online 表单、在线表单              | Online 表单配置       |
| 4   | **jeecg-onlreport**   | 自然语言生成 SQL 并创建 Online 数据报表，支持字典翻译、分组表头等高级能力          | 创建报表、SQL 报表、数据报表            | Online 报表配置       |
| 5   | **jeecg-desform**     | 按需求描述或截图，自动生成设计器表单 JSON，支持 40+ 控件、主子表、公式计算         | AI 设计表单、按照截图生成表单           | 设计器表单 JSON       |
| 6   | **jeecg-onlchart**    | 一句话生成数据可视化图表，智能推导 X / Y 轴字段，支持柱状图、折线图、饼图等        | 创建图表、柱状图、折线图、饼图          | Online 图表配置       |
| 7   | **jeecg-bpmn**        | 描述审批流程，自动生成 Flowable BPMN 2.0 XML 并部署，支持条件分支、并行、会签      | 创建流程、审批流程、工作流、BPM         | Flowable BPMN 2.0 XML |
| 8   | **jeecg-aiflow**      | 一句话生成 AI 编排流程（AIFlow），模板驱动编排大模型 / 知识库 / 判断等节点         | AI 编排、AIFlow、大模型流程、知识库流程 | AIFlow 编排配置       |

### JimuReport 数据可视化（3）

| #   | 技能                  | 一句话能力                                                                          | 触发关键词                                   | 产出物                  |
| --- | --------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------- | ----------------------- |
| 9   | **jimubi-bigscreen**  | 1920×1080 深色主题，监控室 / 展厅级数据可视化大屏，支持数字翻牌、地图、滚动表格      | 创建大屏、监控大屏、可视化大屏、BI 大屏      | Drag Page 大屏配置      |
| 10  | **jimubi-dashboard**  | 24 列栅格、亮色主题、卡片式设计，日常数据看板和运营统计面板的首选                    | 创建仪表盘、数据看板、运营看板               | Drag Page 仪表盘配置    |
| 11  | **jimureport**        | Excel 设计器风格，支持数据 / 打印 / 分组 / 循环 / 填报全类型报表，可按截图原样还原    | 积木报表、Excel 报表、数据填报、打印报表     | 积木报表配置            |

---

## 💬 使用示例

所有技能都在 Claude Code 对话中**通过自然语言触发**，无需手动调用。

<details open>
<summary><b>示例 · 代码生成（jeecg-codegen）</b></summary>

```
🧑 用户提问
使用代码生成，生成一个订单和订单明细的模块。

🤖 AI 回复
✅ 已通过 jeecg-codegen 生成「订单管理」模块（主子表）。

主表  order_main
  订单号 / 客户 / 总金额 / 状态（字典）/ 下单时间

子表  order_detail（一对多）
  关联订单 / 商品 / 单价 / 数量 / 小计

产出：
  - Java   Entity / Mapper / Service / Controller
  - 前端   Vue3 + AntDesign 列表 + 表单页
  - SQL    建表脚本 + 菜单 SQL

复制到工程对应包路径，重启后立即生效。
```

</details>

**通用交互流程**

```
1. 用自然语言描述需求
2. AI 询问后端地址和 Token（如需调用 API）
3. AI 展示配置摘要，等待确认
4. 确认后自动执行，返回结果
5. 可在同一会话中继续修改
```

**X-Access-Token 获取方式**

1. 打开 JeecgBoot 系统并登录
2. 按 F12 打开浏览器开发者工具，切换到 **Network** 标签
3. 点击任意请求，在 **Request Headers** 中找到 `X-Access-Token`
4. 复制完整的 Token 值粘贴给 AI

---

## 🔍 技能详情

### 1. jeecg-codegen — 代码生成器

**一句话**：用自然语言描述业务需求，自动生成 JeecgBoot 全套 CRUD 代码。

**核心能力**：

- 支持单表、树表、一对多（主子表）三种模式
- 智能字段推导：名称 → Input、金额 → InputNumber、状态 → 字典下拉、图片 → 图片上传
- 字典智能匹配：自动读取 `sys_dict` 表，为字段匹配已有字典编码
- 已有表反向生成：给表名即可，自动查询 DDL 生成代码
- 增量修改：加 / 删 / 改字段，精确修改每个相关文件
- 主键策略自适应、Flyway 版本号自动递增

**使用文档**：[skill-usage-guide.md](jeecg-codegen/docs/skill-usage-guide.md)

### 2. jeecg-codegen-new — 新一代代码生成器（Freemarker 驱动）

**一句话**：新一套代码生成器，基于 jeecg 官方 Freemarker 模板生成全套 CRUD，**速度更快**、布局更丰富。

**核心能力**：

- **模板驱动**：基础代码全部由官方 Freemarker 模板生成，AI 只负责拼参数、调脚本、改特殊产物，不再从零写代码
- 表类型 × 前端风格组合：单表 / 树表 / 一对多，一对多支持 Tab-in-Modal、内嵌子表、ERP 三种布局
- 前端风格可选 `vue3` / `vue3Native`
- 智能字段映射 + 字典自动匹配（查 `sys_dict` 自动套字典编码）
- 已有表反向生成、增量加 / 删 / 改字段
- 产出后端 Java + 前端 Vue3 + 菜单 SQL，Flyway 版本号自动递增

> 与 `jeecg-codegen` 互补：`codegen-new` 走 Freemarker 模板、生成更快且布局更多；按需选用。

### 3. jeecg-onlform — Online 表单生成器

**一句话**：用自然语言描述表结构，自动通过 API 创建 Online 表单（元数据驱动 CRUD）。

**核心能力**：

- 元数据驱动，无需写代码即可生成完整 CRUD 页面
- 单表 / 主子表（一对多 / 一对一）/ 树表 三种模式
- 智能字段类型推导和控件映射（30+ 控件类型）
- 字典智能匹配（系统字典 / 字典表 / 带条件字典表）
- 增量字段修改（加 / 删 / 改字段，无需重新创建）
- 自动同步数据库 + 生成菜单 SQL

### 4. jeecg-onlreport — Online 报表生成器

**一句话**：用自然语言描述报表需求，自动生成 SQL 并通过 API 创建 Online 数据报表。

**核心能力**：

- SQL 驱动的数据报表，支持查询、排序、导出
- 智能字段配置：显示 / 隐藏、查询模式（模糊 / 精确 / 范围）、排序、合计
- 字段中文名自动翻译
- 字典和取值表达式支持
- 分组表头、字段跳转等高级功能
- SQL 参数化查询（Velocity 模板语法）

### 5. jeecg-desform — 设计器表单生成器

**一句话**：用自然语言描述表单需求或提供截图，自动生成设计器表单 JSON 并通过 API 创建。

**核心能力**：

- **按截图原样生成表单**：提供表单截图，AI 自动识别布局和字段，还原生成对应表单
- 支持 40+ 控件类型：文本、数字、选择、日期、上传、富文本、人员选择等
- 支持主子表（明细表）设计
- 支持布局控制：一行多字段、分栏布局
- 关联记录 + 他表字段、公式计算
- 支持表单编辑和删除

### 6. jeecg-onlchart — Online 图表生成器

**一句话**：用自然语言描述图表需求，自动生成 SQL 并通过 API 创建 Online 数据可视化图表。

**核心能力**：

- 支持柱状图、折线图、饼图、组合图表
- 智能推导 X / Y 轴字段：维度字段 → X 轴，度量字段 → Y 轴
- 根据数据特征自动推荐图表类型
- 字段中文名翻译、字典自动关联
- 组合图表（折线 + 柱状同时展示）
- SQL 参数化查询、动态数据源

### 7. jeecg-bpmn — BPM 流程生成器

**一句话**：用自然语言描述审批流程，自动生成 Flowable BPMN 2.0 XML 并通过 API 部署。

**核心能力**：

- 支持顺序审批、条件分支（排他网关）、并行审批（并行网关）
- 支持会签（多实例任务）、子流程
- 多种审批人类型：固定人、发起人、部门负责人、角色组、上一节点指派
- 条件表达式自动生成：金额判断、天数判断、状态判断
- 同一会话内可连续修改流程

### 8. jeecg-aiflow — AI 编排流程生成器

**一句话**：用自然语言描述需求，自动创建 AI 编排流程（AIFlow），编排大模型 / 知识库 / 判断等节点并发布。

**核心能力**：

- **模板驱动编排**：AI 选择节点类型，脚本从权威模板生成完整节点结构与 LiteFlow EL 链路，避免格式错误
- 丰富节点类型：开始 / 结束、大模型（LLM）、知识库检索、条件判断、参数提取等
- 全生命周期管理：创建、编辑、查询、删除、调试运行、发布 / 取消发布、复制流程
- 工作目录机制：凭 `workId` 自动读取 API 凭证与流程 design JSON，修改前先查询再改
- 典型场景：知识库问答助手、大模型对话流程、智能体编排

> 注意：本技能仅处理 AI 编排流程（AIFlow），BPMN 工作流请用 `jeecg-bpmn`，简流请用 `jeecg-lowcode-miniflow`。

### 9. jimubi-bigscreen — 大屏生成器

**一句话**：用自然语言描述大屏需求，自动生成全屏数据可视化大屏并通过 API 创建。

**核心能力**：

- 全屏展示模式，绝对定位（像素坐标），深色主题
- 默认 1920×1080 分辨率，适用于监控室 / 展厅 / 展示墙
- 丰富组件支持：数字翻牌、折线图、柱状图、饼图、地图、滚动表格、排行榜等
- 装饰元素：边框（JDragBorder）、装饰条（JDragDecoration）增强视觉效果
- 自定义背景图和主题配色

> 注意：大屏与仪表盘使用完全不同的布局和样式体系，仪表盘请使用 `jimubi-dashboard`。

### 10. jimubi-dashboard — 仪表盘生成器

**一句话**：用自然语言描述看板需求，自动生成栅格布局数据仪表盘并通过 API 创建。

**核心能力**：

- 24 列栅格布局，亮色主题，卡片式设计
- 适用于日常数据看板、运营统计面板
- 支持数字卡片、折线图、柱状图、饼图、表格、排行榜、仪表盘等组件
- 智能栅格分配：数字卡片 4 个一行，图表半宽或全宽自动排列
- 卡片头与 ECharts 标题智能去重

> 注意：仪表盘与大屏使用完全不同的布局和样式体系，大屏请使用 `jimubi-bigscreen`。

### 11. jimureport — 积木报表生成器

**一句话**：用自然语言描述报表需求或提供截图，自动生成积木报表（全类型支持）并通过 API 创建。

**核心能力**：

- **按截图原样生成报表**：提供报表截图，AI 自动识别表格布局、字段和样式，还原生成对应报表
- 全类型报表支持：数据报表、打印报表、分组报表（横向 / 纵向分组小计）、循环报表（loopBlock 明细循环）、数据填报等
- 可视化 Excel 设计器风格，支持自由布局、合并单元格、多 Sheet
- 数据绑定：`#{数据集编码.字段名}` 模板语法
- 支持数据填报（submitForm），用户可直接在报表中录入和提交数据
- 精细打印控制：纸张大小、边距、方向，适用于票据、证书、处方等打印场景
- CSS / JS / Python 增强能力
- 与 Online 报表（cgreport）互补：积木报表侧重复杂布局与多样化报表类型，Online 报表侧重快速配置

---

## 🧩 适用版本

- **JeecgBoot** 3.x（Spring Boot 3 + Jakarta + MyBatis-Plus）
- **JimuReport** 积木报表 1.7+
- **前端** Vue3 + TypeScript + Vite + Ant Design Vue 4
- **Claude Code** 最新版本

---

## 🔗 相关链接

- **官方 Skills 主页**：<https://jeecg.com/skills>
- **GitHub 仓库**：<https://github.com/jeecgboot/skills>
- **Gitee 镜像**：<https://gitee.com/jeecg/skills>
- **在线文档**：<https://help.jeecg.com/java/ai/skills/skill-comparison>
- **视频教程**：[Skills + JeecgBoot 自然语言编程实战（Bilibili）](https://www.bilibili.com/video/BV1KKwTzJEbX/)
- **Claude Code 下载**：<https://code.claude.com/docs/zh-CN/quickstart>

---

<p align="center">
  <sub>JeecgBoot v3.9.2 王炸升级｜低代码迈入 v2.0 时代 — 告别拖拉拽，Skills 加持一句话搭建系统</sub>
</p>
