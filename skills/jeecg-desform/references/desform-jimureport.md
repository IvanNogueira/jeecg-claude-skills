# desform 一键生成积木报表（打印）

为表单设计器（desform）表单一键创建积木报表并关联到「积木报表打印」（`allowJmReport`），
实现单条记录的高度自定义打印效果。脚本：`scripts/desform_jimureport.py`。

> 触发场景：用户说「给这个表单加积木报表打印」「创建打印报表」「desform 集成积木」「一键生成打印模板」等。
> 仅需简单的"按字段排版打印"用本脚本即可，**无需**加载 jimureport 技能。
> 仅当用户要高度定制的报表（分组/交叉/图表/套打背景图等）时，才加载 **jimureport** 技能，
> 并用本文档的 desform 数据 API 规范作为数据集来源。

---

## 与 onlform 集成的关键差异（已实测确认 @2026-05-21）

| 维度 | desform（本脚本） | onlform |
|------|------------------|---------|
| 数据 API 路径 | `/desform/api/data/{desformCode}/queryById` | `/online/cgform/api/data/{tableName}/queryById` |
| `mock` 参数 | **不支持**（apiUrl 里不带 `&mock=true`） | 支持 `&mock=true` |
| `fieldList.fieldName` | 控件 **model**（如 `input_1779...`） | 数据库字段名 |
| `fieldList.fieldText` | 控件 **title**（中文名） | 字段中文名 |
| 单元格绑定符号 | `${dbCode.model}`（**单值**绑定） | `#{dbCode.field}`（列表绑定） |
| 数据返回结构 | `{"data":[ {model:value} ]}` | 同 |
| `isList` / `isPage` | `"1"` / `"0"` | `"1"` / `"0"` |
| 预览 URL 变量 | `{{sysBasePath}}/jmreport/view/{id}` | `{{ window._CONFIG['domianURL'] }}/jmreport/view/{id}` |
| 回写位置 | `designConfig.config.allowJmReport` + `jmReportURL` | `extConfigJson.reportPrintShow` + `reportPrintUrl` |
| 回写方式 | `update_design_config(code, {...})` | `PUT /online/cgform/head/edit` |

> **核心结论（最易踩坑）**：数据 API 返回 JSON 的 key **永远等于控件 `model`**。
> 所以 `fieldName` 必须填 model、绑定写 `${dbCode.model}`；填 `key` 或中文名会导致打印值全空。

---

## API base 可能是两个不同地址（重要）

desform 接口与积木报表接口的服务地址常常不同：

| 接口前缀 | 用哪个 base | 示例 |
|---------|-----------|------|
| `/desform/*` | `--api-base` | `http://host:3100/jeecgboot` |
| `/jmreport/*` | `--jmreport-base` | `http://host:8080/jeecg-boot` |

- `--jmreport-base` 缺省时与 `--api-base` 相同（同体部署时只传一个即可）。
- 部署分离时**必须**显式传 `--jmreport-base`，否则报表创建/预览会失败或访问到错误后端。
- 回写表单的 `jmReportURL` 用运行时变量 `{{sysBasePath}}`，由前端解析，不写死地址，因此跨环境迁移友好。

---

## 用法

```bash
python <skill目录>/scripts/desform_jimureport.py \
    --api-base http://host:3100/jeecgboot \
    --jmreport-base http://host:8080/jeecg-boot \
    --token <X-Access-Token> \
    --config <config.json>
```

> Windows 下用 PowerShell tool 执行（避免 Bash tool 把 python 后台化）。

### 创建报表 config

```json
{
  "action": "create_report",
  "desformCode": "oa_car_use",
  "reportName": "用车申请打印",
  "formStyle": "auto"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `action` | 是 | `create_report` |
| `desformCode` | 是 | desform 表单编码 |
| `reportName` | 否 | 缺省 = `{表单名}打印` |
| `formStyle` | 否 | `auto`(默认,读表单 formStyle) / `normal` / `word` |
| `dataCode` | 否 | 数据集编码，缺省 = desformCode |
| `fields` | 否 | 手动指定字段 `[{"fieldName":"<model>","fieldText":"中文"}]`；缺省自动从表单设计读取 |

脚本 5 步：创建空报表 → 保存 API 数据源 → 构造卡片模板 → 保存设计 → 回写表单 `allowJmReport`/`jmReportURL`。

### 删除报表 config

```json
{
  "action": "delete_report",
  "reportId": "1217365226891173888",
  "desformCode": "oa_car_use"
}
```

- `reportId` 必填。
- `desformCode` 可选：提供则同时清除表单的 `allowJmReport=false`、`jmReportURL=""`。
- ⚠️ 若该表单的关联已指向**另一个**报表，删旧报表时**不要**传 `desformCode`，否则会误清当前关联。

---

## formStyle 样式适配

脚本按表单的 `formStyle` 自动套用两套打印样式（`formStyle:"auto"` 时）：

| 表单风格 | 标题 | 标签列 | 值列 |
|---------|------|--------|------|
| `normal` | 蓝底深蓝字加粗（style 5） | 灰底右对齐加粗（style 3） | 左对齐（style 6） |
| `word` | 无底色加粗（style 7） | 浅灰底居中加粗（style 8） | 左对齐（style 6） |

布局：标签-值成对排列，每行 2 组共 4 列；长文本控件（textarea/富文本）值独占整行（合并 3 列）。
样式数组与 onlform 的 `build_styles()` 同源，确保观感一致。

---

## 不打印的内容（与"复杂控件不特殊处理"约定一致）

脚本提取字段时自动跳过：
- 布局容器：`card` / `grid` / `tabs` / `divider` / `text` / `html` / `button` / `alert`
- **子表**（`sub-table-design`）：跳过；如需打印子表请加载 jimureport 技能手动设计循环块/主子报表

其余数据控件（选人/选部门/关联记录/图片/文件等）按 `${dbCode.model}` 原样绑定，渲染其存储值文本，不做转换。

---

## 实测验证记录

- 2026-05-21：`oa_car_use`（用车申请，10 字段，normal 风格），分离 base（desform=3100/jeecgboot，jmreport=8080/jeecg-boot）一次创建成功；浏览器预览 `${oa_car_use.model}` 全部正确替换为真实值，卡片布局、蓝底标题、标签灰底均正常渲染。
- 关键确认：数据 API 返回 `{"data":[{...}]}`，key=控件 model；`isList="1"` + `${}` 单值绑定组合渲染正确。
