import requests
import json
import os
import re
from github import Github
from datetime import datetime

# --- 配置 ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
FILE_PATH = "ip_pool.json"

# 更加真实的请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/"
}

def extract_ips_from_text(text):
    """使用正则表达式从任何文本中提取 IPv4 地址"""
    # 匹配标准的 IPv4 格式
    ip_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    return set(re.findall(ip_pattern, text))

def fetch_ips():
    ips = set()
    if not os.path.exists("sources.txt"):
        return []
        
    with open("sources.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            print(f"🔍 尝试穿透提取: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            
            # 不管是不是 JSON，都先尝试正则提取
            found = extract_ips_from_text(resp.text)
            
            # 过滤掉一些常见的非 Cloudflare IP (可选)
            # 比如过滤掉 0.0.0.0 或 127.0.0.1
            found = {ip for ip in found if not ip.startswith(('127.', '0.'))}
            
            if found:
                ips.update(found)
                print(f"✅ 成功从源码中“抠”出 {len(found)} 个 IP")
            else:
                print(f"❌ 源码中未发现 IP 特征 (Status: {resp.status_code})")

        except Exception as e:
            print(f"❌ 请求异常: {e}")
                
    return list(ips)

# ... 后续 update_pool 保持不变 ...
