import streamlit as st
import arxiv
import pandas as pd
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Load environment variables
load_dotenv()

# --- Logic Layer ---

def get_arxiv_papers(query, max_results=10):
    """
    Fetch papers from Arxiv based on the query.
    """
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        papers = []
        for result in search.results():
            papers.append({
                "title": result.title,
                "summary": result.summary,
                "published": result.published,
                "pdf_url": result.pdf_url,
                "authors": [a.name for a in result.authors],
                "entry_id": result.entry_id
            })
        return papers
    except Exception as e:
        st.error(f"Error fetching papers: {e}")
        return []

# Configure retry logic: retry up to 3 times, waiting exponentially
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def call_openai_with_retry(client, model, messages, response_format):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        response_format=response_format,
        timeout=30  # 30 seconds timeout
    )

def analyze_paper(client, paper, company_context):
    """
    Analyze a single paper using OpenAI API.
    """
    prompt = f"""
    公司背景: {company_context}
    
    论文信息:
    标题: {paper['title']}
    摘要: {paper['summary']}
    
    请根据公司背景，对该论文进行评估。
    你的输出必须是严格的 JSON 格式，包含以下字段：
    1. "score": 0-10 之间的整数，表示相关性评分。
    2. "summary": 字符串，3句以内的核心创新点总结。
    3. "reason": 字符串，说明为什么该论文对公司有价值或无用 (Why it matters)。
    4. "priority": 字符串，取值为 "High", "Medium", "Low"。
    
    JSON 示例:
    {{
        "score": 8,
        "summary": "提出了一种新的轻量化注意力机制...",
        "reason": "该方法可用于优化我们的边缘设备模型推理速度。",
        "priority": "High"
    }}
    """
    
    try:
        # Using gpt-4o as originally designed
        response = call_openai_with_retry(
            client,
            model="Qwen/Qwen3-8B", 
            messages=[
                {"role": "system", "content": "你是一个资深技术专家助手，负责为公司筛选前沿技术论文。请只返回 JSON 格式的结果。"},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        st.error(f"Error analyzing paper {paper['title']}: {e}")
        return None

# --- UI Layer ---

def main():
    st.set_page_config(page_title="Arxiv 智能哨兵", layout="wide", page_icon="📚")
    st.title("📚 Arxiv-Insight Sentinel (论文智能哨兵)")
    st.markdown("每日自动抓取特定领域最新论文，利用 AI 进行相关性评分与摘要。")

    # --- Sidebar Configuration ---
    with st.sidebar:
        st.header("⚙️ 系统配置")
        
        # API Key handling
        env_api_key = os.getenv("OPENAI_API_KEY")
        api_key = st.text_input("OpenAI API Key", value=env_api_key if env_api_key else "", type="password")
        
        st.subheader("上下文设定")
        company_bg = st.text_area(
            "公司业务背景", 
            # value="我们是用友网络，致力于构建 LOM (Large Ontology Model) 引擎，通过将传统软件的知识、逻辑与流程深度“内化”进大模型，打造具备“发现、分析、决策、执行”全生命周期闭环能力的本体智能体，实现从“人适应软件”到“模型自主执行”的进化。",
            value="我们是用友网络，致力于基于大模型构建本体，让本体构建过程自动化，目标实现 LOM (Large Ontology Model) 引擎。", 
            height=150
        )
        
        st.subheader("抓取设定")
        # topic = st.text_input("Arxiv 搜索关键词", value="cat:cs.CL AND (LLM OR benchmark OR database OR ontology OR Graph)")
        topic = st.text_input("Arxiv 搜索关键词", value='"probing knowledge"') # "probing knowledge" or "knowledge probing" or "concept probing" or "probing concept"
        max_results = st.slider("抓取数量", 5, 200, 10)
        
        start_btn = st.button("🚀 开始同步与分析")

    # --- Main Content ---
    
    if start_btn:
        if not api_key:
            st.warning("请先配置 OpenAI API Key！")
            return

        client = OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn")
        
        with st.status("正在从 Arxiv 抓取最新论文...", expanded=True) as status:
            st.write(f"正在搜索关键词: `{topic}`")
            papers = get_arxiv_papers(topic, max_results)
            st.write(f"成功获取 {len(papers)} 篇论文。")
            
            if not papers:
                status.update(label="未找到相关论文", state="error")
                return

            status.update(label="正在进行 AI 智能分析...", state="running")
            
            # Progress bar
            progress_bar = st.progress(0)
            analyzed_results = []
            
            for i, paper in enumerate(papers):
                result = analyze_paper(client, paper, company_bg)
                if result:
                    # Combine paper info with analysis result
                    full_data = {**paper, **result}
                    analyzed_results.append(full_data)
                progress_bar.progress((i + 1) / len(papers))
            
            status.update(label="分析完成！", state="complete")
        
        # --- Display Results ---
        if analyzed_results:
            # Sort by score descending
            analyzed_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            st.divider()
            st.subheader(f"📊 分析报告 (共 {len(analyzed_results)} 篇)")

            json_ready_results = []
            for p in analyzed_results:
                p_copy = p.copy()
                pub = p_copy.get("published")
                if hasattr(pub, "isoformat"):
                    p_copy["published"] = pub.isoformat()
                json_ready_results.append(p_copy)

            json_data = json.dumps(json_ready_results, ensure_ascii=False, indent=2)
            st.download_button(
                "💾 下载全部分析结果（JSON）",
                data=json_data,
                file_name="arxiv_analysis.json",
                mime="application/json"
            )
            
            for paper in analyzed_results:
                score = paper.get("score", 0)
                
                # Determine color based on priority/score
                priority = paper.get("priority", "Low")
                if priority == "High":
                    border_color = "red"
                    icon = "🔥"
                elif priority == "Medium":
                    border_color = "orange"
                    icon = "⚠️"
                else:
                    border_color = "grey"
                    icon = "ℹ️"

                with st.container(border=True):
                    col1, col2 = st.columns([1, 4])
                    
                    with col1:
                        st.metric("AI 相关性评分", f"{score}/10")
                        st.markdown(f"**优先级**: {icon} {priority}")
                        st.markdown(f"[📄 下载 PDF]({paper['pdf_url']})")
                        st.text(f"发布日期: {paper['published'].strftime('%Y-%m-%d')}")

                    with col2:
                        st.markdown(f"### {paper['title']}")
                        st.markdown(f"**👨‍💻 作者**: {', '.join(paper['authors'][:3])} et al.")
                        
                        st.markdown("#### 💡 核心创新点")
                        st.info(paper.get("summary", "无总结"))
                        
                        st.markdown("#### 🎯 价值评估 (Why it matters)")
                        st.write(paper.get("reason", "无评估"))
                        
                        with st.expander("查看原始摘要"):
                            st.caption(paper['summary'])

if __name__ == "__main__":
    if st.runtime.exists():
        main()
    else:
        import sys
        from streamlit.web import cli as stcli
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
