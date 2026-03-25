# Arxiv-Insight Sentinel (arxiv 论文智能哨兵)

这是一个利用 LLM（大模型）对 Arxiv 论文进行每日自动抓取、筛选和精读的智能助手。

## 功能特点

- **自动抓取**: 根据预设关键词抓取 Arxiv 最新论文。
- **AI 智能评分**: 结合公司/个人背景，对论文相关性打分 (0-10)。
- **一句话总结**: AI 提炼核心创新点和价值评估。
- **可视化报告**: 按优先级排序展示，支持 PDF 下载。

## 快速开始

### 1. 安装依赖

确保你已经安装了 Python (建议 3.8+)。

```bash
pip install -r requirements.txt
```

### 2. 配置环境 (可选)

你可以创建一个 `.env` 文件来预设 OpenAI API Key，或者直接在界面上输入。

```bash
cp .env.example .env
# 编辑 .env 文件填入你的 API Key
```

### 3. 运行应用

```bash
streamlit run app.py
```

## 使用说明

1. 在左侧侧边栏输入 **OpenAI API Key** (如果未在 .env 中配置)。
2. 修改 **公司业务背景**，描述你关注的技术领域。
3. 设置 **Arxiv 搜索关键词** (例如 `cat:cs.CV` 表示计算机视觉)。
4. 点击 **开始同步与分析**。

## 核心技术栈

- [Streamlit](https://streamlit.io/): Web 界面
- [Arxiv API](https://pypi.org/project/arxiv/): 论文数据源
- [OpenAI API](https://platform.openai.com/): 智能分析引擎
