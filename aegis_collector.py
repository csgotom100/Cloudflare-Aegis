import requests
import json
import os
from github import Github
from datetime import datetime

# --- 配置 ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
FILE_PATH = "ip_pool.json"

# 模拟浏览器的请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def fetch_ips():
    ips = set()
    if not os.path.exists("sources.txt"):
        print("❌ 错误: 找不到 sources.txt")
        return []
        
    with open("sources.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            print(f"🔍 正在从 {url} 提取原料...")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            
            # 如果状态码不是 200，说明被拦截了
            if resp.status_code != 200:
                print(f"⚠️ 访问受阻 (Status: {resp.status_code})")
                continue

            data = resp.json()
            
            # 兼容 uouin 结构: {"data": [{"ip": "1.2.3.4"}, ...]}
            # 兼容 hostmonit 结构: {"info": [{"address": "1.2.3.4"}, ...]}
            # 兼容某些直接返回数组的结构
            raw_list = []
            if isinstance(data, list):
                raw_list = data
            elif isinstance(data, dict):
                raw_list = data.get('data', data.get('info', []))
            
            count_before = len(ips)
            for item in raw_list:
                if isinstance(item, str): # 如果直接是IP字符串
                    ips.add(item)
                else:
                    ip = item.get('ip') or item.get('address')
                    if ip: ips.add(ip)
            
            print(f"✅ 成功从该源获取了 {len(ips) - count_before} 个新IP")

        except Exception as e:
            print(f"❌ 提取失败 {url}: {e}")
            # 打印部分返回内容方便调试
            if 'resp' in locals():
                print(f"原始内容预览: {resp.text[:100]}")
                
    return list(ips)

def update_pool(new_ips):
    # 这里保持之前的 GitHub 推送逻辑不变...
    # (为了简洁，此处省略重复的 update_pool 代码，直接调用你脚本中的即可)
    pass 

if __name__ == "__main__":
    raw_ips = fetch_ips()
    # ...后续逻辑...
