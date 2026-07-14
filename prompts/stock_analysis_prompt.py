STOCK_ANALYSIS_SYSTEM_PROMPT = """
你是一个股票单股分析助手，面向股市新手解释技术面和风险。
你不能直接输出买入或卖出指令，只能给出观察建议和风险提示。
"""


def build_stock_analysis_prompt(stock_text: str) -> str:
    return f"""
请基于下面的单只股票数据，输出新手能看懂的辅助分析。

请包含：
1. 当前走势状态
2. 技术指标怎么理解
3. 需要重点观察的价格或均线
4. 风险点
5. 辅助观察建议
6. 风险提示

禁止输出直接买入/卖出指令。

股票数据：
{stock_text}
"""

