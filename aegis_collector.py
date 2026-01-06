import requests
import json
import base64
from github import Github
import os
from datetime import datetime

# --- 配置 ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY") # 格式：用户名/仓库名
FILE_PATH = "ip_pool.json"

def fetch_ips():
    ips = set()
    # 从 sources.txt 读取原料地址
    if not os.path.exists("sources.txt"):
        return []
        
    with open("sources.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            print(f"正在从 {url} 提取原料...")
            resp = requests.get(url, timeout=15)
            data = resp.json()
            
            # 兼容 uouin 结构: {"data": [{"ip": "1.2.3.4"}, ...]}
            # 兼容 hostmonit 结构: {"info": [{"address": "1.2.3.4"}, ...]}
            raw_list = data.get('data', data.get('info', []))
            
            for item in raw_list:
                ip = item.get('ip') or item.get('address')
                if ip:
                    ips.add(ip)
        except Exception as e:
            print(f"提取失败 {url}: {e}")
    return list(ips)

def update_pool(new_ips):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    try:
        contents = repo.get_contents(FILE_PATH)
        db = json.loads(contents.decoded_content.decode())
    except:
        db = {"last_update": "", "pool": {}}

    # 1. 保留原有 IP 的信用分，只增加新面孔
    # 2. 如果是库里已有的 IP，保持原分数，不重复添加
    for ip in new_ips:
        if ip not in db['pool']:
            db['pool'][ip] = {
                "score": 100,
                "fail_count": 0,
                "added_at": datetime.now().strftime("%Y-%m-%d")
            }
            
    db['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 推送更新
    repo.update_file(contents.path, "Refill Ammo from Raw Sources", 
                     json.dumps(db, indent=2), contents.sha)
    print(f"✅ 汇总完成！当前弹药库共有 {len(db['pool'])} 个动态优选 IP")

if __name__ == "__main__":
    raw_ips = fetch_ips()
    if raw_ips:
        update_pool(raw_ips)
