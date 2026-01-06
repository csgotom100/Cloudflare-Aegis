import requests
import json
import os
import re
import base64
from github import Github
from datetime import datetime

# --- 配置 ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
FILE_JSON = "ip_pool.json"
FILE_TXT = "ips_txt_view.txt"  # 新增：方便观察的文本格式

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}

def extract_ips(text):
    """最强正则：提取 IPv4"""
    return set(re.findall(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', text))

def fetch_ips():
    all_found = set()
    if not os.path.exists("sources.txt"):
        print("❌ sources.txt 不存在")
        return []
        
    with open("sources.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            print(f"🌐 正在爬取: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            # 尝试直接正则抓取
            ips = extract_ips(resp.text)
            
            # 如果没抓到，尝试对整个页面进行 Base64 解码后再抓（针对某些加密源）
            if not ips:
                try:
                    decoded_text = base64.b64decode(resp.text).decode('utf-8')
                    ips = extract_ips(decoded_text)
                except:
                    pass
            
            if ips:
                all_found.update(ips)
                print(f"✅ 抓取成功: 获得 {len(ips)} 个 IP")
            else:
                print(f"⚠️ 抓取结果为空，页面长度: {len(resp.text)}")
        except Exception as e:
            print(f"❌ 请求失败: {url} -> {e}")
                
    return sorted(list(all_found))

def update_repo(ips_list):
    if not ips_list:
        print("停止更新：本次未获取到任何 IP")
        return

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    # --- 1. 更新 ip_pool.json (逻辑库) ---
    try:
        contents = repo.get_contents(FILE_JSON)
        db = json.loads(contents.decoded_content.decode())
    except:
        db = {"last_update": "", "pool": {}}

    for ip in ips_list:
        if ip not in db['pool']:
            db['pool'][ip] = {"score": 100, "fail_count": 0, "added_at": datetime.now().strftime("%Y-%m-%d")}
    
    db['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    json_str = json.dumps(db, indent=2)

    # --- 2. 更新 ips_txt_view.txt (观察清单) ---
    txt_content = f"# 弹药库预览 (最后更新: {db['last_update']})\n"
    txt_content += f"# 总计数量: {len(ips_list)}\n\n"
    txt_content += "\n".join(ips_list)

    # --- 3. 提交更改 ---
    print(f"🚀 准备提交: 库内总数 {len(db['pool'])}，本次新增文本预览...")
    
    # 提交 JSON
    try:
        repo.update_file(FILE_JSON, "Update JSON Pool", json_str, contents.sha)
    except:
        repo.create_file(FILE_JSON, "Create JSON Pool", json_str)

    # 提交 TXT (覆盖更新)
    try:
        txt_file = repo.get_contents(FILE_TXT)
        repo.update_file(FILE_TXT, "Update TXT View", txt_content, txt_file.sha)
    except:
        repo.create_file(FILE_TXT, "Create TXT View", txt_content)
    
    print("🔥 GitHub 仓库同步成功！")
    print(f"🔍 样板数据 (前5个): {ips_list[:5]}")

if __name__ == "__main__":
    found_list = fetch_ips()
    update_repo(found_list)
