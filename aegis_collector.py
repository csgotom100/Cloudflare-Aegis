import requests
import os
import random
import re
import json
import time

# ================= 配置区 =================
WORKER_URL = "https://ip.usub.de5.net/update" 
API_KEY = "your_secret_password_here"  # 必须与 Worker 中的 MASTER_KEY 一致
LOCAL_FILE = "sources.txt"             # 你手动维护的高质量 IP
SOURCE_URLS = [
    "https://raw.githubusercontent.com/Alvin9999/new-pac/master/cloudflare/ip.txt",
    "https://raw.githubusercontent.com/vfarid/v2ray-worker-proxy/main/ips.txt"
]
# 黑名单：剔除 1.0.0.1, 1.1.1.1 等公共 DNS
IP_BLACKLIST = [
    "1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "1.1.1.2", "1.0.0.2",
    "1.1.1.3", "1.0.0.3", "9.9.9.9", "149.112.112.112"
]
# =========================================

def is_valid_ip(ip):
    ip = ip.strip()
    pattern = r'^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$'
    if not re.match(pattern, ip) or ip in IP_BLACKLIST:
        return False
    if ip.startswith(("127.", "192.168.", "10.", "172.16.")):
        return False
    return True

def fetch_ips():
    all_ips = set()
    # 1. 读取本地保底文件
    if os.path.exists(LOCAL_FILE):
        with open(LOCAL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                for p in line.replace(',', ' ').split():
                    if is_valid_ip(p): all_ips.add(p)
    
    # 2. 抓取远程优选源
    for url in SOURCE_URLS:
        try:
            res = requests.get(url, timeout=10)
            for p in res.text.replace(',', ' ').replace('\n', ' ').replace('\r', ' ').split():
                if is_valid_ip(p): all_ips.add(p)
        except: continue
    return list(all_ips)

def save_and_push():
    ip_list = fetch_ips()
    
    # 保底逻辑：如果新抓取的太少，尝试合并旧的 ips.txt
    if len(ip_list) < 20 and os.path.exists("ips.txt"):
        with open("ips.txt", "r") as f:
            old_ips = [line.strip() for line in f if is_valid_ip(line)]
            ip_list = list(set(ip_list) | set(old_ips))

    if not ip_list:
        print("❌ 错误：未获取到任何有效 IP")
        return

    # 随机挑选，有多少拿多少，上限 40
    selected_ips = random.sample(ip_list, min(len(ip_list), 40))

    # 生成 TXT 备份
    with open("ips.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(selected_ips))

    # 生成 JSON 备份
    with open("ips.json", "w", encoding="utf-8") as f:
        json.dump({
            "update_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_found": len(ip_list),
            "ips": selected_ips
        }, f, indent=4)

    # 推送至 Worker
    try:
        r = requests.post(WORKER_URL, json={"key": API_KEY, "ips": selected_ips}, timeout=15)
        print(f"✅ 推送成功: {r.status_code}, 弹药量: {len(selected_ips)}")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

if __name__ == "__main__":
    save_and_push()
