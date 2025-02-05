#!/usr/bin/env python3
# 投资级代币智能推送系统 v2.1
import os
import json
import asyncio
import aiohttp
from redis import Redis
from deepseek_api import DeepSeek
from gmgn import EnhancedGMGNClient
from telegram import Bot, InputFile

class TokenMonitor:
    def __init__(self):
        # 环境配置
        self.redis = Redis(host=os.getenv('REDIS_HOST', 'localhost'))
        self.deepseek = DeepSeek(api_key=os.getenv('DEEPSEEK_KEY'))
        self.gmgn = EnhancedGMGNClient(
            api_key=os.getenv('GMGN_KEY'),
            proxy=os.getenv('PROXY_URL')
        )
        self.bot = Bot(token=os.getenv('TG_BOT_TOKEN'))
        
        # 动态配置
        self.investment_grade = ["A+", "A", "B+"]
        self.analysis_template = self.load_analysis_template()
        
    def load_analysis_template(self):
        """加载动态分析模板"""
        with open('investment_template.md', 'r') as f:
            return f.read().strip()

    async def enhanced_analysis(self, contract):
        """带自我验证的深度分析"""
        analysis = await self.base_analysis(contract)
        verification = await self.cross_validate(contract, analysis)
        return self.fusion_results(analysis, verification)

    async def base_analysis(self, contract):
        """基础DeepSeek分析流程"""
        prompt = self.analysis_template.format(
            contract=contract,
            market_data=await self.get_market_context()
        )
        for retry in range(3):
            try:
                response = await self.deepseek.chat.completions.create(
                    model="deepseek-chat-32k",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                return self.parse_response(response)
            except Exception as e:
                print(f"分析异常重试 {retry+1}/3: {str(e)}")
                await asyncio.sleep(2**retry)
        return None

    async def cross_validate(self, contract, analysis):
        """多维度交叉验证"""
        tasks = [
            self.check_dev_expertise(contract['dev_address']),
            self.verify_market_hype(contract['symbol']),
            self.simulate_trading(contract['liquidity'])
        ]
        results = await asyncio.gather(*tasks)
        return {
            'dev_skill': results[0],
            'hype_index': results[1],
            'volatility': results[2]
        }

    async def process_contract(self, contract):
        """增强型处理管道"""
        if self.redis.exists(contract['address']):
            return
        
        # 标记处理中
        self.redis.setex(contract['address'], 600, 'processing')
        
        try:
            # GMGN基础过滤
            if not await self.gmgn_safety_check(contract):
                return

            # 深度分析
            analysis = await self.enhanced_analysis(contract)
            if analysis['grade'] not in self.investment_grade:
                return

            # 生成可视化报告
            report = await self.generate_visual_report(contract, analysis)
            
            # 最终推送
            await self.push_alert(report)

        finally:
            self.redis.delete(contract['address'])

    async def push_alert(self, report):
        """带附件的富文本推送"""
        chart = InputFile(report['chart'])
        message = f"""
📈 **DeepSeek精选警报** 📉
{report['text']}
        """
        await self.bot.send_photo(
            chat_id=os.getenv('TG_CHAT_ID'),
            photo=chart,
            caption=message,
            parse_mode="MarkdownV2"
        )

# 部署流水线脚本
DEPLOY_TEMPLATE = """#!/bin/bash
# 自动部署脚本
set -e

echo "🛠️  正在部署代币监控系统..."
export DEEPSEEK_KEY="{{deepseek_key}}"
export GMGN_KEY="{{gmgn_key}}"

# 安装服务配置
cat > /etc/systemd/system/token-monitor.service <<EOF
[Unit]
Description=Token Monitoring Service
After=network.target redis.service

[Service]
ExecStart=/usr/bin/python3 {path}/monitor.py
Restart=always
EnvironmentFile={path}/.env

[Install]
WantedBy=multi-user.target
EOF

# 启用服务
systemctl daemon-reload
systemctl enable token-monitor
systemctl start token-monitor

echo "✅ 部署完成！使用 systemctl status token-monitor 查看状态"
"""