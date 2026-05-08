# 示例代码包

两份"故意写脏"的小项目，方便快速演示扫描效果。

## sample_python_project/

3 个文件，约 174 行。包含的常见问题：

- `data_processor.py`：4 层嵌套 if（高复杂度）+ 复制粘贴的 `process_data` / `transform_data`
- `user_module.py`：命名不规范、缺文档字符串、魔法值
- `utils.py`：未使用的 import、过长的行

## sample_java_project/

2 个文件，约 82 行：

- `Calculator.java`：方法命名不规范、魔法值、深嵌套
- `User.java`：缺 Javadoc、字段未私有化

## 使用方式

### 通过界面上传

```bash
# Windows: 在 examples 目录下右键 -> 发送到 -> 压缩文件夹
# Linux/Mac:
cd examples
zip -r sample_python.zip sample_python_project/
zip -r sample_java.zip   sample_java_project/
```

然后通过浏览器上传 `sample_python.zip` 或 `sample_java.zip`。

### 通过 CURL 上传

```bash
# 先创建项目
PID=$(curl -s -X POST http://127.0.0.1:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"示例 Python","language":"python"}' | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# 打包并上传
cd examples
zip -r /tmp/py.zip sample_python_project/
curl -X POST http://127.0.0.1:8000/api/scans/upload \
  -F project_id=$PID -F version_tag=v1.0 -F file=@/tmp/py.zip
```

## 期望扫描结果

| 示例 | 评分预期 | 主要问题 |
|------|----------|---------|
| sample_python_project | C 级（约 60-70 分） | 命名 + 复杂度 + 重复 |
| sample_java_project   | C 级（约 60-70 分） | Javadoc + 魔法值 + 命名 |

可作为系统验证基线：每次代码改动后跑一次，分数应保持稳定。
