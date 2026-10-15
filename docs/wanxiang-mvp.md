# 万象拼音离线资源集成（Trime v3.3.12）

本目录资源面向 Trime v3.3.12（上游 `e09ac711`）。方案、词库和已有语言模型随 APK 分发，首次部署在设备本地编译；未训练模型，未增加任何运行时联网代码。开发机下载不属于 APK 行为。

## 当前完成状态（2026-10-15）

本地模型完整下载完成，源文件与资产副本均匹配固定 SHA-256。已依次执行 `download-wanxiang.py`（全部命中缓存并核验）、严格 `import-wanxiang.py`（未使用允许缺模型选项）和 `verify-wanxiang.py`，最终全部成功。

- `model_complete: true`，`passed: true`，错误列表为空。
- 包含 68 个文件，总计 **492,043,713 字节**；其中模型 **398,354,476 字节**。
- 93 项静态引用检查通过；字典文本合计 2,649,009 条记录（含反查、字符集及中英混合，不表示去重后的中文词数）。
- 原始资源缓存保留在工作区 `work/wanxiang-source/`，本地可打包资产已生成到 `app/src/main/assets/rime/`。
- 主代理将生成资产目录加入 `.gitignore`，避免把近 492 MB 数据直接推送到 Git；CI 在构建前按 lock 下载、导入及校验，再打入 APK。固定资源清单、导入/校验脚本、许可证下载来源和文档应跟随源码提交。
- 尚未完成的验收：真实 Android 上的首次部署、长句输入、耗时/内存测试，以及最终 APK 内容核对。本报告不声称这些已通过。

## 版本、来源与许可证

| 资源 | 固定版本 / 来源 | 许可证 |
| --- | --- | --- |
| 万象基础版、词库和 Lua | [v13.1.0](https://github.com/amzxyz/rime-wanxiang/releases/tag/v13.1.0)，提交 `ced3589c2b6222e46001d32430aa297477770184` | CC-BY-4.0；保留源码中的作者和引用说明 |
| 万象简体长句语法模型 | [RIME-LMDG LTS](https://github.com/amzxyz/RIME-LMDG/releases/tag/LTS)，资产 ID `636982290`，2026-10-13T12:36:37Z 更新 | CC-BY-4.0 |
| 简繁转换数据 | [OpenCC](https://github.com/BYVoid/OpenCC/tree/907bfcbbd3aae86ff04bc8eaca67c8af03108ddf)，与 Trime 固定子模块一致 | Apache-2.0 |

选取已有正式基础版标签而非持续变化的 main，不引入 PRO 辅助码、T9、桌面前端配置或更新器。原始基础包保存于工作区 `work/wanxiang-source/rime-wanxiang-base-v13.1.0.zip`，原始模型保存于同一目录。

- 基础包：35,782,036 字节；SHA-256 `ede13f916fc3d415c1fe2e3057f30ccb68ee4e0f9658ec359d6684c24c68a992`。
- 模型：398,354,476 字节；SHA-256 `20aca767f06ab2abdccce5ea9c45af5364114a37e25bb7c6de40e4f328be029e`。
- **LTS 标签会变动**，因此以上模型通过资产 ID、大小、上游发布的 SHA-256 和本地缓存共同固定，不能仅凭 `LTS` URL 判断版本。重新下载出现哈希变化时应停止，不自动升级模型。上游删除旧资产后，固定版本的重建需要保留的本地缓存。
- 完整来源、大小、逐项哈希见 [wanxiang-resources.lock.json](wanxiang-resources.lock.json)。包内逐文件哈希见 [wanxiang-assets.manifest.json](wanxiang-assets.manifest.json)。许可证与署名同时位于 `app/src/main/assets/rime/licenses/`，会随 APK 分发。

## 与 librime 的兼容依据

通过 Trime v3.3.12 的 Git tree 核对：

- librime：`33e78140250125871856cdc5b42ddc6a5fcd3cd4`，其 CMakeLists 声明版本 **1.17.0**。
- librime-lua：`68f9c364a2d25a04c7d4794981d7c796b05ab627`。
- librime-octagram：`bd12863f45fbbd5c7db06d5ec8be8987b10253bf`。
- `app/src/main/jni/cmake/Rime.cmake` 已启用 lua、octagram、predict，无需本任务修改原生库或 Gradle。

万象基础方案使用 Rime `script_translator`、现有 Lua 插件与 octagram 的 `.gram` 文件。已检查模型二进制文件头为 `Rime::Grammar/1.0`，与固定 octagram 提交的 `src/gram_db.cc` 中 `kGrammarFormat` 一致。`grammar/language: wanxiang-lts-zh-hans` 精确对应模型文件名。上游 `translator/contextual_suggestions: false` 予以保留：这不关闭输入中整句组词使用的 grammar，而是关闭跨次输入的 contextual suggestions。当前未启用另一个需要独立预测数据的 predict 方案。

词库包含带声调拼音，采用包内 `wanxiang_algebra:/base/全拼` 转写；默认支持全拼和简拼。原始词库、Lua、主方案和模型内容不修改。兼容性依据为版本、组件和配置静态核对，**不等同于目标 Android 设备上的部署及长句输入验收通过**。

## 为什么使用 assets/rime

已检查 `DataManager.kt`、`ResourceUtils.kt` 和 `DataChecksumsPlugin.kt` 的实际代码，而非只依据目录名称：

1. assets 下原有公共配置在 `shared/`。
2. `generateDataChecksums` 递归枚举 assets，生成包含相对路径的 `checksums.json`。无需手工维护此文件。
3. `DataManager.sync()` 使用 `sharedDataDir.resolveSibling(it.path)` 计算新增/更新文件目标；所以 `rime/wanxiang.schema.yaml` 实际复制到 `getExternalFilesDir(null)/rime/wanxiang.schema.yaml`。
4. 工作区当前 DataManager 将上述应用专属 `rime/` 目录用作运行时用户目录。Lua、词库、模型及 OpenCC 数据在这里有统一路径。
5. 同步资产后才检查 `default.custom.yaml` 是否存在，并在缺失时生成只含朙月拼音的 fallback。本包提供 `rime/default.custom.yaml`，将 `schema_list` 设为 `wanxiang`，候选每页 6 个，保留万象数字声调规则。

本任务没有编辑核心 Kotlin、Manifest、Gradle 或其他功能。其他代理若调整 DataManager 用户目录，必须同步确认这些资源仍进入实际运行时用户目录。

## 包含的资源与本地改动

基础词库包括字表、基础词、关联词、联想长词、纠错、兼容读音、诗词、地名，以及中英混合、反查和字符集字典。保留全部实际被基础方案引用的 `dicts/`、`lua/` 和 `opencc/` 数据；省略示例 custom、T9、weasel、squirrel 和附带主题。

基础包不包含系统简繁转换数据，所以额外从 Trime 固定的 OpenCC 提交取得 `s2t/s2hk/s2tw` 配置以及 `STPhrases/STCharacters/HKVariants/TWVariants` 词典。导入脚本把这些配置里的 `ocd2` 类型和文件名改为对应的 `text` / `.txt`，直接使用 OpenCC 支持的文本词典，避免依赖构建时才生成的 `shared/opencc` 文件。原始 OpenCC 配置和其哈希仍保存在源目录及 lock 文件中。

Lua 的 `super_tips` 使用 `os.execute` 创建本地目录；没有下载、HTTP、socket 或更新器逻辑。`version_display` 输出项目网址作为普通候选文本，不会发起请求。用户词库、tips 数据库和排序数据可在应用专属目录本地生成。

## 导入与检查

从 trime 根目录执行（Python 3.11+；校验脚本另需开发环境 PyYAML）：

```powershell
python scripts/download-wanxiang.py
python scripts/import-wanxiang.py
python scripts/verify-wanxiang.py
```

下载脚本仅用于开发机/CI，匹配固定哈希的缓存不会重新下载。导入脚本不联网，先核对 lock 中全部下载文件的 SHA-256 和长度，再解包、添加本地配置、复制模型并重建包内 manifest。可用 `--source-dir` 指定保存原始资源的目录。开发阶段可以 `--allow-missing-model` 仅落地基础方案，但会明确标记 `model_complete: false`，严格校验也会失败；不能把这种状态当成完整模型 APK。重复导入会覆盖本任务管理的同名资源，不清理其他代理新增文件。

若缓存缺失，下载脚本按 lock 中的 URL 在**开发机或 CI**下载到对应 `file` 路径；大模型也可从 `asset_api_url` 以 `Accept: application/octet-stream` 获取，或使用发布 URL 后校验固定哈希。此次开发下载的分段脚本与原始发布元数据保留在工作区 `work/wanxiang-source/`；仓库下载脚本与 CI 配置也不进入 APK。

静态校验包括：YAML 可解析、字典 import_tables、schema dependencies、配置 include/patch 目标、Lua 入口与 require、表格文本、OpenCC JSON 及其字典、grammar 文件、包内所有文件 SHA-256。结果写入 [wanxiang-validation.json](wanxiang-validation.json)，其中记录真实词条行数。它不尝试替代 Rime 的部署编译或 Android 执行。

## 验收及已知限制

- 完整资源约 492 MB（详见 manifest 的逐项大小），另需 APK、首次复制和 Rime 编译产物空间。尚未在目标设备测量首次部署时间、峰值内存和最终磁盘占用。
- 没有在本任务中构建 APK、安装到设备或执行真实 librime 部署。应由构建/设备验收阶段确认 `.gram` 已进 APK 和运行时目录，检查 Rime 日志无缺词典、Lua 加载及 grammar 错误。
- 飞行模式首次启动并部署；确认方案列表显示万象，输入 `nihao`、`zhonghuarenmingongheguo`，以及 `jintianxiawuwomenyiqiqugongyuansanbu` 等连续拼音。验证空格选词、候选翻页、长句结果和简繁切换；不预先声称任意长句的首选命中率。
- 如测试长句模型收益，必须在干净的用户词库下分别运行有/无模型的相同输入，并记录结果；仅有配置及文件存在不能证明收益。
- 本包以全新安装为主要 MVP 场景。旧用户目录中同名 default/config 文件在资产更新时可能被覆盖，升级迁移策略不在本次资源集成范围。
- 上游 DataManager 删除资产时的路径处理与新增/更新处理不同，本任务没有更改它。后续资源删改或迁移目录应单独测试升级行为。
